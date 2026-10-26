"""Commandes : création depuis le panier, machine à états (§6.1), appels de confirmation.
Chaque changement écrit statut, stock, paiement, historique et audit dans la même transaction."""

from collections import Counter
from datetime import UTC, datetime

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
    Order,
    OrderEvent,
    OrderItem,
    OrderStatus,
    order_number_seq,
)
from app.modules.orders.notify import fcfa
from app.modules.orders.schemas import CheckoutIn
from app.modules.payments.models import Payment, PaymentStatus

S = OrderStatus
TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    S.EN_ATTENTE_CONFIRMATION: {S.CONFIRMEE, S.ANNULEE},
    S.CONFIRMEE: {S.EN_PREPARATION, S.ANNULEE},
    S.EN_PREPARATION: {S.EN_LIVRAISON, S.ANNULEE},
    S.EN_LIVRAISON: {S.LIVREE, S.ECHEC_LIVRAISON},
    S.ECHEC_LIVRAISON: {S.EN_LIVRAISON, S.RETOURNEE},
    S.LIVREE: {S.RETOURNEE},
    S.RETOURNEE: set(),
    S.ANNULEE: set(),
}
CANCELLABLE = {S.EN_ATTENTE_CONFIRMATION, S.CONFIRMEE, S.EN_PREPARATION}  # RG-32
FINAL = {S.LIVREE, S.RETOURNEE, S.ANNULEE}
MAX_UNANSWERED_CALLS = 3  # RG-31

LABELS = {
    S.EN_ATTENTE_CONFIRMATION: "En attente de confirmation",
    S.CONFIRMEE: "Confirmée",
    S.EN_PREPARATION: "En préparation",
    S.EN_LIVRAISON: "En livraison",
    S.LIVREE: "Livrée",
    S.ECHEC_LIVRAISON: "Échec de livraison",
    S.RETOURNEE: "Retournée",
    S.ANNULEE: "Annulée",
}


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
    total = summary.subtotal + commune.delivery_fee
    if total > cart_service.COD_LIMIT:
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
            {"subtotal": summary.subtotal, "delivery_fee": commune.delivery_fee, "total": total},
        )

    order = Order(
        number=f"{settings.order_number_prefix}-{db.scalar(order_number_seq.next_value())}",
        user_id=user.id if user else None,
        status=S.EN_ATTENTE_CONFIRMATION,
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
        total=total,
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
    db.add(Payment(order_id=order.id, amount=total, status=PaymentStatus.A_ENCAISSER))
    db.add(
        OrderEvent(
            order_id=order.id,
            kind=EventKind.STATUS_CHANGE,
            to_status=S.EN_ATTENTE_CONFIRMATION,
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
) -> None:
    """Seules les transitions du §6.1 passent ; les rôles sont contrôlés par les routes."""
    origin = order.status
    if to not in TRANSITIONS[origin]:
        raise AppError(
            409,
            "INVALID_TRANSITION",
            f"Impossible de passer de « {LABELS[origin]} » à « {LABELS[to]} ».",
        )
    lines = {i.variant_id: i.quantity for i in items(db, order)}
    if to == S.ANNULEE:
        inventory.release(db, lines, order_id=order.id, user_id=actor_id)  # RG-14
        payment(db, order).status = PaymentStatus.ANNULE
        order.cancel_reason = note or None
    elif to == S.EN_LIVRAISON:
        courier = db.get(User, courier_id) if courier_id is not None else None
        if courier is None or courier.role != UserRole.COURIER or not courier.is_active:
            raise AppError(422, "COURIER_REQUIRED", "Attribuez un livreur actif (RG-41).")
        if origin == S.EN_PREPARATION:  # une nouvelle tentative n'a plus rien à sortir
            inventory.ship(db, lines, order_id=order.id, user_id=actor_id)  # RG-13
        order.courier_id = courier.id
        order.delivery_attempts += 1
    elif to == S.LIVREE:  # RG-43 : livrée implique encaissée, par le livreur de la commande
        paid = payment(db, order)
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
    """Le livreur confirme avoir reçu le montant total exact (RG-43, US-23)."""
    if order.status == S.EN_LIVRAISON and amount_collected != order.total:
        raise AppError(
            422,
            "AMOUNT_MISMATCH",
            f"Le montant encaissé doit être exactement {fcfa(order.total)}.",
            {"total": order.total},
        )
    transition(db, order, S.LIVREE, actor_id=actor_id, note=f"Encaissé : {fcfa(order.total)}")


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
