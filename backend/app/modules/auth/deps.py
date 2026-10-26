from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.db import get_db
from app.core.errors import AppError
from app.modules.auth.models import User, UserRole, UserSession
from app.modules.auth.service import TOTP_ROLES, session_ttl

SESSION_COOKIE = "session"
DB = Annotated[Session, Depends(get_db)]


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def get_optional_user(request: Request, db: DB) -> User | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    row = db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            UserSession.token_hash == security.sha256(raw),
            UserSession.expires_at > datetime.now(UTC),
        )
    ).first()
    if row is None:
        return None
    session, user = row
    if not user.is_active:  # RG-54 : un compte désactivé perd l'accès immédiatement
        return None
    now = datetime.now(UTC)
    if now - session.last_seen_at > timedelta(hours=1):
        session.last_seen_at = now
        if user.role == UserRole.CUSTOMER:  # session client glissante
            session.expires_at = now + session_ttl(user)
        db.commit()
    return user


def get_current_user(user: Annotated[User | None, Depends(get_optional_user)]) -> User:
    if user is None:
        raise AppError(401, "AUTH_REQUIRED", "Connexion requise.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole, allow_without_totp: bool = False) -> Callable[[User], User]:
    """Contrôle d'accès côté serveur. Les rôles du back-office doivent avoir activé la double
    authentification, sauf sur les routes qui servent justement à l'activer."""

    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN", "Accès refusé.")
        if user.role in TOTP_ROLES and user.totp_secret is None and not allow_without_totp:
            raise AppError(
                403,
                "TOTP_SETUP_REQUIRED",
                "Activez la double authentification pour accéder à l'administration.",
            )
        return user

    return dependency


# Gestionnaire ou Propriétaire : catalogue, stock, commandes (matrice des rôles, conception §7).
BackOffice = Annotated[User, Depends(require_roles(UserRole.MANAGER, UserRole.OWNER))]
