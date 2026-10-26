import enum
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, str_enum


class PaymentMethod(enum.StrEnum):
    CASH_ON_DELIVERY = "CASH_ON_DELIVERY"


class PaymentStatus(enum.StrEnum):
    A_ENCAISSER = "A_ENCAISSER"
    ENCAISSE = "ENCAISSE"
    REMIS = "REMIS"
    ANNULE = "ANNULE"
    REMBOURSE = "REMBOURSE"


class CashRemittance(IdMixin, Base):
    """Remise d'espèces d'un livreur à la boutique : lecture seule une fois créée (RG-45)."""

    __tablename__ = "cash_remittances"
    __table_args__ = (
        CheckConstraint("expected_amount >= 0", name="expected_positive"),
        CheckConstraint("received_amount >= 0", name="received_positive"),
        CheckConstraint(
            "difference = received_amount - expected_amount", name="difference_consistent"
        ),
    )

    courier_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    received_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    expected_amount: Mapped[int]
    received_amount: Mapped[int]
    difference: Mapped[int]
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Payment(IdMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="amount_positive"),)

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), unique=True
    )
    method: Mapped[PaymentMethod] = mapped_column(
        str_enum(PaymentMethod), default=PaymentMethod.CASH_ON_DELIVERY
    )
    status: Mapped[PaymentStatus] = mapped_column(
        str_enum(PaymentStatus), default=PaymentStatus.A_ENCAISSER
    )
    amount: Mapped[int]
    collected_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT")
    )
    collected_at: Mapped[datetime | None]
    remittance_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("cash_remittances.id", ondelete="RESTRICT"), index=True
    )
    refunded_at: Mapped[datetime | None]
