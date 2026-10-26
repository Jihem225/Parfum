"""codes promo : table promo_codes ; remise et code figés sur la commande

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-26 20:22:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "promo_codes",
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(
                "PERCENT",
                "FIXED",
                name="promokind",
                native_enum=False,
                create_constraint=False,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("max_discount", sa.Integer(), nullable=True),
        sa.Column("min_subtotal", sa.Integer(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(length=200), nullable=True),
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "kind <> 'PERCENT' OR value <= 90", name=op.f("ck_promo_codes_percent_range")
        ),
        sa.CheckConstraint("kind IN ('PERCENT', 'FIXED')", name=op.f("ck_promo_codes_promokind")),
        sa.CheckConstraint(
            "max_discount IS NULL OR max_discount > 0",
            name=op.f("ck_promo_codes_max_discount_positive"),
        ),
        sa.CheckConstraint(
            "max_uses IS NULL OR max_uses > 0", name=op.f("ck_promo_codes_max_uses_positive")
        ),
        sa.CheckConstraint(
            "min_subtotal IS NULL OR min_subtotal > 0",
            name=op.f("ck_promo_codes_min_subtotal_positive"),
        ),
        sa.CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR ends_at > starts_at",
            name=op.f("ck_promo_codes_period_order"),
        ),
        sa.CheckConstraint("value > 0", name=op.f("ck_promo_codes_value_positive")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_promo_codes")),
        sa.UniqueConstraint("code", name=op.f("uq_promo_codes_code")),
    )
    op.add_column("orders", sa.Column("discount", sa.Integer(), server_default="0", nullable=False))
    op.add_column("orders", sa.Column("promo_code_id", sa.BigInteger(), nullable=True))
    op.add_column("orders", sa.Column("promo_code", sa.String(length=30), nullable=True))
    op.create_index(op.f("ix_orders_promo_code_id"), "orders", ["promo_code_id"])
    op.create_foreign_key(
        op.f("fk_orders_promo_code_id_promo_codes"),
        "orders",
        "promo_codes",
        ["promo_code_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # Non détectées par l'autogénération : la remise entre dans le total.
    op.drop_constraint(op.f("ck_orders_total_consistent"), "orders", type_="check")
    op.create_check_constraint(
        op.f("ck_orders_total_consistent"), "orders", "total = subtotal - discount + delivery_fee"
    )
    op.create_check_constraint(
        op.f("ck_orders_discount_range"), "orders", "discount BETWEEN 0 AND subtotal"
    )


def downgrade() -> None:
    # Échoue tant que des commandes avec remise existent : c'est voulu (pas de perte silencieuse).
    op.drop_constraint(op.f("ck_orders_discount_range"), "orders", type_="check")
    op.drop_constraint(op.f("ck_orders_total_consistent"), "orders", type_="check")
    op.create_check_constraint(
        op.f("ck_orders_total_consistent"), "orders", "total = subtotal + delivery_fee"
    )
    op.drop_constraint(op.f("fk_orders_promo_code_id_promo_codes"), "orders", type_="foreignkey")
    op.drop_index(op.f("ix_orders_promo_code_id"), table_name="orders")
    op.drop_column("orders", "promo_code")
    op.drop_column("orders", "promo_code_id")
    op.drop_column("orders", "discount")
    op.drop_table("promo_codes")
