"""Espace livreur (mobile) : ses livraisons en cours et leur clôture."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.email import send_email
from app.core.errors import AppError
from app.modules.auth.deps import DB, require_roles
from app.modules.auth.models import User, UserRole
from app.modules.orders import notify, service
from app.modules.orders.models import Order, OrderStatus

router = APIRouter(prefix="/courier/deliveries", tags=["livreur"])

Deliverer = Annotated[
    User, Depends(require_roles(UserRole.COURIER, UserRole.MANAGER, UserRole.OWNER))
]


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


@router.post("/{number}/delivered")
def mark_delivered(
    number: str, data: DeliveredIn, user: Deliverer, db: DB, background: BackgroundTasks
) -> DeliveryOut:
    order = service.locked(db, number)
    if user.role == UserRole.COURIER and order.courier_id != user.id:
        raise AppError(404, "NOT_FOUND", "Commande introuvable.")
    service.deliver(db, order, data.amount_collected, actor_id=user.id)
    db.commit()
    message = notify.to_customer(order)
    if message is not None:
        background.add_task(send_email, *message)
    return _out(db, order)
