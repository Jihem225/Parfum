"""Commandes : création depuis le panier, machine à états (§6.1), appels de confirmation.
Chaque changement écrit statut, stock, paiement, historique et audit dans la même transaction."""

import hashlib
import hmac
from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.config import settings
from app.core.errors import AppError
from app.modules.auth.models import User, UserRole
from app.modules.cart import service as cart_service
from app.modules.cart.models import Cart, CartItem
from app.modules.delivery.models import Commune
from app.modules.inventory import service as inventory
from app.modules.orders.models import (
    CallResult,
    EventKind,
    FailureReason,
    Order,
    OrderEvent,
    OrderItem,
    OrderStatus,
    order_number_seq,
)
from app.modules.orders.notify import fcfa
from app.modules.orders.schemas import CheckoutIn
from app.modules.payments.models import Payment, PaymentMethod, PaymentStatus
from app.modules.payments.providers import Notification, get_provider
from app.modules.promotions import service as promotions

S = OrderStatus
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    S.EN_ATTENTE_PAIEMENT: {S.CONFIRMEE, S.ANNULEE},  # confirmée par le paiement, pas un appel
    S.EN_ATTENTE_CONFIRMATION: {S.CONFIRMEE, S.ANNULEE},
    S.CONFIRMEE: {S.EN_PREPARATION, S.ANNULEE},
    S.EN_PREPARATION: {S.EN_LIVRAISON, S.ANNULEE},
    S.EN_LIVRAISON: {S.LIVREE, S.ECHEC_LIVRAISON},
    S.ECHEC_LIVRAISON: {S.EN_LIVRAISON, S.RETOURNEE},
    S.LIVREE: {S.RETOURNEE},
    S.RETOURNEE: set(),
    S.ANNULEE: set(),
}
CANCELLABLE = {S.EN_ATTENTE_PAIEMENT, S.EN_ATTENTE_CONFIRMATION, S.CONFIRMEE, S.EN_PREPARATION}
FINAL = {S.LIVREE, S.RETOURNEE, S.ANNULEE}
MAX_UNANSWERED_CALLS = 3  # RG-31
MAX_DELIVERY_ATTEMPTS = 2  # RG-44
RETRIABLE = {FailureReason.INJOIGNABLE, FailureReason.REPORTEE}
PAYMENT_DELAY = timedelta(minutes=30)  # mobile money non payé : commande annulée

LABELS = {
    S.EN_ATTENTE_PAIEMENT: "En attente de paiement",
    S.EN_ATTENTE_CONFIRMATION: "En attente de confirmation",
    S.CONFIRMEE: "Confirmée",
    S.EN_PREPARATION: "En préparation",
    S.EN_LIVRAISON: "En livraison",
    S.LIVREE: "Livrée",
    S.ECHEC_LIVRAISON: "Échec de livraison",
    S.RETOURNEE: "Retournée",
    S.ANNULEE: "Annulée",
}


def payment_token(number: str) -> str:
    """Jeton remis à l'acheteur : seul lui peut ouvrir ou suivre le paiement en ligne."""
    message = f"paiement:{number}".encode()
    return hmac.new(settings.secret_key.encode(), message, hashlib.sha256).hexdigest()[:32]


def check_payment_token(number: str, token: str) -> None:
    if not hmac.compare_digest(payment_token(number.upper()), token):
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")


def served_commune(db: Session, commune_id: int) -> Commune:
    commune = db.get(Commune, commune_id)
    if commune is None or not commune.is_active:
        raise AppError(422, "COMMUNE_NOT_SERVED", "Nous ne livrons pas encore cette commune.")
    return commune


