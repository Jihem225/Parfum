from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import BaseModel, Field, StringConstraints, model_validator

from app.modules.inventory.models import MovementType


class MovementIn(BaseModel):
    variant_id: int
    type: Literal[MovementType.ENTREE, MovementType.AJUSTEMENT]
    quantity: Annotated[int, Field(ge=-100_000, le=100_000)]  # signée pour un ajustement
    reason: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.quantity == 0:
            raise ValueError("La quantité ne peut pas être nulle.")
        if self.type == MovementType.ENTREE and self.quantity < 0:
            raise ValueError("Une entrée de stock doit être positive : utilisez un ajustement.")
        if self.type == MovementType.AJUSTEMENT and not self.reason:
            raise ValueError("Le motif est obligatoire pour un ajustement.")
        return self


class StockRow(BaseModel):
    variant_id: int
    product_id: int
    product_name: str
    volume_ml: int
    sku: str
    is_active: bool
    stock_physical: int
    stock_reserved: int
    available: int
    low_stock_threshold: int
    is_low: bool  # disponible au seuil ou en dessous (RG-17)


class MovementOut(BaseModel):
    id: int
    created_at: datetime
    variant_id: int
    product_name: str
    volume_ml: int
    sku: str
    type: MovementType
    delta_physical: int
    delta_reserved: int
    reason: str | None
    order_number: str | None
    author: str | None


class MovementPage(BaseModel):
    items: list[MovementOut]
    total: int
    page: int
    page_size: int
