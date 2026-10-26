from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.audit import audit
from app.core.errors import AppError
from app.modules.auth.deps import DB, Owner
from app.modules.delivery.models import Commune
from app.modules.delivery.schemas import CommuneIn, CommuneOut, CommunePatch

public = APIRouter(prefix="/delivery", tags=["livraison"])
admin = APIRouter(prefix="/admin/communes", tags=["admin: livraison"])

_ORDER = (Commune.position, Commune.name)
_KEYS = ("name", "delivery_fee", "delay_label", "is_active", "position")


def _out(c: Commune) -> CommuneOut:
    return CommuneOut.model_validate(c, from_attributes=True)


def _save(db: DB) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "NAME_TAKEN", "Cette commune existe déjà.") from exc


@public.get("/communes")
def served_communes(db: DB) -> list[CommuneOut]:
    """Communes desservies, avec frais et délai (RG-40)."""
    return [_out(c) for c in db.scalars(select(Commune).where(Commune.is_active).order_by(*_ORDER))]


@admin.get("")
def list_communes(_: Owner, db: DB) -> list[CommuneOut]:
    return [_out(c) for c in db.scalars(select(Commune).order_by(*_ORDER))]


@admin.post("", status_code=201)
def create_commune(data: CommuneIn, user: Owner, db: DB) -> CommuneOut:
    commune = Commune(**data.model_dump())
    db.add(commune)
    _save(db)
    audit(
        db,
        actor_id=user.id,
        action="commune.create",
        entity_type="commune",
        entity_id=commune.id,
        after=data.model_dump(),
    )
    db.commit()
    return _out(commune)


@admin.patch("/{commune_id}")
def update_commune(commune_id: int, data: CommunePatch, user: Owner, db: DB) -> CommuneOut:
    """Un changement de frais ne touche pas les commandes passées : elles en gardent une copie."""
    commune = db.get(Commune, commune_id)
    if commune is None:
        raise AppError(404, "NOT_FOUND", "Commune introuvable.")
    before = {k: getattr(commune, k) for k in _KEYS}
    for key, value in data.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(commune, key, value)
    _save(db)
    audit(
        db,
        actor_id=user.id,
        action="commune.update",
        entity_type="commune",
        entity_id=commune.id,
        before=before,
        after={k: getattr(commune, k) for k in _KEYS},
    )
    db.commit()
    return _out(commune)