def checkout(
    db: Session, data: CheckoutIn, *, cart: Cart | None, user: User | None
) -> tuple[Order, bool]:
    """Renvoie (commande, créée ?). Le panier est verrouillé par l'appelant : un double envoi
    attend le premier puis retrouve la commande par sa clé d'idempotence."""
    existing = db.scalar(select(Order).where(Order.idempotency_key == data.idempotency_key))
    if existing is not None:
        return existing, False
    if not data.accept_terms:
        raise AppError(
            422, "TERMS_REQUIRED", "Vous devez accepter les conditions générales de vente."
        )
    summary = cart_service.view(db, cart)
    if not summary.items or cart is None:
        raise AppError(409, "CART_EMPTY", "Votre panier est vide.")
    if any(line.issue for line in summary.items):
        raise AppError(
            409,
            "CART_CHANGED",
            "Certains articles ne sont plus disponibles dans la quantité demandée : vérifiez "
            "votre panier.",
            summary.model_dump(mode="json"),
        )
    commune = served_commune(db, data.commune_id)
    promo, discount = None, 0
    if data.promo_code:  # verrouillé : limites respectées même avec des commandes simultanées
        promo, discount = promotions.apply(
            db, data.promo_code, summary.subtotal, data.phone, lock=True
        )
    total = summary.subtotal - discount + commune.delivery_fee
    if total <= 0:
        raise AppError(
            422, "PROMO_INVALID", "Ce code promo ne peut pas rendre la commande gratuite."
        )
    mobile = data.payment_method == PaymentMethod.MOBILE_MONEY
    if mobile and get_provider() is None:
        raise AppError(
            422, "PAYMENT_UNAVAILABLE", "Le paiement par mobile money n'est pas disponible."
        )
    if not mobile and total > cart_service.COD_LIMIT:
        raise AppError(
            409,
            "COD_LIMIT",
            "Au-delà de 300 000 FCFA, contactez la boutique pour passer votre commande.",
        )
    if total != data.expected_total:
        # US-06 : un prix modifié entre l'ajout au panier et la validation est signalé.
        raise AppError(
            409,
            "PRICE_CHANGED",
            "Le montant de votre commande a changé : vérifiez le nouveau total.",
            {
                "subtotal": summary.subtotal,
                "discount": discount,
                "delivery_fee": commune.delivery_fee,
                "total": total,
            },
        )

    order = Order(
        number=f"{settings.order_number_prefix}-{db.scalar(order_number_seq.next_value())}",
        user_id=user.id if user else None,
        status=S.EN_ATTENTE_PAIEMENT if mobile else S.EN_ATTENTE_CONFIRMATION,
        idempotency_key=data.idempotency_key,
        customer_name=data.customer_name,
        phone=data.phone,
        email=data.email,
        commune_name=commune.name,
        address_line=data.address_line,
        landmark=data.landmark or None,
        delivery_fee=commune.delivery_fee,
        delivery_delay_label=commune.delay_label,
        subtotal=summary.subtotal,
        discount=discount,
        total=total,
        promo_code_id=promo.id if promo else None,
        promo_code=promo.code if promo else None,
    )
    db.add(order)
    db.flush()
    # RG-12 : tout ou rien ; en cas de manque, l'exception annule aussi la commande.
    inventory.reserve(
        db,
        {line.variant_id: line.quantity for line in summary.items},
        order_id=order.id,
        user_id=user.id if user else None,
    )
    db.add_all(
        OrderItem(
            order_id=order.id,
            variant_id=line.variant_id,
            product_name=line.product_name,
            volume_ml=line.volume_ml,
            sku=line.sku,
            unit_price=line.unit_price,
            quantity=line.quantity,
            line_total=line.line_total,
        )
        for line in summary.items
    )
    db.add(
        Payment(
            order_id=order.id,
            amount=total,
            method=data.payment_method,
            status=PaymentStatus.A_PAYER if mobile else PaymentStatus.A_ENCAISSER,
        )
    )
    db.add(
        OrderEvent(
            order_id=order.id,
            kind=EventKind.STATUS_CHANGE,
            to_status=order.status,
            user_id=user.id if user else None,
        )
    )
    db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    return order, True


