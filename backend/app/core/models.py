import enum
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, str_enum


class AuditLog(IdMixin, Base):
    """Actions sensibles du back-office (RG-53), en ajout seul."""

    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_entity", "entity_type", "entity_id"),)

    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(80))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(40))
    before: Mapped[dict[str, Any] | None]
    after: Mapped[dict[str, Any] | None]
    ip: Mapped[str | None] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)


class RateLimitHit(Base):
    """Compteurs de limitation de débit par fenêtre de temps (pas de Redis au MVP)."""

    __tablename__ = "rate_limit_hits"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    window_start: Mapped[datetime] = mapped_column(primary_key=True)
    count: Mapped[int] = mapped_column(default=0)


class EmailStatus(enum.StrEnum):
    PENDING = "PENDING"  # à envoyer (premier essai ou nouvel essai programmé)
    SENT = "SENT"
    FAILED = "FAILED"  # abandonné après le dernier essai : à renvoyer depuis le back-office


class EmailMessage(IdMixin, Base):
    """File d'envoi : l'e-mail est écrit dans la transaction de l'action qui le déclenche, puis
    envoyé par la tâche de fond, avec nouveaux essais en cas d'échec."""

    __tablename__ = "email_outbox"
    __table_args__ = (Index("ix_email_outbox_due", "status", "next_attempt_at"),)

    to_address: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)  # vidé après l'envoi (liens de réinitialisation…)
    status: Mapped[EmailStatus] = mapped_column(str_enum(EmailStatus), default=EmailStatus.PENDING)
    attempts: Mapped[int] = mapped_column(default=0)
    next_attempt_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_error: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    sent_at: Mapped[datetime | None]
