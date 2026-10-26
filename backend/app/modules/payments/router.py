"""Encaissements (F-44) : espèces détenues par chaque livreur et remises de caisse (RG-45)."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.errors import AppError
from app.modules.auth.deps import DB, BackOffice
from app.modules.auth.models import User
from app.modules.orders.models import Order
from app.modules.orders.notify import fcfa
from app.modules.orders.schemas import PersonRef
from app.modules.payments.models import CashRemittance, Payment, PaymentStatus
from app.modules.payments.schemas import (
    PendingCash,
    PendingOrder,
    RemittanceIn,
    RemittanceOut,
    RemittancePage,
)

admin = APIRouter(prefix="/admin", tags=["admin: encaissements"])

_PENDING = (Payment.status == PaymentStatus.ENCAISSE, Payment.remittance_id.is_(None))


def _person(db: Session, user_id: int) -> PersonRef:
    user = db.get_one(User, user_id)
    return PersonRef(id=user.id, full_name=user.full_name)


def _pending(db: Session, courier_id: int) -> PendingCash:
    rows = db.execute(
        select(Payment, Order.number)
        .join(Order, Order.id == Payment.order_id)
        .where(*_PENDING, Payment.collected_by == courier_id)
        .order_by(Payment.collected_at)
    ).all()
    return PendingCash(
        courier=_person(db, courier_id),
        amount=sum(p.amount for p, _ in rows),
        orders=[
            PendingOrder(number=number, amount=p.amount, collected_at=p.collected_at)
            for p, number in rows
        ],
    )


@admin.get("/couriers/pending-cash")
def pending_cash(_: BackOffice, db: DB) -> list[PendingCash]:
    couriers = db.scalars(
        select(Payment.collected_by).where(*_PENDING).group_by(Payment.collected_by)
    )
    return [_pending(db, c) for c in couriers if c is not None]


@admin.get("/couriers/{courier_id}/pending-cash")
def courier_pending_cash(courier_id: int, _: BackOffice, db: DB) -> PendingCash:
    if db.get(User, courier_id) is None:
        raise AppError(404, "NOT_FOUND", "Livreur introuvable.")
    return _pending(db, courier_id)


def _remittance_out(db: Session, r: CashRemittance) -> RemittanceOut:
    numbers = db.scalars(
        select(Order.number)
        .join(Payment, Payment.order_id == Order.id)
        .where(Payment.remittance_id == r.id)
        .order_by(Order.id)
    )
    return RemittanceOut(
        id=r.id,
        created_at=r.created_at,
        courier=_person(db, r.courier_id),
        received_by=_person(db, r.received_by),
        expected_amount=r.expected_amount,
        received_amount=r.received_amount,
        difference=r.difference,
        note=r.note,
        order_numbers=list(numbers),
    )


@admin.post("/remittances", status_code=201)
def create_remittance(data: RemittanceIn, user: BackOffice, db: DB) -> RemittanceOut:
    """Le montant attendu est calculé par le serveur ; l'écart est figé (pas de modification)."""
    payments = list(
        db.scalars(
            select(Payment)
            .where(*_PENDING, Payment.collected_by == data.courier_id)
            .with_for_update()
        )
    )
    if not payments:
        raise AppError(409, "NOTHING_TO_REMIT", "Ce livreur n'a pas d'espèces à remettre.")
    expected = sum(p.amount for p in payments)
    if expected != data.expected_amount:
        # Une livraison a été clôturée entre l'affichage et la saisie : on recompte.
        raise AppError(
            409,
            "EXPECTED_CHANGED",
            f"Le montant attendu est maintenant de {fcfa(expected)} : recomptez.",
            {"expected_amount": expected},
        )
    difference = data.received_amount - expected
    if difference and not data.note:
        raise AppError(422, "NOTE_REQUIRED", "Expliquez l'écart entre le montant attendu et reçu.")
    remittance = CashRemittance(
        courier_id=data.courier_id,
        received_by=user.id,
        expected_amount=expected,
        received_amount=data.received_amount,
        difference=difference,
        note=data.note or None,
    )
    db.add(remittance)
    db.flush()
    for p in payments:
        p.status = PaymentStatus.REMIS
        p.remittance_id = remittance.id
    audit(
        db,
        actor_id=user.id,
        action="cash.remittance",
        entity_type="remittance",
        entity_id=remittance.id,
        after={
            "courier_id": data.courier_id,
            "expected_amount": expected,
            "received_amount": data.received_amount,
            "difference": difference,
        },
    )
    db.commit()
    return _remittance_out(db, remittance)


@admin.get("/remittances")
def list_remittances(
    _: BackOffice,
    db: DB,
    courier_id: int | None = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> RemittancePage:
    filters = [CashRemittance.courier_id == courier_id] if courier_id else []
    total = db.scalar(select(func.count()).select_from(CashRemittance).where(*filters)) or 0
    rows = db.scalars(
        select(CashRemittance)
        .where(*filters)
        .order_by(CashRemittance.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return RemittancePage(
        items=[_remittance_out(db, r) for r in rows], total=total, page=page, page_size=page_size
    )