def locked(db: Session, number: str) -> Order:
    order = db.scalar(select(Order).where(Order.number == number.upper()).with_for_update())
    if order is None:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    return order


def items(db: Session, order: Order) -> list[OrderItem]:
    return list(
        db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.id))
    )


def payment(db: Session, order: Order) -> Payment:
    return db.scalars(select(Payment).where(Payment.order_id == order.id)).one()


def transition(
    db: Session,
    order: Order,
    to: OrderStatus,
    *,
    actor_id: int | None,
    note: str = "",
    courier_id: int | None = None,
    failure_reason: FailureReason | None = None,
) -> None:
    """Seules les transitions du §6.1 passent ; les rôles sont contrôlés par les routes."""
    origin = order.status
    if to not in TRANSITIONS[origin]:
        raise AppError(
            409,
            "INVALID_TRANSITION",
            f"Impossible de passer de « {LABELS[origin]} » à « {LABELS[to]} ».",
        )
    paid = payment(db, order)
    if origin == S.EN_ATTENTE_PAIEMENT and to == S.CONFIRMEE and paid.status != PaymentStatus.PAYE:
        raise AppError(409, "NOT_PAID", "Cette commande sera confirmée par son paiement.")
    if origin == S.ECHEC_LIVRAISON and to == S.EN_LIVRAISON:
        _check_retry(db, order)
    lines = {i.variant_id: i.quantity for i in items(db, order)}
    if to == S.ANNULEE:
        inventory.release(db, lines, order_id=order.id, user_id=actor_id)  # RG-14
        if (
            paid.status != PaymentStatus.PAYE
        ):  # payée en ligne : reste « Payé » jusqu'au remboursement
            paid.status = PaymentStatus.ANNULE
        order.cancel_reason = note or None
    elif to == S.EN_LIVRAISON:
        courier = db.get(User, courier_id) if courier_id is not None else None
        if courier is None or courier.role != UserRole.COURIER or not courier.is_active:
            raise AppError(422, "COURIER_REQUIRED", "Attribuez un livreur actif (RG-41).")
        if origin == S.EN_PREPARATION:  # une nouvelle tentative n'a plus rien à sortir
            inventory.ship(db, lines, order_id=order.id, user_id=actor_id)  # RG-13
        order.courier_id = courier.id
        order.delivery_attempts += 1
    elif to == S.LIVREE and paid.method == PaymentMethod.CASH_ON_DELIVERY:
        # RG-43 : livrée implique encaissée, par le livreur de la commande
        paid.status = PaymentStatus.ENCAISSE
        paid.collected_by = order.courier_id
        paid.collected_at = datetime.now(UTC)
    order.status = to
    db.add(
        OrderEvent(
            order_id=order.id,
            kind=EventKind.STATUS_CHANGE,
            from_status=origin,
            to_status=to,
            failure_reason=failure_reason,
            note=note or None,
            user_id=actor_id,
        )
    )
    audit(
        db,
        actor_id=actor_id,
        action="order.status",
        entity_type="order",
        entity_id=order.number,
        before={"status": origin.value},
        after={"status": to.value, "note": note or None, "courier_id": order.courier_id},
    )


def deliver(db: Session, order: Order, amount_collected: int, *, actor_id: int) -> None:
    """Le livreur confirme avoir reçu le montant total exact (RG-43, US-23) ; rien pour une
    commande déjà payée par mobile money."""
    due = amount_due(db, order)
    if order.status == S.EN_LIVRAISON and amount_collected != due:
        raise AppError(
            422,
            "AMOUNT_MISMATCH",
            f"Le montant encaissé doit être exactement {fcfa(due)}.",
            {"total": due},
        )
    note = f"Encaissé : {fcfa(due)}" if due else "Déjà payée par mobile money"
    transition(db, order, S.LIVREE, actor_id=actor_id, note=note)


def amount_due(db: Session, order: Order) -> int:
    return 0 if payment(db, order).method == PaymentMethod.MOBILE_MONEY else order.total


