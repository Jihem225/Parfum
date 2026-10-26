import enum
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, str_enum


class UserRole(enum.StrEnum):
    CUSTOMER = "CUSTOMER"
    COURIER = "COURIER"
    MANAGER = "MANAGER"
    OWNER = "OWNER"


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"
    # E-mail unique sans tenir compte des majuscules (RG-50).
    __table_args__ = (Index("uq_users_email_lower", text("lower(email)"), unique=True),)

    email: Mapped[str] = mapped_column(String(254))
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    role: Mapped[UserRole] = mapped_column(str_enum(UserRole), default=UserRole.CUSTOMER)
    is_active: Mapped[bool] = mapped_column(default=True)
    last_login_at: Mapped[datetime | None]
    # Double authentification (Propriétaire, Gestionnaire) : secret chiffré, codes de secours hachés
    totp_secret: Mapped[str | None] = mapped_column(String(255))
    totp_recovery_codes: Mapped[list[str] | None]


class UserSession(IdMixin, Base):
    __tablename__ = "sessions"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    last_seen_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip: Mapped[str | None] = mapped_column(String(45))


class PasswordResetToken(IdMixin, Base):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
