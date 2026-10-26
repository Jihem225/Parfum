import json
import uuid
from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core import rate_limit
from app.core.config import settings
from app.core.email import queue
from app.core.errors import AppError
from app.modules.auth.deps import DB, BackOffice, CurrentUser, Owner, client_ip
from app.modules.auth.models import User, UserRole
from app.modules.cart import service as cart_service
from app.modules.cart.router import CART_COOKIE, OptionalUser
from app.modules.catalog.queries import like
from app.modules.orders import notify, service
from app.modules.orders.models import (
    CallResult,
    EventKind,
    Order,
    OrderEvent,
    OrderItem,
    OrderStatus,
)
from app.modules.orders.schemas import (
    AdminOrderOut,
    AdminOrderPage,
    AdminOrderRow,
    CallIn,
    CancelIn,
    CheckoutIn,
    CheckoutPreview,
    EventOut,
    OrderLineOut,
    OrderOut,
    OrderSummary,
    PaymentLink,
    PaymentStart,
    PaymentState,
    PersonRef,
    PreviewIn,
    RefundIn,
    ReturnIn,
    SimulatedPayment,
    StatusStep,
    TrackIn,
    TransitionIn,
)
from app.modules.payments.models import Payment, PaymentMethod
from app.modules.payments.providers import get_provider, sign

public = APIRouter(tags=["commandes"])
admin = APIRouter(prefix="/admin/orders", tags=["admin: commandes"])

HOUR = 3600
ABIDJAN = ZoneInfo("Africa/Abidjan")


def _events(db: Session, order: Order) -> list[OrderEvent]:
    return list(
        db.scalars(
            select(OrderEvent).where(OrderEvent.order_id == order.id).order_by(OrderEvent.id)
        )
    )


def _out(db: Session, order: Order, *, can_cancel: bool = False) -> OrderOut:
    awaiting = order.status == OrderStatus.EN_ATTENTE_PAIEMENT
    return OrderOut(
        number=order.number,
        status=order.status,
        created_at=order.created_at,
        customer_name=order.customer_name,
        phone=order.phone,
        email=order.email,
        commune_name=order.commune_name,
        address_line=order.address_line,
        landmark=order.landmark,
        delivery_fee=order.delivery_fee,
        delivery_delay_label=order.delivery_delay_label,
        subtotal=order.subtotal,
        total=order.total,
        payment_method=service.payment(db, order).method,
        items=[
            OrderLineOut.model_validate(i, from_attributes=True) for i in service.items(db, order)
        ],
        history=[
            StatusStep(status=e.to_status, at=e.created_at)
            for e in _events(db, order)
            if e.kind == EventKind.STATUS_CHANGE and e.to_status is not None
        ],
        can_cancel=can_cancel and order.status in service.CANCELLABLE,
        payment_token=service.payment_token(order.number) if awaiting else None,
    )


def summaries(db: Session, user_id: int) -> list[OrderSummary]:
    """Commandes d'un compte, de la plus récente à la plus ancienne."""
    counts = (
        select(OrderItem.order_id, func.sum(OrderItem.quantity).label("n"))
        .group_by(OrderItem.order_id)
        .subquery()
    )
    rows = db.execute(
        select(Order, counts.c.n)
        .join(counts, counts.c.order_id == Order.id)
        .where(Order.user_id == user_id)
        .order_by(Order.id.desc())
    )
    return [
        OrderSummary(
            number=o.number, status=o.status, created_at=o.created_at, total=o.total, item_count=n
        )
        for o, n in rows
    ]


# --- Boutique ------------------------------------------------------------------------------------


