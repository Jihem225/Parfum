from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints

from app.core.slug import Slug
from app.modules.catalog.models import Gender, ProductStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Position = Annotated[int, Field(ge=0, le=10_000)]


class CollectionIn(BaseModel):
    name: Name
    slug: Slug | None = None  # déduit du nom si absent
    description: Description | None = None
    position: Position = 0
    is_active: bool = True


class CollectionPatch(BaseModel):
    name: Name | None = None
    slug: Slug | None = None
    description: Description | None = None
    position: Position | None = None
    is_active: bool | None = None


class CollectionOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    position: int
    is_active: bool
    product_count: int  # parfums publiés


class FamilyIn(BaseModel):
    name: Name
    slug: Slug | None = None
    position: Position = 0


class FamilyPatch(BaseModel):
    name: Name | None = None
    slug: Slug | None = None
    position: Position | None = None


class FamilyOut(BaseModel):
    id: int
    name: str
    slug: str
    position: int
    product_count: int  # parfums publiés


# --- Produits ------------------------------------------------------------------------------------

ProductName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
Notes = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=5000)]
Sku = Annotated[
    str,
    BeforeValidator(lambda v: v.strip().upper() if isinstance(v, str) else v),
    StringConstraints(pattern=r"^[A-Z0-9][A-Z0-9-]{1,39}$"),
]
Price = Annotated[int, Field(gt=0, le=10_000_000)]  # FCFA, entier
Volume = Annotated[int, Field(gt=0, le=1000)]  # millilitres


class ProductIn(BaseModel):
    name: ProductName
    slug: Slug | None = None
    collection_id: int
    family_id: int
    gender: Gender
    description: LongText = ""
    top_notes: Notes = ""
    heart_notes: Notes = ""
    base_notes: Notes = ""


class ProductPatch(BaseModel):
    name: ProductName | None = None
    slug: Slug | None = None
    collection_id: int | None = None
    family_id: int | None = None
    gender: Gender | None = None
    description: LongText | None = None
    top_notes: Notes | None = None
    heart_notes: Notes | None = None
    base_notes: Notes | None = None


class VariantIn(BaseModel):
    volume_ml: Volume
    sku: Sku
    price: Price
    cost_price: Annotated[int, Field(ge=0, le=10_000_000)] | None = None
    low_stock_threshold: Annotated[int, Field(ge=0, le=1000)] = 5
    is_active: bool = True


class VariantPatch(BaseModel):
    volume_ml: Volume | None = None
    sku: Sku | None = None
    price: Price | None = None
    cost_price: Annotated[int, Field(ge=0, le=10_000_000)] | None = None
    low_stock_threshold: Annotated[int, Field(ge=0, le=1000)] | None = None
    is_active: bool | None = None


class ImagePatch(BaseModel):
    alt_text: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class ImageOrderIn(BaseModel):
    image_ids: list[int]


class ImageOut(BaseModel):
    id: int
    url: str
    alt_text: str
    position: int


class TaxonRef(BaseModel):
    name: str
    slug: str


StockStatus = Literal["IN_STOCK", "LOW", "OUT"]


class AdminVariantOut(BaseModel):
    id: int
    volume_ml: int
    sku: str
    price: int
    cost_price: int | None
    stock_physical: int
    stock_reserved: int
    available: int
    low_stock_threshold: int
    is_active: bool


class AdminProductOut(BaseModel):
    id: int
    name: str
    slug: str
    collection_id: int
    family_id: int
    gender: Gender
    description: str
    top_notes: str
    heart_notes: str
    base_notes: str
    status: ProductStatus
    published_at: datetime | None
    variants: list[AdminVariantOut]
    images: list[ImageOut]


class AdminProductRow(BaseModel):
    id: int
    name: str
    slug: str
    collection: TaxonRef
    status: ProductStatus
    volumes: list[int]
    min_price: int | None
    max_price: int | None
    available: int
    image: ImageOut | None


class ProductCard(BaseModel):
    id: int
    name: str
    slug: str
    gender: Gender
    collection: TaxonRef
    family: TaxonRef
    min_price: int
    volumes: list[int]
    stock_status: StockStatus
    low_stock_count: int | None  # renseigné seulement quand il en reste peu (RG-16)
    image: ImageOut | None


class ProductPage(BaseModel):
    items: list[ProductCard]
    total: int
    page: int
    page_size: int


class PublicVariantOut(BaseModel):
    id: int
    volume_ml: int
    sku: str
    price: int
    stock_status: StockStatus
    low_stock_count: int | None


class ProductDetail(BaseModel):
    id: int
    name: str
    slug: str
    gender: Gender
    collection: TaxonRef
    family: TaxonRef
    description: str
    top_notes: str
    heart_notes: str
    base_notes: str
    variants: list[PublicVariantOut]
    images: list[ImageOut]
    similar: list[ProductCard]
