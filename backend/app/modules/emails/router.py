"""E-mails non envoyés (file d'envoi, app/core/email.py) : consultation et renvoi au back-office."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.audit import audit
from app.core.errors import AppError
from app.core.models import EmailMessage, EmailStatus
from app.modules.auth.deps import DB, BackOffice

admin = APIRouter(prefix="/admin/emails", tags=["admin: e-mails"])


class EmailOut(BaseModel):
    id: int
    created_at: datetime
    to_address: str
    subject: str
    status: EmailStatus
    attempts: int
    next_attempt_at: datetime
    last_error: str | None
    sent_at: datetime | None


class EmailPage(BaseModel):
    items: list[EmailOut]
    total: int
    page: int
    page_size: int


@admin.get("")
def list_emails(
    _: BackOffice,
    db: DB,
    status: EmailStatus = EmailStatus.FAILED,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EmailPage:
    filters = [EmailMessage.status == status]
    total = db.scalar(select(func.count()).select_from(EmailMessage).where(*filters)) or 0
    rows = db.scalars(
        select(EmailMessage)
        .where(*filters)
        .order_by(EmailMessage.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return EmailPage(
        items=[EmailOut.model_validate(m, from_attributes=True) for m in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin.post("/{email_id}/retry")
def retry_email(email_id: int, user: BackOffice, db: DB) -> EmailOut:
    """Remet un e-mail abandonné dans la file : nouvelle série d'essais, dans les secondes qui
    suivent (après correction d'une adresse ou de la configuration, par exemple)."""
    message = db.get(EmailMessage, email_id, with_for_update=True)
    if message is None:
        raise AppError(404, "NOT_FOUND", "E-mail introuvable.")
    if message.status != EmailStatus.FAILED:
        raise AppError(409, "NOT_FAILED", "Seul un e-mail en échec peut être renvoyé.")
    message.status = EmailStatus.PENDING
    message.attempts = 0
    message.next_attempt_at = datetime.now(UTC)
    audit(
        db,
        actor_id=user.id,
        action="email.retry",
        entity_type="email",
        entity_id=message.id,
        before={"status": EmailStatus.FAILED.value, "error": message.last_error},
        after={"status": EmailStatus.PENDING.value, "to": message.to_address},
    )
    db.commit()
    return EmailOut.model_validate(message, from_attributes=True)