@public.post("/checkout/preview")
def preview_order(data: PreviewIn, request: Request, user: OptionalUser, db: DB) -> CheckoutPreview:
    cart = cart_service.view(db, cart_service.find(db, user, request.cookies.get(CART_COOKIE)))
    commune = service.served_commune(db, data.commune_id)
    total = cart.subtotal + commune.delivery_fee
    cod = data.payment_method == PaymentMethod.CASH_ON_DELIVERY
    return CheckoutPreview(
        cart=cart,
        commune_name=commune.name,
        delivery_fee=commune.delivery_fee,
        delivery_delay_label=commune.delay_label,
        total=total,
        exceeds_cod_limit=total > cart_service.COD_LIMIT,
        can_order=bool(cart.items)
        and all(line.issue is None for line in cart.items)
        and (total <= cart_service.COD_LIMIT if cod else get_provider() is not None),
    )


@public.post("/orders", status_code=201)
def place_order(data: CheckoutIn, request: Request, user: OptionalUser, db: DB) -> OrderOut:
    rate_limit.limit(f"order:ip:{client_ip(request)}", 10, HOUR)  # RG-51
    cart = cart_service.find(db, user, request.cookies.get(CART_COOKIE))
    order, created = service.checkout(db, data, cart=cart, user=user)
    if (
        created and order.status == OrderStatus.EN_ATTENTE_CONFIRMATION
    ):  # mobile money : au paiement
        queue(db, notify.to_customer(order), notify.to_shop(order, service.items(db, order)))
    db.commit()
    return _out(db, order, can_cancel=user is not None and order.user_id == user.id)


@public.post("/orders/track")
def track_order(data: TrackIn, request: Request, db: DB) -> OrderOut:
    """Suivi invité (US-07) : réponse identique que le numéro ou le téléphone soit faux."""
    rate_limit.limit(f"track:ip:{client_ip(request)}", 20, HOUR)
    rate_limit.limit(f"track:number:{data.number}", 10, HOUR)
    order = db.scalar(select(Order).where(Order.number == data.number, Order.phone == data.phone))
    if order is None:
        raise AppError(
            404, "NOT_FOUND", "Aucune commande ne correspond à ce numéro et ce téléphone."
        )
    return _out(db, order)


def _mine(db: Session, user: User, number: str, *, lock: bool = False) -> Order:
    query = select(Order).where(Order.number == number.upper(), Order.user_id == user.id)
    order = db.scalar(query.with_for_update() if lock else query)
    if order is None:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    return order


@public.get("/me/orders")
def my_orders(user: CurrentUser, db: DB) -> list[OrderSummary]:
    return summaries(db, user.id)


@public.get("/me/orders/{number}")
def my_order(number: str, user: CurrentUser, db: DB) -> OrderOut:
    return _out(db, _mine(db, user, number), can_cancel=True)


@public.post("/me/orders/{number}/cancel")
def cancel_my_order(number: str, data: CancelIn, user: CurrentUser, db: DB) -> OrderOut:
    """RG-32 : possible tant que la commande n'est pas partie en livraison."""
    order = _mine(db, user, number, lock=True)
    if order.status not in service.CANCELLABLE:
        raise AppError(
            409, "NOT_CANCELLABLE", "Votre commande est déjà en route : contactez la boutique."
        )
    service.transition(
        db,
        order,
        OrderStatus.ANNULEE,
        actor_id=user.id,
        note=data.reason or "Annulée par le client",
    )
    queue(db, notify.to_customer(order))
    db.commit()
    return _out(db, order, can_cancel=True)


# --- Paiement mobile money ---------------------------------------------------------------------


@public.post("/orders/{number}/payment")
def start_payment(number: str, data: PaymentStart, db: DB) -> PaymentLink:
    """Ouvre (ou rouvre après un échec) la page de paiement du prestataire."""
    service.check_payment_token(number, data.token)
    provider = get_provider()
    order = db.scalar(select(Order).where(Order.number == number.upper()))
    if provider is None or order is None or order.status != OrderStatus.EN_ATTENTE_PAIEMENT:
        raise AppError(409, "NOT_PAYABLE", "Cette commande n'attend plus de paiement.")
    back = f"{settings.frontend_origin}/commande/paiement?numero={order.number}&t={data.token}"
    return PaymentLink(url=provider.checkout_url(order.number, order.total, back))


