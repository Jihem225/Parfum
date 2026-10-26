import enum

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, str_enum


class MessageStatus(enum.StrEnum):
    NOUVEAU = "NOUVEAU"
    TRAITE = "TRAITE"


class ContactMessage(IdMixin, TimestampMixin, Base):
    __tablename__ = "contact_messages"

    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(254))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[MessageStatus] = mapped_column(
        str_enum(MessageStatus), default=MessageStatus.NOUVEAU, index=True
    )
