"""Espace client : profil et carnet d'adresses (F-22, F-23, US-10). Modifier une adresse ne
touche pas les commandes passées, qui en gardent une copie (RG-26)."""

from typing import Any

from fastapi import APIRouter
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.auth.deps import DB, CurrentUser
from app.modules.auth.models import User
from app.modules.auth.schemas import UserOut
from app.modules.customers.models import Address
from app.modules.customers.schemas import AddressIn, AddressOut, AddressPatch, ProfilePatch
from app.modules.delivery.models import Commune
from app.modules.orders import service as orders

router = APIRouter(prefix="/me", tags=["espace client"])

MAX_ADDRESSES = 10


@router.get("/profile")
def get_profile(user: CurrentUser) -> UserOut:
    return UserOut.of(user)


@router.patch("/profile")
def update_profile(data: ProfilePatch, user: CurrentUser, db: DB) -> UserOut:
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    db.commit()
    return UserOut.of(user)


def _out(address: Address, commune: Commune) -> AddressOut:
    return AddressOut(
        id=address.id,
        label=address.label,
        recipient_name=address.recipient_name,
        phone=address.phone,
        commune_id=commune.id,
        commune_name=commune.name,
        commune_served=commune.is_active,
        address_line=address.address_line,
        landmark=address.landmark,
        is_default=address.is_default,
    )


def _addresses(db: Session, user: User) -> list[AddressOut]:
    rows = db.execute(
        select(Address, Commune)
        .join(Commune, Commune.id == Address.commune_id)
        .where(Address.user_id == user.id)
        .order_by(Address.is_default.desc(), Address.id)
    )
    return [_out(a, c) for a, c in rows]


def _get(db: Session, user: User, address_id: int) -> Address:
    address = db.get(Address, address_id)
    if address is None or address.user_id != user.id:
        raise AppError(404, "NOT_FOUND", "Adresse introuvable.")
    return address


def _apply(db: Session, user: User, address: Address, changes: dict[str, Any]) -> None:
    if "commune_id" in changes:
        orders.served_commune(db, changes["commune_id"])  # RG-25
    for key in ("label", "landmark"):
        if key in changes:
            changes[key] = changes[key] or None
    if changes.pop("is_default", False):
        # Une seule adresse par défaut (index unique partiel) : on retire l'ancienne d'abord.
        db.execute(update(Address).where(Address.user_id == user.id).values(is_default=False))
        address.is_default = True
    for key, value in changes.items():
        setattr(address, key, value)


@router.get("/addresses")
def list_addresses(user: CurrentUser, db: DB) -> list[AddressOut]:
    return _addresses(db, user)


@router.post("/addresses", status_code=201)
def add_address(data: AddressIn, user: CurrentUser, db: DB) -> list[AddressOut]:
    count = db.scalar(select(func.count()).where(Address.user_id == user.id)) or 0
    if count >= MAX_ADDRESSES:
        raise AppError(409, "TOO_MANY_ADDRESSES", f"{MAX_ADDRESSES} adresses maximum.")
    changes = data.model_dump()
    changes["is_default"] = changes["is_default"] or count == 0  # la première sert par défaut
    address = Address(user_id=user.id, is_default=False, commune_id=data.commune_id)
    _apply(db, user, address, changes)
    db.add(address)
    db.commit()
    return _addresses(db, user)


@router.patch("/addresses/{address_id}")
def update_address(
    address_id: int, data: AddressPatch, user: CurrentUser, db: DB
) -> list[AddressOut]:
    address = _get(db, user, address_id)
    _apply(db, user, address, data.model_dump(exclude_none=True))
    db.commit()
    return _addresses(db, user)


@router.delete("/addresses/{address_id}")
def delete_address(address_id: int, user: CurrentUser, db: DB) -> list[AddressOut]:
    address = _get(db, user, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    if was_default:
        latest = db.scalar(
            select(Address).where(Address.user_id == user.id).order_by(Address.id.desc()).limit(1)
        )
        if latest is not None:
            latest.is_default = True
    db.commit()
    return _addresses(db, user)