@public.get("/orders/{number}/payment")
def payment_state(number: str, token: str, db: DB) -> PaymentState:
    service.check_payment_token(number, token)
    order = db.scalar(select(Order).where(Order.number == number.upper()))
    if order is None:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    return PaymentState(order_status=order.status, payment_status=service.payment(db, order).status)


def _notified(db: DB, body: bytes, headers: dict[str, str]) -> None:
    provider = get_provider()
    if provider is None:
        raise AppError(404, "NOT_FOUND", "Paiement en ligne désactivé.")
    order, recorded = service.apply_notification(db, provider.read(body, headers))
    if recorded and order.status == OrderStatus.CONFIRMEE:
        items = service.items(db, order)
        queue(db, notify.to_customer(order), notify.to_shop(order, items, prepaid=True))
    elif recorded:
        queue(db, notify.late_payment(order))
    db.commit()


@public.post("/payments/notifications")
async def payment_notification(request: Request, db: DB) -> dict[str, bool]:
    """Avis du prestataire (sans cookie : exempté du CSRF, authentifié par sa signature calculée
    sur les octets bruts)."""
    _notified(db, await request.body(), dict(request.headers))
    return {"received": True}


@public.post("/payments/simulation/{number}")
def simulate_payment(number: str, data: SimulatedPayment, db: DB) -> PaymentState:
    """Développement et CI uniquement : produit l'avis signé qu'enverrait un prestataire."""
    if settings.payment_provider != "simulation":
        raise AppError(404, "NOT_FOUND", "Simulation désactivée.")
    service.check_payment_token(number, data.token)
    order = db.scalar(select(Order).where(Order.number == number.upper()))
    if order is None:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    body = json.dumps(
        {
            "id": f"sim-{uuid.uuid4().hex[:12]}",
            "order_number": order.number,
            "amount": order.total,
            "status": "paid" if data.paid else "failed",
        }
    ).encode()
    _notified(db, body, {"x-signature": sign(body)})
    return PaymentState(order_status=order.status, payment_status=service.payment(db, order).status)


# --- Back-office ---------------------------------------------------------------------------------


