"""Formulaire de contact (F-12) et messages reçus au back-office (F-46)."""

from datetime import datetime
from typing import Annotated, Self

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, StringConstraints, model_validator
from sqlalchemy import func, select

from app.core import rate_limit
from app.core.config import settings
from app.core.email import queue_email
from app.core.errors import AppError
from app.core.validators import PersonName, Phone
from app.modules.auth.deps import DB, BackOffice, client_ip
from app.modules.auth.schemas import Email, MessageOut
from app.modules.contact.models import ContactMessage, MessageStatus

public = APIRouter(tags=["contact"])
admin = APIRouter(prefix="/admin/contact-messages", tags=["admin: messages"])


class ContactIn(BaseModel):
    name: PersonName
    phone: Phone | None = None
    email: Email | None = None
    message: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=10, max_length=2000)
    ]

    @model_validator(mode="after")
    def _reachable(self) -> Self:
        if not self.phone and not self.email:
            raise ValueError("Indiquez un téléphone ou un e-mail pour que nous puissions répondre.")
        return self


class ContactOut(BaseModel):
    id: int
    created_at: datetime
    name: str
    phone: str | None
    email: str | None
    message: str
    status: MessageStatus


class ContactPage(BaseModel):
    items: list[ContactOut]
    total: int
    page: int
    page_size: int


class ContactPatch(BaseModel):
    status: MessageStatus


@public.post("/contact", status_code=201)
def send_message(data: ContactIn, request: Request, db: DB) -> MessageOut:
    rate_limit.limit(f"contact:ip:{client_ip(request)}", 5, 3600)
    db.add(ContactMessage(**data.model_dump()))
    if settings.shop_notification_email:
        contact = " — ".join(x for x in (data.phone, data.email) if x)
        queue_email(
            db,
            settings.shop_notification_email,
            f"Nouveau message de {data.name}",
            f"{data.name} ({contact}) :\n\n{data.message}",
        )
    db.commit()
    return MessageOut(message="Merci, votre message est bien arrivé. Nous vous répondons vite.")


@admin.get("")
def list_messages(
    _: BackOffice,
    db: DB,
    status: MessageStatus | None = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ContactPage:
    filters = [ContactMessage.status == status] if status else []
    total = db.scalar(select(func.count()).select_from(ContactMessage).where(*filters)) or 0
    rows = db.scalars(
        select(ContactMessage)
        .where(*filters)
        .order_by(ContactMessage.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return ContactPage(
        items=[ContactOut.model_validate(m, from_attributes=True) for m in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@admin.patch("/{message_id}")
def mark_message(message_id: int, data: ContactPatch, _: BackOffice, db: DB) -> ContactOut:
    message = db.get(ContactMessage, message_id)
    if message is None:
        raise AppError(404, "NOT_FOUND", "Message introuvable.")
    message.status = data.status
    db.commit()
    return ContactOut.model_validate(message, from_attributes=True)
