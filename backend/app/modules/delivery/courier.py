"""Espace livreur (mobile) : ses livraisons en cours et leur clôture."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.email import send_email
from app.core.errors import AppError
from app.modules.auth.deps import DB, BackOffice, require_roles
from app.modules.auth.models import User, UserRole
from app.modules.orders import notify, service
from app.modules.orders.models import FailureReason, Order, OrderStatus

router = APIRouter(prefix="/courier/deliveries", tags=["livreur"])
admin = APIRouter(prefix="/admin/couriers", tags=["admin: commandes"])

Deliverer = Annotated[
    User, Depends(require_roles(UserRole.COURIER, UserRole.MANAGER, UserRole.OWNER))
]


class CourierOut(BaseModel):
    id: int
    full_name: str
    phone: str


@admin.get("")
def active_couriers(_: BackOffice, db: DB) -> list[CourierOut]:
    """Livreurs actifs, pour l'attribution d'une commande (RG-41). La gestion complète de
    l'équipe reste réservée au Propriétaire."""
    couriers = db.scalars(
        select(User)
        .where(User.role == UserRole.COURIER, User.is_active.is_(True))
        .order_by(User.full_name)
    )
    return [CourierOut(id=u.id, full_name=u.full_name, phone=u.phone) for u in couriers]


class DeliveryItem(BaseModel):
    product_name: str
    volume_ml: int
    quantity: int


class DeliveryOut(BaseModel):
    number: str
    status: OrderStatus
    customer_name: str
    phone: str
    commune_name: str
    address_line: str
    landmark: str | None
    amount_to_collect: int
    delivery_attempts: int
    items: list[DeliveryItem]


class DeliveredIn(BaseModel):
    amount_collected: Annotated[int, Field(ge=0)]


class FailedIn(BaseModel):
    reason: FailureReason
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


def _out(db: Session, order: Order) -> DeliveryOut:
    return DeliveryOut(
        number=order.number,
        status=order.status,
        customer_name=order.customer_name,
        phone=order.phone,
        commune_name=order.commune_name,
        address_line=order.address_line,
        landmark=order.landmark,
        amount_to_collect=order.total,
        delivery_attempts=order.delivery_attempts,
        items=[
            DeliveryItem(product_name=i.product_name, volume_ml=i.volume_ml, quantity=i.quantity)
            for i in service.items(db, order)
        ],
    )


@router.get("")
def my_deliveries(user: Deliverer, db: DB) -> list[DeliveryOut]:
    """RG-42 : un livreur ne voit que ses commandes « En livraison »."""
    query = select(Order).where(Order.status == OrderStatus.EN_LIVRAISON)
    if user.role == UserRole.COURIER:
        query = query.where(Order.courier_id == user.id)
    return [_out(db, o) for o in db.scalars(query.order_by(Order.commune_name, Order.id))]


def _assigned(db: Session, user: User, number: str) -> Order:
    order = service.locked(db, number)
    if user.role == UserRole.COURIER and order.courier_id != user.id:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    return order


@router.post("/{number}/failed")
def mark_failed(number: str, data: FailedIn, user: Deliverer, db: DB) -> DeliveryOut:
    """F-61 : échec avec motif ; le colis reste chez le livreur jusqu'à la décision de la
    boutique (nouvelle tentative ou retour)."""
    order = _assigned(db, user, number)
    service.fail_delivery(db, order, data.reason, data.note, actor_id=user.id)
    db.commit()
    return _out(db, order)


@router.post("/{number}/delivered")
def mark_delivered(
    number: str, data: DeliveredIn, user: Deliverer, db: DB, background: BackgroundTasks
) -> DeliveryOut:
    order = _assigned(db, user, number)
    service.deliver(db, order, data.amount_collected, actor_id=user.id)
    db.commit()
    message = notify.to_customer(order)
    if message is not None:
        background.add_task(send_email, *message)
    return _out(db, order)
