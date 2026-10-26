from sqlalchemy import BigInteger, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, IdMixin, TimestampMixin


class Address(IdMixin, TimestampMixin, Base):
    __tablename__ = "addresses"
    __table_args__ = (
        # Une seule adresse par défaut par client.
        Index(
            "uq_addresses_default_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str | None] = mapped_column(String(60))
    recipient_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    commune_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("communes.id", ondelete="RESTRICT")
    )
    address_line: Mapped[str] = mapped_column(String(255))
    landmark: Mapped[str | None] = mapped_column(String(255))
    is_default: Mapped[bool] = mapped_column(default=False)
