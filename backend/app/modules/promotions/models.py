import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, str_enum


class PromoKind(enum.StrEnum):
    PERCENT = "PERCENT"  # pourcentage des articles, plafonné par max_discount s'il est fixé
    FIXED = "FIXED"  # montant en FCFA


class PromoCode(IdMixin, TimestampMixin, Base):
    """Code promo (étape 13) : réduction sur les articles, hors livraison. Les utilisations sont
    les commandes non annulées qui le portent (une annulation rend le code)."""

    __tablename__ = "promo_codes"
    __table_args__ = (
        CheckConstraint("value > 0", name="value_positive"),
        CheckConstraint("kind <> 'PERCENT' OR value <= 90", name="percent_range"),
        CheckConstraint("max_discount IS NULL OR max_discount > 0", name="max_discount_positive"),
        CheckConstraint("min_subtotal IS NULL OR min_subtotal > 0", name="min_subtotal_positive"),
        CheckConstraint("max_uses IS NULL OR max_uses > 0", name="max_uses_positive"),
        CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at", name="period_order"
        ),
    )

    code: Mapped[str] = mapped_column(String(30), unique=True)  # en majuscules
    kind: Mapped[PromoKind] = mapped_column(str_enum(PromoKind))
    value: Mapped[int]  # pourcentage (1 à 90) ou montant en FCFA
    max_discount: Mapped[int | None]
    min_subtotal: Mapped[int | None]  # montant d'articles minimum
    starts_at: Mapped[datetime | None]
    ends_at: Mapped[datetime | None]
    max_uses: Mapped[int | None]  # toutes commandes confondues ; en plus, 1 fois par téléphone
    is_active: Mapped[bool] = mapped_column(default=True)
    note: Mapped[str | None] = mapped_column(String(200))  # usage interne (campagne, partenaire)
