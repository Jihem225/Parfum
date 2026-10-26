from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.modules.auth.deps import DB, BackOffice
from app.modules.auth.models import User
from app.modules.catalog import products, queries
from app.modules.catalog.models import Product, ProductVariant
from app.modules.inventory import service
from app.modules.inventory.models import MovementType, StockMovement
from app.modules.inventory.schemas import MovementIn, MovementOut, MovementPage, StockRow
from app.modules.orders.models import Order

admin = APIRouter(prefix="/admin/stock", tags=["admin: stock"])

_AVAILABLE = ProductVariant.stock_physical - ProductVariant.stock_reserved
_IS_LOW = ProductVariant.is_active & (_AVAILABLE <= ProductVariant.low_stock_threshold)


def _row(variant: ProductVariant, product_name: str) -> StockRow:
    available = variant.stock_physical - variant.stock_reserved
    return StockRow(
        variant_id=variant.id,
        product_id=variant.product_id,
        product_name=product_name,
        volume_ml=variant.volume_ml,
        sku=variant.sku,
        is_active=variant.is_active,
        stock_physical=variant.stock_physical,
        stock_reserved=variant.stock_reserved,
        available=available,
        low_stock_threshold=variant.low_stock_threshold,
        is_low=variant.is_active and available <= variant.low_stock_threshold,
    )


@admin.get("")
def stock_list(
    _: BackOffice,
    db: DB,
    low_only: bool = False,
    q: Annotated[str | None, Query(max_length=80)] = None,
) -> list[StockRow]:
    """État du stock par contenance ; `low_only` donne les alertes du tableau de bord."""
    query = (
        select(ProductVariant, Product.name)
        .join(Product)
        .order_by(Product.name, ProductVariant.volume_ml)
    )
    if low_only:
        query = query.where(_IS_LOW)
    if q:
        query = query.where(queries.like(Product.name, q) | queries.like(ProductVariant.sku, q))
    return [_row(v, name) for v, name in db.execute(query)]


@admin.post("/movements", status_code=201)
def add_movement(data: MovementIn, user: BackOffice, db: DB) -> StockRow:
    variant = products.get_variant(db, data.variant_id)
    if data.type == MovementType.ENTREE:
        service.receive(db, variant, data.quantity, data.reason or None, user_id=user.id)
    else:
        service.adjust(db, variant, data.quantity, data.reason, user_id=user.id)
    db.commit()
    name = db.scalars(select(Product.name).where(Product.id == variant.product_id)).one()
    return _row(variant, name)


@admin.get("/movements")
def movements(
    _: BackOffice,
    db: DB,
    variant_id: int | None = None,
    type: MovementType | None = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
) -> MovementPage:
    """Historique des mouvements, du plus récent au plus ancien."""
    filters = []
    if variant_id is not None:
        filters.append(StockMovement.variant_id == variant_id)
    if type is not None:
        filters.append(StockMovement.type == type)
    total = db.scalar(select(func.count()).select_from(StockMovement).where(*filters)) or 0
    rows = db.execute(
        select(StockMovement, ProductVariant, Product.name, Order.number, User.full_name)
        .join(ProductVariant, StockMovement.variant_id == ProductVariant.id)
        .join(Product)
        .outerjoin(Order, StockMovement.order_id == Order.id)
        .outerjoin(User, StockMovement.user_id == User.id)
        .where(*filters)
        .order_by(StockMovement.id.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    return MovementPage(
        items=[
            MovementOut(
                id=m.id,
                created_at=m.created_at,
                variant_id=v.id,
                product_name=name,
                volume_ml=v.volume_ml,
                sku=v.sku,
                type=m.type,
                delta_physical=m.delta_physical,
                delta_reserved=m.delta_reserved,
                reason=m.reason,
                order_number=number,
                author=author,
            )
            for m, v, name, number, author in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
