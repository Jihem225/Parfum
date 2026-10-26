"""Codes promo au back-office (étape 13) : consultés par l'équipe, créés et modifiés par le
Propriétaire. Un code déjà utilisé ne se supprime pas : il se désactive."""

import re
from datetime import datetime
from typing import Annotated, Any, Self

from fastapi import APIRouter
from pydantic import AfterValidator, BaseModel, Field, StringConstraints, model_validator
from sqlalchemy import func, select

from app.core.audit import audit
from app.core.errors import AppError
from app.modules.auth.deps import DB, BackOffice, Owner
from app.modules.orders.models import Order, OrderStatus
from app.modules.promotions.models import PromoCode, PromoKind

admin = APIRouter(prefix="/admin/promo-codes", tags=["admin: codes promo"])


def _code_format(value: str) -> str:
    if not re.fullmatch(r"[A-Z0-9-]+", value):
        raise ValueError("Lettres, chiffres et tirets uniquement (ex. BIENVENUE10).")
    return value


Code = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_upper=True, min_length=3, max_length=30),
    AfterValidator(_code_format),
]
Amount = Annotated[int, Field(gt=0, le=10_000_000)]


class PromoIn(BaseModel):
    kind: PromoKind
    value: Amount
    max_discount: Amount | None = None
    min_subtotal: Amount | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    max_uses: Annotated[int, Field(gt=0, le=1_000_000)] | None = None
    is_active: bool = True
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""

    @model_validator(mode="after")
    def _coherent(self) -> Self:
        if self.kind == PromoKind.PERCENT and self.value > 90:
            raise ValueError("Pourcentage de 1 à 90.")
        if self.kind == PromoKind.FIXED and self.max_discount is not None:
            raise ValueError("Le plafond ne concerne que les pourcentages.")
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("La fin doit être après le début.")
        return self


class PromoCreate(PromoIn):
    code: Code


class PromoOut(PromoCreate):
    id: int
    created_at: datetime
    uses: int  # commandes non annulées
    discount_total: int  # remises accordées sur ces commandes


def _values(promo: PromoCode) -> dict[str, Any]:
    return {name: getattr(promo, name) for name in PromoCreate.model_fields} | {
        "note": promo.note or ""
    }


def _out(db: DB, promo: PromoCode) -> PromoOut:
    uses, total = db.execute(
        select(func.count(), func.coalesce(func.sum(Order.discount), 0)).where(
            Order.promo_code_id == promo.id, Order.status != OrderStatus.ANNULEE
        )
    ).one()
    return PromoOut(
        **_values(promo), id=promo.id, created_at=promo.created_at, uses=uses, discount_total=total
    )


def _get(db: DB, promo_id: int) -> PromoCode:
    promo = db.get(PromoCode, promo_id, with_for_update=True)
    if promo is None:
        raise AppError(404, "NOT_FOUND", "Code promo introuvable.")
    return promo


@admin.get("")
def list_promo_codes(_: BackOffice, db: DB) -> list[PromoOut]:
    return [_out(db, p) for p in db.scalars(select(PromoCode).order_by(PromoCode.id.desc()))]


@admin.post("", status_code=201)
def create_promo_code(data: PromoCreate, user: Owner, db: DB) -> PromoOut:
    if db.scalar(select(PromoCode.id).where(PromoCode.code == data.code)):
        raise AppError(409, "CODE_TAKEN", "Ce code existe déjà.")
    promo = PromoCode(**data.model_dump(exclude={"note"}), note=data.note or None)
    db.add(promo)
    db.flush()
    audit(
        db,
        actor_id=user.id,
        action="promo.create",
        entity_type="promo_code",
        entity_id=promo.code,
        after=data.model_dump(mode="json"),
    )
    db.commit()
    return _out(db, promo)


@admin.put("/{promo_id}")
def update_promo_code(promo_id: int, data: PromoIn, user: Owner, db: DB) -> PromoOut:
    """Tout sauf le code lui-même ; les commandes passées gardent leur réduction (copie figée)."""
    promo = _get(db, promo_id)
    before = PromoIn.model_validate(_values(promo)).model_dump(mode="json")
    for name, value in data.model_dump(exclude={"note"}).items():
        setattr(promo, name, value)
    promo.note = data.note or None
    audit(
        db,
        actor_id=user.id,
        action="promo.update",
        entity_type="promo_code",
        entity_id=promo.code,
        before=before,
        after=data.model_dump(mode="json"),
    )
    db.commit()
    return _out(db, promo)


@admin.delete("/{promo_id}", status_code=204)
def delete_promo_code(promo_id: int, user: Owner, db: DB) -> None:
    promo = _get(db, promo_id)
    if db.scalar(select(func.count()).where(Order.promo_code_id == promo.id)):
        raise AppError(409, "PROMO_USED", "Ce code a servi à des commandes : désactivez-le plutôt.")
    audit(
        db,
        actor_id=user.id,
        action="promo.delete",
        entity_type="promo_code",
        entity_id=promo.code,
        before=PromoCreate.model_validate(_values(promo)).model_dump(mode="json"),
    )
    db.delete(promo)
    db.commit()
