from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.modules.orders.schemas import PersonRef


class PendingOrder(BaseModel):
    number: str
    amount: int
    collected_at: datetime | None


class PendingCash(BaseModel):
    """Espèces encaissées par un livreur et pas encore remises à la boutique."""

    courier: PersonRef
    amount: int
    orders: list[PendingOrder]


class RemittanceIn(BaseModel):
    courier_id: int
    expected_amount: Annotated[int, Field(ge=0)]  # montant affiché lors de la saisie
    received_amount: Annotated[int, Field(ge=0, le=100_000_000)]
    note: Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] = ""


class RemittanceOut(BaseModel):
    id: int
    created_at: datetime
    courier: PersonRef
    received_by: PersonRef
    expected_amount: int
    received_amount: int
    difference: int  # reçu − attendu : négatif = manquant
    note: str | None
    order_numbers: list[str]


class RemittancePage(BaseModel):
    items: list[RemittanceOut]
    total: int
    page: int
    page_size: int
