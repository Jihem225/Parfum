import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, str_enum


class Gender(enum.StrEnum):
    FEMME = "FEMME"
    HOMME = "HOMME"
    MIXTE = "MIXTE"


class ProductStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Collection(IdMixin, TimestampMixin, Base):
    __tablename__ = "collections"

    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_key: Mapped[str | None] = mapped_column(String(255))
    position: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)


class OlfactoryFamily(IdMixin, TimestampMixin, Base):
    __tablename__ = "olfactory_families"

    name: Mapped[str] = mapped_column(String(80))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    position: Mapped[int] = mapped_column(default=0)


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_status_collection", "status", "collection_id"),
        Index("ix_products_status_family", "status", "family_id"),
    )

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True)
    collection_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("collections.id", ondelete="RESTRICT")
    )
    family_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("olfactory_families.id", ondelete="RESTRICT")
    )
    gender: Mapped[Gender] = mapped_column(str_enum(Gender))
    description: Mapped[str] = mapped_column(Text, default="")
    top_notes: Mapped[str] = mapped_column(String(255), default="")
    heart_notes: Mapped[str] = mapped_column(String(255), default="")
    base_notes: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[ProductStatus] = mapped_column(
        str_enum(ProductStatus), default=ProductStatus.DRAFT
    )
    published_at: Mapped[datetime | None]


class ProductVariant(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "volume_ml"),
        CheckConstraint("volume_ml > 0", name="volume_positive"),
        CheckConstraint("price > 0", name="price_positive"),
        CheckConstraint("cost_price IS NULL OR cost_price >= 0", name="cost_price_positive"),
        CheckConstraint("low_stock_threshold >= 0", name="threshold_positive"),
        # Dernier rempart anti-survente : jamais de réservation au-delà du stock physique.
        CheckConstraint("stock_reserved >= 0", name="reserved_positive"),
        CheckConstraint("stock_reserved <= stock_physical", name="reserved_within_physical"),
    )

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    sku: Mapped[str] = mapped_column(String(40), unique=True)
    volume_ml: Mapped[int]
    price: Mapped[int]  # FCFA, entier
    cost_price: Mapped[int | None]  # FCFA, entier, facultatif
    stock_physical: Mapped[int] = mapped_column(default=0)
    stock_reserved: Mapped[int] = mapped_column(default=0)
    low_stock_threshold: Mapped[int] = mapped_column(default=5)
    is_active: Mapped[bool] = mapped_column(default=True)


class ProductImage(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(255))
    alt_text: Mapped[str] = mapped_column(String(255), default="")
    position: Mapped[int] = mapped_column(default=0)  # 0 = image principale
