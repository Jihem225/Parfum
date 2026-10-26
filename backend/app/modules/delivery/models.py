from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class Commune(IdMixin, TimestampMixin, Base):
    __tablename__ = "communes"
    __table_args__ = (CheckConstraint("delivery_fee >= 0", name="delivery_fee_positive"),)

    name: Mapped[str] = mapped_column(String(80), unique=True)
    delivery_fee: Mapped[int]
    delay_label: Mapped[str] = mapped_column(String(60))
    is_active: Mapped[bool] = mapped_column(default=True)
    position: Mapped[int] = mapped_column(default=0)
