"""Lecture du catalogue public : recherche, filtres, tri, fiche produit, parfums similaires."""

from collections import defaultdict
from collections.abc import Sequence
from typing import Literal

from sqlalchemy import ColumnElement, Select, and_, exists, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session, aliased

from app.core.errors import AppError
from app.modules.catalog.models import (
    Collection,
    Gender,
    OlfactoryFamily,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
)
from app.modules.catalog.products import image_out, stock_status
from app.modules.catalog.schemas import (
    ProductCard,
    ProductDetail,
    ProductPage,
    PublicVariantOut,
    TaxonRef,
)
from app.modules.orders.models import Order, OrderItem, OrderStatus

Sort = Literal["nouveautes", "popularite", "prix_croissant", "prix_decroissant"]

_min_price = (
    select(func.min(ProductVariant.price))
    .where(ProductVariant.product_id == Product.id, ProductVariant.is_active)
    .scalar_subquery()
)
# Popularité = unités effectivement livrées (les commandes annulées ne comptent pas).
_units_sold = (
    select(func.coalesce(func.sum(OrderItem.quantity), 0))
    .join(ProductVariant, ProductVariant.id == OrderItem.variant_id)
    .join(Order, Order.id == OrderItem.order_id)
    .where(ProductVariant.product_id == Product.id, Order.status == OrderStatus.LIVREE)
    .scalar_subquery()
)


def like(column: ColumnElement[str] | InstrumentedAttribute[str], term: str) -> ColumnElement[bool]:
    escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return func.unaccent(column).ilike(func.unaccent(f"%{escaped}%"), escape="\\")


def _published() -> Select[Product]:
    """Publié ET au moins une contenance active : sinon rien à vendre."""
    return select(Product).where(
        Product.status == ProductStatus.PUBLISHED,
        exists().where(ProductVariant.product_id == Product.id, ProductVariant.is_active),
    )


def cards(db: Session, products: Sequence[Product]) -> list[ProductCard]:
    ids = [p.id for p in products]
    if not ids:
        return []
    variants: dict[int, list[ProductVariant]] = defaultdict(list)
    for v in db.scalars(
        select(ProductVariant)
        .where(ProductVariant.product_id.in_(ids), ProductVariant.is_active)
        .order_by(ProductVariant.volume_ml)
    ):
        variants[v.product_id].append(v)
    first_images: dict[int, ProductImage] = {}
    for img in db.scalars(
        select(ProductImage).where(ProductImage.product_id.in_(ids)).order_by(ProductImage.position)
    ):
        first_images.setdefault(img.product_id, img)
    collections = {c.id: c for c in db.scalars(select(Collection))}
    families = {f.id: f for f in db.scalars(select(OlfactoryFamily))}

    result = []
    for p in products:
        vs = variants[p.id]
        status, low = stock_status(sum(v.stock_physical - v.stock_reserved for v in vs))
        image = first_images.get(p.id)
        result.append(
            ProductCard(
                id=p.id,
                name=p.name,
                slug=p.slug,
                gender=p.gender,
                collection=TaxonRef(
                    name=collections[p.collection_id].name, slug=collections[p.collection_id].slug
                ),
                family=TaxonRef(name=families[p.family_id].name, slug=families[p.family_id].slug),
                min_price=min(v.price for v in vs),
                volumes=[v.volume_ml for v in vs],
                stock_status=status,
                low_stock_count=low,
                image=image_out(image) if image else None,
            )
        )
    return result


def search(
    db: Session,
    *,
    q: str | None,
    collection: str | None,
    family: str | None,
    gender: Gender | None,
    min_price: int | None,
    max_price: int | None,
    volume: int | None,
    in_stock: bool,
    sort: Sort,
    page: int,
    page_size: int,
) -> ProductPage:
    query = _published()
    if q:
        query = query.where(
            or_(
                *(
                    like(c, q)
                    for c in (
                        Product.name,
                        Product.top_notes,
                        Product.heart_notes,
                        Product.base_notes,
                    )
                )
            )
        )
    if collection:
        query = query.join(Collection, Collection.id == Product.collection_id).where(
            Collection.slug == collection, Collection.is_active
        )
    if family:
        query = query.join(OlfactoryFamily, OlfactoryFamily.id == Product.family_id).where(
            OlfactoryFamily.slug == family
        )
    if gender:
        query = query.where(Product.gender == gender)
    # Prix, contenance et disponibilité doivent porter sur la MÊME contenance.
    v = aliased(ProductVariant)
    variant_filters: list[ColumnElement[bool]] = []
    if min_price is not None:
        variant_filters.append(v.price >= min_price)
    if max_price is not None:
        variant_filters.append(v.price <= max_price)
    if volume is not None:
        variant_filters.append(v.volume_ml == volume)
    if in_stock:
        variant_filters.append(v.stock_physical - v.stock_reserved > 0)
    if variant_filters:
        query = query.where(
            exists().where(and_(v.product_id == Product.id, v.is_active, *variant_filters))
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    order = {
        "nouveautes": (Product.published_at.desc(),),
        "popularite": (_units_sold.desc(), Product.published_at.desc()),
        "prix_croissant": (_min_price.asc(),),
        "prix_decroissant": (_min_price.desc(),),
    }[sort]
    products = db.scalars(
        query.order_by(*order, Product.id).limit(page_size).offset((page - 1) * page_size)
    ).all()
    return ProductPage(items=cards(db, products), total=total, page=page, page_size=page_size)


def _public_variant(v: ProductVariant) -> PublicVariantOut:
    status, low = stock_status(v.stock_physical - v.stock_reserved)
    return PublicVariantOut(
        id=v.id,
        volume_ml=v.volume_ml,
        sku=v.sku,
        price=v.price,
        stock_status=status,
        low_stock_count=low,
    )


def detail(db: Session, slug: str) -> ProductDetail:
    product = db.scalar(_published().where(Product.slug == slug))
    if product is None:
        raise AppError(404, "NOT_FOUND", "Parfum introuvable.")
    collection = db.get(Collection, product.collection_id)
    family = db.get(OlfactoryFamily, product.family_id)
    assert collection is not None and family is not None  # clés étrangères NOT NULL
    variants = db.scalars(
        select(ProductVariant)
        .where(ProductVariant.product_id == product.id, ProductVariant.is_active)
        .order_by(ProductVariant.volume_ml)
    )
    product_images = db.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.position)
    )
    similar = db.scalars(
        _published()
        .where(Product.family_id == product.family_id, Product.id != product.id)
        .order_by(_units_sold.desc(), Product.published_at.desc(), Product.id)
        .limit(4)
    ).all()
    return ProductDetail(
        id=product.id,
        name=product.name,
        slug=product.slug,
        gender=product.gender,
        collection=TaxonRef(name=collection.name, slug=collection.slug),
        family=TaxonRef(name=family.name, slug=family.slug),
        description=product.description,
        top_notes=product.top_notes,
        heart_notes=product.heart_notes,
        base_notes=product.base_notes,
        variants=[_public_variant(v) for v in variants],
        images=[image_out(i) for i in product_images],
        similar=cards(db, similar),
    )