def _last_failure(db: Session, order: Order) -> FailureReason | None:
    return db.scalar(
        select(OrderEvent.failure_reason)
        .where(OrderEvent.order_id == order.id, OrderEvent.failure_reason.is_not(None))
        .order_by(OrderEvent.id.desc())
        .limit(1)
    )


def _check_retry(db: Session, order: Order) -> None:
    """RG-44 : nouvelle tentative seulement si le client est injoignable ou a reporté, et
    2 tentatives au total ; sinon le colis revient à la boutique."""
    if _last_failure(db, order) not in RETRIABLE:
        raise AppError(
            409, "NO_RETRY", "Le client a refusé ou l'adresse est introuvable : retour boutique."
        )
    if order.delivery_attempts >= MAX_DELIVERY_ATTEMPTS:
        raise AppError(
            409,
            "NO_RETRY",
            f"{MAX_DELIVERY_ATTEMPTS} tentatives déjà faites : le colis revient à la boutique.",
        )


def fail_delivery(
    db: Session, order: Order, reason: FailureReason, note: str, *, actor_id: int
) -> None:
    transition(db, order, S.ECHEC_LIVRAISON, actor_id=actor_id, note=note, failure_reason=reason)


def receive_return(
    db: Session,
    order: Order,
    lines: Mapping[int, tuple[int, int]],
    *,
    actor_id: int,
    note: str,
    refund_amount: int | None,
) -> None:
    """Colis revenu (RG-15) ou retour d'une commande livrée (RG-46). Chaque article est
    contrôlé : remis en stock (« Retour ») ou perdu (« Perte »)."""
    ordered = {i.variant_id: i.quantity for i in items(db, order)}
    if set(lines) != set(ordered) or any(
        sum(lines[v]) != quantity for v, quantity in ordered.items()
    ):
        raise AppError(
            422,
            "INVALID_RETURN",
            "Indiquez, pour chaque article, combien reviennent en stock et combien sont perdus.",
        )
    paid = payment(db, order)
    if paid.status == PaymentStatus.ENCAISSE:
        raise AppError(
            409,
            "CASH_NOT_REMITTED",
            "Enregistrez d'abord la remise de caisse du livreur pour cette commande.",
        )
    if paid.status in (PaymentStatus.REMIS, PaymentStatus.PAYE):  # l'argent est à la boutique
        if refund_amount is None or not 0 <= refund_amount <= order.total:
            raise AppError(
                422,
                "REFUND_REQUIRED",
                f"Indiquez le montant remboursé (de 0 à {fcfa(order.total)}).",
            )
        paid.status = PaymentStatus.REMBOURSE
        paid.refunded_at = datetime.now(UTC)
        note = f"{note} — remboursé : {fcfa(refund_amount)}".lstrip(" —")
    else:
        paid.status = PaymentStatus.ANNULE
    transition(db, order, S.RETOURNEE, actor_id=actor_id, note=note)
    restocked = {v: r for v, (r, _) in lines.items() if r}
    if restocked:
        inventory.restock_return(db, restocked, order_id=order.id, user_id=actor_id)
    for variant_id, (_, lost) in lines.items():
        if lost:
            inventory.record_loss(
                db,
                variant_id,
                lost,
                order_id=order.id,
                user_id=actor_id,
                reason=note or "Produit abîmé",
            )


def record_call(db: Session, order: Order, result: CallResult, note: str, *, actor_id: int) -> None:
    """RG-30 : chaque appel est noté ; un appel concluant confirme la commande."""
    if order.status in FINAL:
        raise AppError(409, "ORDER_CLOSED", "Cette commande est close.")
    db.add(
        OrderEvent(
            order_id=order.id,
            kind=EventKind.CALL,
            call_result=result,
            note=note or None,
            user_id=actor_id,
        )
    )
    if result == CallResult.CONFIRMEE and order.status == S.EN_ATTENTE_CONFIRMATION:
        transition(db, order, S.CONFIRMEE, actor_id=actor_id, note="Confirmée par téléphone")


