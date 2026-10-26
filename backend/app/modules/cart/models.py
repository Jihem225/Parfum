from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin


class Cart(IdMixin, Base):
    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint("token_hash IS NOT NULL OR user_id IS NOT NULL", name="has_owner"),
    )

    token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)  # visiteur
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class CartItem(IdMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "variant_id"),
        CheckConstraint("quantity BETWEEN 1 AND 5", name="quantity_range"),  # RG-22
    )

    cart_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("carts.id", ondelete="CASCADE"))
    variant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_variants.id", ondelete="CASCADE")
    )
    quantity: Mapped[int]
