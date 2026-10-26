from datetime import datetime
from typing import Any

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Setting(Base):
    """Réglages de la boutique (nom, téléphone, WhatsApp, adresse…) en clé / valeur JSON."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, Any]]
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
