"""Tableau de bord (F-40, US-40) : indicateurs d'une période en jours d'Abidjan."""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import and_, func, select

from app.core.errors import AppError
from app.core.models import EmailMessage, EmailStatus
from app.modules.auth.deps import DB, BackOffice
from app.modules.catalog.models import ProductVariant
from app.modules.contact.models import ContactMessage, MessageStatus
from app.modules.orders.models import Order, OrderItem, OrderStatus
from app.modules.payments.models import Payment, PaymentStatus

admin = APIRouter(prefix="/admin/dashboard", tags=["admin: tableau de bord"])

ABIDJAN = ZoneInfo("Africa/Abidjan")
MAX_DAYS = 366
TO_PROCESS = (
    OrderStatus.EN_ATTENTE_CONFIRMATION,
    OrderStatus.CONFIRMEE,
    OrderStatus.EN_PREPARATION,
    OrderStatus.ECHEC_LIVRAISON,
)


class BestSeller(BaseModel):
    product_name: str
    volume_ml: int
    quantity: int
    revenue: int


class DashboardOut(BaseModel):
    date_from: date
    date_to: date
    revenue: int  # commandes livrées et encaissées sur la période, hors frais de livraison
    delivery_fees: int
    delivered_orders: int
    average_basket: int | None
    orders_created: int
    orders_by_status: dict[OrderStatus, int]  # commandes passées sur la période
    delivery_success_rate: float | None  # % livrées parmi les livrées + revenues sans livraison
    best_sellers: list[BestSeller]
    to_process: dict[OrderStatus, int]  # à l'instant, toutes périodes confondues
    low_stock_variants: int
    cash_held_by_couriers: int
    new_contact_messages: int
    failed_emails: int  # abandonnés après le dernier essai : à renvoyer


@admin.get("")
def dashboard(
    _: BackOffice, db: DB, date_from: date | None = None, date_to: date | None = None
) -> DashboardOut:
    date_to = date_to or datetime.now(ABIDJAN).date()
    date_from = date_from or date_to - timedelta(days=29)
    if not 0 <= (date_to - date_from).days < MAX_DAYS:
        raise AppError(422, "INVALID_PERIOD", f"Période de 1 à {MAX_DAYS} jours.")
    start = datetime.combine(date_from, time(), ABIDJAN)
    end = datetime.combine(date_to + timedelta(days=1), time(), ABIDJAN)

    delivered = and_(
        Order.status == OrderStatus.LIVREE,
        Payment.collected_at >= start,
        Payment.collected_at < end,
    )
    revenue, fees, delivered_count = db.execute(
        select(
            func.coalesce(func.sum(Order.subtotal), 0),
            func.coalesce(func.sum(Order.delivery_fee), 0),
            func.count(),
        )
        .select_from(Order)
        .join(Payment, Payment.order_id == Order.id)
        .where(delivered)
    ).one()

    created = and_(Order.created_at >= start, Order.created_at < end)
    by_status = {
        status: n
        for status, n in db.execute(
            select(Order.status, func.count()).where(created).group_by(Order.status)
        )
    }
    succeeded, returned = db.execute(
        select(
            func.count().filter(Payment.collected_at.is_not(None)),
            func.count().filter(
                Order.status == OrderStatus.RETOURNEE, Payment.collected_at.is_(None)
            ),
        )
        .select_from(Order)
        .join(Payment, Payment.order_id == Order.id)
        .where(created)
    ).one()

    sold = func.sum(OrderItem.quantity)
    best = db.execute(
        select(
            func.max(OrderItem.product_name),
            func.max(OrderItem.volume_ml),
            sold,
            func.sum(OrderItem.line_total),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .join(Payment, Payment.order_id == Order.id)
        .where(delivered)
        .group_by(OrderItem.variant_id)
        .order_by(sold.desc())
        .limit(5)
    )
    to_process = {
        status: n
        for status, n in db.execute(
            select(Order.status, func.count())
            .where(Order.status.in_(TO_PROCESS))
            .group_by(Order.status)
        )
    }
    available = ProductVariant.stock_physical - ProductVariant.stock_reserved
    low = db.scalar(
        select(func.count()).where(
            ProductVariant.is_active, available <= ProductVariant.low_stock_threshold
        )
    )
    cash = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.ENCAISSE, Payment.remittance_id.is_(None)
        )
    )
    messages = db.scalar(select(func.count()).where(ContactMessage.status == MessageStatus.NOUVEAU))
    failed = db.scalar(select(func.count()).where(EmailMessage.status == EmailStatus.FAILED))
    return DashboardOut(
        date_from=date_from,
        date_to=date_to,
        revenue=revenue,
        delivery_fees=fees,
        delivered_orders=delivered_count,
        average_basket=revenue // delivered_count if delivered_count else None,
        orders_created=sum(by_status.values()),
        orders_by_status=by_status,
        delivery_success_rate=round(100 * succeeded / (succeeded + returned), 1)
        if succeeded + returned
        else None,
        best_sellers=[
            BestSeller(product_name=n, volume_ml=v, quantity=q, revenue=r) for n, v, q, r in best
        ],
        to_process=to_process,
        low_stock_variants=low or 0,
        cash_held_by_couriers=cash or 0,
        new_contact_messages=messages or 0,
        failed_emails=failed or 0,
    )
