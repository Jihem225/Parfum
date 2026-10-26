from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import security
from app.core.audit import audit
from app.core.errors import AppError
from app.core.validators import Password, PersonName, Phone
from app.modules.auth import service as auth_service
from app.modules.auth.deps import DB, Owner, client_ip
from app.modules.auth.models import User, UserRole
from app.modules.auth.schemas import Email, UserOut

router = APIRouter(prefix="/admin/staff", tags=["admin: collaborateurs"])

STAFF_ROLES = (UserRole.COURIER, UserRole.MANAGER, UserRole.OWNER)


class StaffCreateIn(BaseModel):
    email: Email
    full_name: PersonName
    phone: Phone
    role: UserRole
    temporary_password: Password


class StaffUpdateIn(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None
    reset_totp: bool = False


def _snapshot(user: User) -> dict[str, Any]:
    return {"role": user.role.value, "is_active": user.is_active}


def _active_owner_count(db: Session) -> int:
    return (
        db.scalar(select(func.count()).where(User.role == UserRole.OWNER, User.is_active.is_(True)))
        or 0
    )


@router.get("")
def list_staff(_: Owner, db: DB) -> list[UserOut]:
    users = db.scalars(select(User).where(User.role.in_(STAFF_ROLES)).order_by(User.full_name))
    return [UserOut.of(u) for u in users]


@router.post("", status_code=201)
def create_staff(data: StaffCreateIn, request: Request, owner: Owner, db: DB) -> UserOut:
    if data.role not in STAFF_ROLES:
        raise AppError(422, "INVALID_ROLE", "Rôle de collaborateur invalide.")
    if auth_service.find_by_email(db, data.email):
        raise AppError(409, "EMAIL_TAKEN", "Un compte existe déjà avec cet e-mail.")
    user = User(
        email=data.email,
        password_hash=security.hash_password(data.temporary_password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
    )
    db.add(user)
    db.flush()
    audit(
        db,
        actor_id=owner.id,
        action="staff.create",
        entity_type="user",
        entity_id=user.id,
        after=_snapshot(user) | {"email": user.email},
        ip=client_ip(request),
    )
    db.commit()
    return UserOut.of(user)


@router.patch("/{user_id}")
def update_staff(
    user_id: int, data: StaffUpdateIn, request: Request, owner: Owner, db: DB
) -> UserOut:
    user = db.get(User, user_id, with_for_update=True)
    if user is None or user.role not in STAFF_ROLES:
        raise AppError(404, "NOT_FOUND", "Collaborateur introuvable.")
    if data.role is not None and data.role not in STAFF_ROLES:
        raise AppError(422, "INVALID_ROLE", "Rôle de collaborateur invalide.")
    before = _snapshot(user)
    loses_owner = (
        user.role == UserRole.OWNER
        and user.is_active
        and ((data.role is not None and data.role != UserRole.OWNER) or data.is_active is False)
    )
    if loses_owner and _active_owner_count(db) <= 1:
        raise AppError(
            409, "LAST_OWNER", "Impossible : il doit rester au moins un Propriétaire actif."
        )
    if data.role is not None:
        user.role = data.role
    if data.is_active is not None:
        user.is_active = data.is_active
    if data.reset_totp:  # téléphone perdu : le collaborateur réactivera la double authentification
        user.totp_secret = None
        user.totp_recovery_codes = None
    if data.is_active is False or data.reset_totp:
        auth_service.revoke_sessions(db, user.id)
    audit(
        db,
        actor_id=owner.id,
        action="staff.update",
        entity_type="user",
        entity_id=user.id,
        before=before,
        after=_snapshot(user) | {"reset_totp": data.reset_totp},
        ip=client_ip(request),
    )
    db.commit()
    return UserOut.of(user)
