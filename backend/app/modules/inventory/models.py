import enum
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, str_enum


class MovementType(enum.StrEnum):
    ENTREE = "ENTREE"
    AJUSTEMENT = "AJUSTEMENT"
    RESERVATION = "RESERVATION"
    LIBERATION = "LIBERATION"
    SORTIE_VENTE = "SORTIE_VENTE"
    RETOUR = "RETOUR"
    PERTE = "PERTE"


class StockMovement(IdMixin, Base):
    """Journal en ajout seul : chaque modification de stock d'une variante y laisse une ligne."""

    __tablename__ = "stock_movements"
    __table_args__ = (Index("ix_stock_movements_variant_created", "variant_id", "created_at"),)

    variant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_variants.id", ondelete="RESTRICT")
    )
    type: Mapped[MovementType] = mapped_column(str_enum(MovementType))
    delta_physical: Mapped[int] = mapped_column(default=0)
    delta_reserved: Mapped[int] = mapped_column(default=0)
    order_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
