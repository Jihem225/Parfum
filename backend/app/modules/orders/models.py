import enum
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Sequence, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin, str_enum


class OrderStatus(enum.StrEnum):
    EN_ATTENTE_PAIEMENT = "EN_ATTENTE_PAIEMENT"  # mobile money : annulée si non payée à temps
    EN_ATTENTE_CONFIRMATION = "EN_ATTENTE_CONFIRMATION"
    CONFIRMEE = "CONFIRMEE"
    EN_PREPARATION = "EN_PREPARATION"
    EN_LIVRAISON = "EN_LIVRAISON"
    LIVREE = "LIVREE"
    ECHEC_LIVRAISON = "ECHEC_LIVRAISON"
    RETOURNEE = "RETOURNEE"
    ANNULEE = "ANNULEE"


class EventKind(enum.StrEnum):
    STATUS_CHANGE = "STATUS_CHANGE"
    CALL = "CALL"
    DELIVERY_ATTEMPT = "DELIVERY_ATTEMPT"
    NOTE = "NOTE"


class CallResult(enum.StrEnum):
    CONFIRMEE = "CONFIRMEE"
    PAS_DE_REPONSE = "PAS_DE_REPONSE"
    ANNULATION_DEMANDEE = "ANNULATION_DEMANDEE"


class FailureReason(enum.StrEnum):
    INJOIGNABLE = "INJOIGNABLE"
    REFUS = "REFUS"
    ADRESSE_INTROUVABLE = "ADRESSE_INTROUVABLE"
    REPORTEE = "REPORTEE"


# Numéros lisibles au téléphone : PP-10001, PP-10002… (préfixe dans ORDER_NUMBER_PREFIX).
order_number_seq = Sequence("order_number_seq", start=10001, metadata=Base.metadata)


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_status_created", "status", "created_at"),
        CheckConstraint("subtotal > 0", name="subtotal_positive"),
        CheckConstraint("delivery_fee >= 0", name="delivery_fee_positive"),
        CheckConstraint("total = subtotal + delivery_fee", name="total_consistent"),
        CheckConstraint("delivery_attempts >= 0", name="attempts_positive"),
    )

    number: Mapped[str] = mapped_column(String(20), unique=True)
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        str_enum(OrderStatus), default=OrderStatus.EN_ATTENTE_CONFIRMATION
    )
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True)
    # Copie figée au moment de la commande (RG-26) : jamais recalculée.
    customer_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), index=True)
    email: Mapped[str | None] = mapped_column(String(254))
    commune_name: Mapped[str] = mapped_column(String(80))
    address_line: Mapped[str] = mapped_column(String(255))
    landmark: Mapped[str | None] = mapped_column(String(255))
    delivery_fee: Mapped[int]
    delivery_delay_label: Mapped[str] = mapped_column(String(60))
    subtotal: Mapped[int]
    total: Mapped[int]
    courier_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    delivery_attempts: Mapped[int] = mapped_column(default=0)
    cancel_reason: Mapped[str | None] = mapped_column(String(255))


class OrderItem(IdMixin, Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="unit_price_positive"),
        CheckConstraint("quantity BETWEEN 1 AND 5", name="quantity_range"),
        CheckConstraint("line_total = unit_price * quantity", name="line_total_consistent"),
    )

    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    # RESTRICT : une variante déjà commandée ne peut pas être supprimée, seulement archivée (RG-04).
    variant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("product_variants.id", ondelete="RESTRICT"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(120))
    volume_ml: Mapped[int]
    sku: Mapped[str] = mapped_column(String(40))
    unit_price: Mapped[int]
    quantity: Mapped[int]
    line_total: Mapped[int]


class OrderEvent(IdMixin, Base):
    """Historique en ajout seul : statuts, appels de confirmation, tentatives de livraison."""

    __tablename__ = "order_events"
    __table_args__ = (Index("ix_order_events_order_created", "order_id", "created_at"),)

    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id", ondelete="CASCADE"))
    kind: Mapped[EventKind] = mapped_column(str_enum(EventKind))
    from_status: Mapped[OrderStatus | None] = mapped_column(str_enum(OrderStatus, "from_status"))
    to_status: Mapped[OrderStatus | None] = mapped_column(str_enum(OrderStatus, "to_status"))
    call_result: Mapped[CallResult | None] = mapped_column(str_enum(CallResult))
    failure_reason: Mapped[FailureReason | None] = mapped_column(str_enum(FailureReason))
    note: Mapped[str | None] = mapped_column(String(500))
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
