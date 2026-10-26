from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.modules.catalog.schemas import ImageOut

Quantity = Annotated[int, Field(ge=1, le=5)]  # RG-22


class CartItemIn(BaseModel):
    variant_id: int
    quantity: Quantity = 1


class QuantityIn(BaseModel):
    quantity: Quantity


# UNAVAILABLE : parfum retiré ou contenance désactivée ; INSUFFICIENT_STOCK : quantité > disponible.
CartIssue = Literal["UNAVAILABLE", "INSUFFICIENT_STOCK"]


class CartLine(BaseModel):
    variant_id: int
    product_name: str
    product_slug: str
    volume_ml: int
    sku: str
    unit_price: int  # prix actuel, relu à chaque affichage (RG-21)
    quantity: int
    line_total: int
    max_quantity: int  # min(5, disponible) : ne dévoile pas le stock exact
    image: ImageOut | None
    issue: CartIssue | None


class CartOut(BaseModel):
    items: list[CartLine]
    item_count: int
    subtotal: int
    exceeds_cod_limit: bool  # RG-23 : au-delà, le client est invité à contacter la boutique
    can_checkout: bool