def call_counts(events: list[OrderEvent]) -> Counter[CallResult]:
    return Counter(e.call_result for e in events if e.call_result is not None)


def apply_notification(db: Session, notice: Notification) -> tuple[Order, bool]:
    """Avis de paiement déjà vérifié par le prestataire. Idempotent : un avis rejoué ou un échec
    ne change rien (la commande expire seule). Renvoie (commande, paiement enregistré ?)."""
    order = locked(db, notice.order_number)
    paid = payment(db, order)
    if paid.method != PaymentMethod.MOBILE_MONEY:
        raise AppError(409, "NOT_MOBILE_MONEY", "Cette commande se paie à la livraison.")
    if notice.amount != paid.amount:
        raise AppError(409, "AMOUNT_MISMATCH", "Montant payé différent du montant de la commande.")
    # ANNULE : commande expirée ou annulée avant l'avis ; l'argent est bien reçu, on l'enregistre.
    if not notice.paid or paid.status not in (PaymentStatus.A_PAYER, PaymentStatus.ANNULE):
        return order, False
    before = paid.status
    paid.status = PaymentStatus.PAYE
    paid.collected_at = datetime.now(UTC)
    paid.provider_ref = notice.provider_ref
    if order.status == S.EN_ATTENTE_PAIEMENT:
        transition(db, order, S.CONFIRMEE, actor_id=None, note="Payée par mobile money")
    else:  # annulée entre-temps (délai dépassé, client) : l'argent est reçu, il faut rembourser
        db.add(
            OrderEvent(
                order_id=order.id,
                kind=EventKind.NOTE,
                note=f"Paiement reçu après annulation : {fcfa(paid.amount)} à rembourser.",
            )
        )
    audit(
        db,
        actor_id=None,
        action="payment.received",
        entity_type="order",
        entity_id=order.number,
        before={"status": before.value},
        after={"status": PaymentStatus.PAYE.value, "provider_ref": notice.provider_ref},
    )
    return order, True


def expire_unpaid(db: Session, now: datetime) -> list[Order]:
    """Commandes mobile money non payées dans le délai : annulées, stock libéré."""
    expired = list(
        db.scalars(
            select(Order)
            .where(Order.status == S.EN_ATTENTE_PAIEMENT, Order.created_at < now - PAYMENT_DELAY)
            .with_for_update(skip_locked=True)
        )
    )
    for order in expired:
        transition(
            db, order, S.ANNULEE, actor_id=None, note="Paiement non reçu dans les 30 minutes"
        )
    return expired


def refund_cancelled(db: Session, order: Order, amount: int, note: str, *, actor_id: int) -> None:
    """Remboursement, fait chez le prestataire, d'une commande annulée après son paiement."""
    paid = payment(db, order)
    if order.status != S.ANNULEE or paid.status != PaymentStatus.PAYE:
        raise AppError(409, "NOT_REFUNDABLE", "Aucun paiement à rembourser sur cette commande.")
    if not 0 < amount <= paid.amount:
        raise AppError(
            422, "REFUND_REQUIRED", f"Indiquez le montant remboursé (jusqu'à {fcfa(paid.amount)})."
        )
    paid.status = PaymentStatus.REMBOURSE
    paid.refunded_at = datetime.now(UTC)
    text = f"Remboursé : {fcfa(amount)}" + (f" — {note}" if note else "")
    db.add(OrderEvent(order_id=order.id, kind=EventKind.NOTE, note=text, user_id=actor_id))
    audit(
        db,
        actor_id=actor_id,
        action="payment.refund",
        entity_type="order",
        entity_id=order.number,
        before={"status": PaymentStatus.PAYE.value},
        after={"status": PaymentStatus.REMBOURSE.value, "amount": amount},
    )
