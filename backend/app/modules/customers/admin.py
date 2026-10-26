"""Clients au back-office (F-45) : liste et fiche avec l'historique des commandes."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import Select, func, or_, select

from app.core.errors import AppError
from app.modules.auth.deps import DB, BackOffice
from app.modules.auth.models import User, UserRole
from app.modules.catalog.queries import like
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.router import summaries
from app.modules.orders.schemas import OrderSummary

admin = APIRouter(prefix="/admin/customers", tags=["admin: clients"])


class CustomerRow(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str
    is_active: bool
    created_at: datetime
    orders_count: int
    delivered_total: int  # montant des commandes livrées, frais compris


class CustomerPage(BaseModel):
    items: list[CustomerRow]
    total: int
    page: int
    page_size: int


class CustomerDetail(CustomerRow):
    orders: list[OrderSummary]


_orders = (
    select(
        Order.user_id,
        func.count().label("n"),
        func.coalesce(func.sum(Order.total).filter(Order.status == OrderStatus.LIVREE), 0).label(
            "delivered"
        ),
    )
    .group_by(Order.user_id)
    .subquery()
)


def _query() -> Select[User, int, int]:
    return (
        select(User, func.coalesce(_orders.c.n, 0), func.coalesce(_orders.c.delivered, 0))
        .outerjoin(_orders, _orders.c.user_id == User.id)
        .where(User.role == UserRole.CUSTOMER)
    )


def _row(user: User, n: int, delivered: int) -> CustomerRow:
    return CustomerRow(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        is_active=user.is_active,
        created_at=user.created_at,
        orders_count=n,
        delivered_total=delivered,
    )


@admin.get("")
def list_customers(
    _: BackOffice,
    db: DB,
    q: Annotated[str | None, Query(max_length=80)] = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> CustomerPage:
    query = _query()
    if q:
        digits = "".join(ch for ch in q if ch.isdigit())
        query = query.where(
            or_(
                like(User.full_name, q),
                like(User.email, q),
                *([User.phone.contains(digits)] if len(digits) >= 4 else []),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.execute(
        query.order_by(User.id.desc()).limit(page_size).offset((page - 1) * page_size)
    )
    return CustomerPage(
        items=[_row(u, n, d) for u, n, d in rows], total=total, page=page, page_size=page_size
    )


@admin.get("/{customer_id}")
def get_customer(customer_id: int, _: BackOffice, db: DB) -> CustomerDetail:
    row = db.execute(_query().where(User.id == customer_id)).first()
    if row is None:
        raise AppError(404, "NOT_FOUND", "Client introuvable.")
    user, n, delivered = row
    return CustomerDetail(**_row(user, n, delivered).model_dump(), orders=summaries(db, user.id))
