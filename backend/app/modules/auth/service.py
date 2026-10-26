from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core import security
from app.core.errors import AppError
from app.modules.auth.models import PasswordResetToken, User, UserRole, UserSession

# Rôles pour lesquels la double authentification est obligatoire.
TOTP_ROLES = {UserRole.OWNER, UserRole.MANAGER}
CUSTOMER_SESSION = timedelta(days=30)
STAFF_SESSION = timedelta(hours=12)
RESET_TOKEN_TTL = timedelta(hours=1)


def _invalid_credentials() -> AppError:
    return AppError(401, "INVALID_CREDENTIALS", "E-mail ou mot de passe incorrect.")


def session_ttl(user: User) -> timedelta:
    return CUSTOMER_SESSION if user.role == UserRole.CUSTOMER else STAFF_SESSION


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def register(db: Session, *, email: str, password: str, full_name: str, phone: str) -> User:
    if find_by_email(db, email):
        raise AppError(409, "EMAIL_TAKEN", "Un compte existe déjà avec cet e-mail.")
    user = User(
        email=email,
        password_hash=security.hash_password(password),
        full_name=full_name,
        phone=phone,
        role=UserRole.CUSTOMER,
    )
    db.add(user)
    db.flush()
    return user


def _consume_recovery_code(user: User, code: str) -> bool:
    digest = security.sha256(code.strip().lower())
    codes = user.totp_recovery_codes or []
    if digest not in codes:
        return False
    user.totp_recovery_codes = [c for c in codes if c != digest]  # usage unique
    return True


def authenticate(db: Session, *, email: str, password: str, totp_code: str | None) -> User:
    user = find_by_email(db, email)
    if user is None:
        security.burn_password_check(password)
        raise _invalid_credentials()
    if not security.verify_password(password, user.password_hash) or not user.is_active:
        raise _invalid_credentials()
    if user.role in TOTP_ROLES and user.totp_secret:
        if not totp_code:
            raise AppError(401, "TOTP_REQUIRED", "Saisissez le code de double authentification.")
        secret = security.decrypt(user.totp_secret)
        if not security.verify_totp(secret, totp_code) and not _consume_recovery_code(
            user, totp_code
        ):
            raise AppError(401, "TOTP_INVALID", "Code de double authentification incorrect.")
    user.last_login_at = datetime.now(UTC)
    return user


def create_session(
    db: Session, user: User, *, user_agent: str | None, ip: str | None
) -> tuple[str, timedelta]:
    raw, digest = security.new_token()
    ttl = session_ttl(user)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=digest,
            expires_at=datetime.now(UTC) + ttl,
            user_agent=(user_agent or "")[:255] or None,
            ip=ip,
        )
    )
    return raw, ttl


def end_session(db: Session, raw_token: str) -> None:
    db.execute(delete(UserSession).where(UserSession.token_hash == security.sha256(raw_token)))


def revoke_sessions(db: Session, user_id: int, *, except_hash: str | None = None) -> None:
    query = delete(UserSession).where(UserSession.user_id == user_id)
    if except_hash:
        query = query.where(UserSession.token_hash != except_hash)
    db.execute(query)


def start_password_reset(db: Session, email: str) -> tuple[User, str] | None:
    user = find_by_email(db, email)
    if user is None or not user.is_active:
        return None
    raw, digest = security.new_token()
    db.add(
        PasswordResetToken(
            user_id=user.id, token_hash=digest, expires_at=datetime.now(UTC) + RESET_TOKEN_TTL
        )
    )
    return user, raw


def reset_password(db: Session, *, token: str, password: str) -> None:
    reset = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == security.sha256(token),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > func.now(),
        )
        .with_for_update()
    )
    user = db.get(User, reset.user_id) if reset else None
    if reset is None or user is None or not user.is_active:
        raise AppError(400, "INVALID_TOKEN", "Ce lien est invalide ou a expiré.")
    reset.used_at = datetime.now(UTC)
    user.password_hash = security.hash_password(password)
    revoke_sessions(db, user.id)  # déconnecte tous les appareils


def change_password(
    db: Session, user: User, *, current: str, new: str, keep_session_hash: str | None
) -> None:
    if not security.verify_password(current, user.password_hash):
        raise AppError(400, "INVALID_PASSWORD", "Le mot de passe actuel est incorrect.")
    user.password_hash = security.hash_password(new)
    revoke_sessions(db, user.id, except_hash=keep_session_hash)


def enable_totp(user: User, *, secret: str, code: str) -> list[str]:
    if user.totp_secret:
        raise AppError(409, "TOTP_ALREADY_ENABLED", "La double authentification est déjà active.")
    if not security.verify_totp(secret, code):
        raise AppError(400, "TOTP_INVALID", "Code incorrect : vérifiez l'heure de votre téléphone.")
    codes = security.new_recovery_codes()
    user.totp_secret = security.encrypt(secret)
    user.totp_recovery_codes = [security.sha256(c) for c in codes]
    return codes
