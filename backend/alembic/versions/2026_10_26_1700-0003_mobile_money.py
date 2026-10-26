"""mobile money : statuts « en attente de paiement », « à payer », « payé » ; référence prestataire

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-26 17:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORDER = [
    "EN_ATTENTE_CONFIRMATION",
    "CONFIRMEE",
    "EN_PREPARATION",
    "EN_LIVRAISON",
    "LIVREE",
    "ECHEC_LIVRAISON",
    "RETOURNEE",
    "ANNULEE",
]
PAYMENT = ["A_ENCAISSER", "ENCAISSE", "REMIS", "ANNULE", "REMBOURSE"]
METHOD = ["CASH_ON_DELIVERY"]

# (table, colonne, nom de contrainte, valeurs avant, valeurs ajoutées)
CHECKS = [
    ("orders", "status", "ck_orders_orderstatus", ORDER, ["EN_ATTENTE_PAIEMENT"]),
    ("order_events", "from_status", "ck_order_events_from_status", ORDER, ["EN_ATTENTE_PAIEMENT"]),
    ("order_events", "to_status", "ck_order_events_to_status", ORDER, ["EN_ATTENTE_PAIEMENT"]),
    ("payments", "status", "ck_payments_paymentstatus", PAYMENT, ["A_PAYER", "PAYE"]),
    ("payments", "method", "ck_payments_paymentmethod", METHOD, ["MOBILE_MONEY"]),
]


def _check(table: str, column: str, name: str, values: list[str]) -> None:
    op.drop_constraint(op.f(name), table, type_="check")
    listed = ", ".join(f"'{v}'" for v in values)
    op.create_check_constraint(op.f(name), table, f"{column} IN ({listed})")


def upgrade() -> None:
    for table, column, name, before, added in CHECKS:
        _check(table, column, name, before + added)
    op.add_column("payments", sa.Column("provider_ref", sa.String(length=100), nullable=True))


def downgrade() -> None:
    # Échoue tant que des commandes mobile money existent : c'est voulu (pas de perte silencieuse).
    op.drop_column("payments", "provider_ref")
    for table, column, name, before, _ in CHECKS:
        _check(table, column, name, before)