@admin.get("")
def list_orders(
    _: BackOffice,
    db: DB,
    status: OrderStatus | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    commune: Annotated[str | None, Query(max_length=80)] = None,
    courier_id: int | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AdminOrderPage:
    """F-43 : filtres statut, période (jours d'Abidjan), commune, livreur ; recherche par
    numéro, nom ou téléphone."""
    filters = []
    if status:
        filters.append(Order.status == status)
    if date_from:
        filters.append(Order.created_at >= datetime.combine(date_from, time(), ABIDJAN))
    if date_to:
        end = datetime.combine(date_to + timedelta(days=1), time(), ABIDJAN)
        filters.append(Order.created_at < end)
    if commune:
        filters.append(Order.commune_name == commune)
    if courier_id:
        filters.append(Order.courier_id == courier_id)
    if q:
        digits = "".join(ch for ch in q if ch.isdigit())
        filters.append(
            or_(
                like(Order.number, q),
                like(Order.customer_name, q),
                *([Order.phone.contains(digits)] if len(digits) >= 4 else []),
            )
        )
    total = db.scalar(select(func.count()).select_from(Order).where(*filters)) or 0
    courier = aliased(User)
    rows = db.execute(
        select(Order, Payment.status, courier.full_name)
        .join(Payment, Payment.order_id == Order.id)
        .outerjoin(courier, courier.id == Order.courier_id)
        .where(*filters)
        .order_by(Order.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return AdminOrderPage(
        items=[
            AdminOrderRow(
                number=o.number,
                status=o.status,
                created_at=o.created_at,
                customer_name=o.customer_name,
                phone=o.phone,
                commune_name=o.commune_name,
                total=o.total,
                payment_status=payment_status,
                courier_name=courier_name,
            )
            for o, payment_status, courier_name in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def _admin_out(db: Session, order: Order) -> AdminOrderOut:
    events = _events(db, order)
    authors = {
        u.id: u.full_name
        for u in db.scalars(select(User).where(User.id.in_({e.user_id for e in events})))
    }
    courier = db.get(User, order.courier_id) if order.courier_id else None
    unanswered = service.call_counts(events)[CallResult.PAS_DE_REPONSE]
    return AdminOrderOut(
        **_out(db, order).model_dump(exclude={"can_cancel"}),
        can_cancel=order.status in service.CANCELLABLE,
        id=order.id,
        user_id=order.user_id,
        payment_status=service.payment(db, order).status,
        courier=PersonRef(id=courier.id, full_name=courier.full_name) if courier else None,
        delivery_attempts=order.delivery_attempts,
        cancel_reason=order.cancel_reason,
        events=[
            EventOut(
                kind=e.kind,
                from_status=e.from_status,
                to_status=e.to_status,
                call_result=e.call_result,
                failure_reason=e.failure_reason,
                note=e.note,
                author=authors.get(e.user_id) if e.user_id else None,
                at=e.created_at,
            )
            for e in events
        ],
        unanswered_calls=unanswered,
        should_cancel=order.status == OrderStatus.EN_ATTENTE_CONFIRMATION
        and unanswered >= service.MAX_UNANSWERED_CALLS,
    )


@admin.get("/{number}")
def get_order(number: str, _: BackOffice, db: DB) -> AdminOrderOut:
    order = db.scalar(select(Order).where(Order.number == number.upper()))
    if order is None:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    return _admin_out(db, order)


@admin.post("/{number}/calls", status_code=201)
def add_call(number: str, data: CallIn, user: BackOffice, db: DB) -> AdminOrderOut:
    order = service.locked(db, number)
    before = order.status
    service.record_call(db, order, data.result, data.note, actor_id=user.id)
    if order.status != before:
        queue(db, notify.to_customer(order))
    db.commit()
    return _admin_out(db, order)


@admin.post("/{number}/transition")
def change_status(number: str, data: TransitionIn, user: BackOffice, db: DB) -> AdminOrderOut:
    if data.to == OrderStatus.ANNULEE and not data.note:
        raise AppError(422, "REASON_REQUIRED", "Indiquez le motif de l'annulation.")
    order = service.locked(db, number)
    service.transition(
        db, order, data.to, actor_id=user.id, note=data.note, courier_id=data.courier_id
    )
    prepaid = service.payment(db, order).method == PaymentMethod.MOBILE_MONEY
    queue(db, notify.to_customer(order, prepaid=prepaid))
    db.commit()
    return _admin_out(db, order)


@admin.post("/{number}/refund")
def refund_order(number: str, data: RefundIn, user: Owner, db: DB) -> AdminOrderOut:
    """Commande payée par mobile money puis annulée : remboursement fait chez le prestataire."""
    order = service.locked(db, number)
    service.refund_cancelled(db, order, data.amount, data.note, actor_id=user.id)
    db.commit()
    return _admin_out(db, order)


@admin.post("/{number}/return")
def return_order(number: str, data: ReturnIn, user: BackOffice, db: DB) -> AdminOrderOut:
    """Colis revenu après échec (Gestionnaire) ou retour d'une commande livrée, avec
    remboursement (Propriétaire seulement, RG-46)."""
    order = service.locked(db, number)
    if order.status == OrderStatus.LIVREE and user.role != UserRole.OWNER:
        raise AppError(
            403, "FORBIDDEN", "Seul le Propriétaire traite le retour d'une commande livrée."
        )
    service.receive_return(
        db,
        order,
        {line.variant_id: (line.restocked, line.lost) for line in data.items},
        actor_id=user.id,
        note=data.note,
        refund_amount=data.refund_amount,
    )
    db.commit()
    return _admin_out(db, order)
