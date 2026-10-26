from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, Form, Query, UploadFile
from sqlalchemy import select

from app.core import images
from app.core.storage import get_storage
from app.modules.auth.deps import DB, BackOffice
from app.modules.catalog import products, queries
from app.modules.catalog.models import Collection, Gender, Product, ProductStatus, ProductVariant
from app.modules.catalog.schemas import (
    AdminProductOut,
    AdminProductRow,
    ImageOrderIn,
    ImageOut,
    ImagePatch,
    ProductDetail,
    ProductIn,
    ProductPage,
    ProductPatch,
    TaxonRef,
    VariantIn,
    VariantPatch,
)

public = APIRouter(prefix="/catalog", tags=["catalogue"])
admin = APIRouter(prefix="/admin", tags=["admin: catalogue"])


# --- Boutique ------------------------------------------------------------------------------------


@public.get("/products")
def list_products(
    db: DB,
    q: Annotated[str | None, Query(max_length=80)] = None,
    collection: str | None = None,
    family: str | None = None,
    gender: Gender | None = None,
    min_price: Annotated[int | None, Query(ge=0)] = None,
    max_price: Annotated[int | None, Query(ge=0)] = None,
    volume: Annotated[int | None, Query(gt=0)] = None,
    in_stock: bool = False,
    sort: queries.Sort = "nouveautes",
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    page_size: Annotated[int, Query(ge=1, le=48)] = 24,
) -> ProductPage:
    return queries.search(
        db,
        q=q.strip() if q else None,
        collection=collection,
        family=family,
        gender=gender,
        min_price=min_price,
        max_price=max_price,
        volume=volume,
        in_stock=in_stock,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@public.get("/products/{slug}")
def get_product(slug: str, db: DB) -> ProductDetail:
    return queries.detail(db, slug)


# --- Back-office : parfums -----------------------------------------------------------------------


@admin.get("/products")
def admin_list_products(
    _: BackOffice,
    db: DB,
    status: ProductStatus | None = None,
    collection_id: int | None = None,
    q: Annotated[str | None, Query(max_length=80)] = None,
) -> list[AdminProductRow]:
    query = select(Product).order_by(Product.name)
    if status:
        query = query.where(Product.status == status)
    if collection_id:
        query = query.where(Product.collection_id == collection_id)
    if q:
        sku_match = select(ProductVariant.product_id).where(queries.like(ProductVariant.sku, q))
        query = query.where(queries.like(Product.name, q) | Product.id.in_(sku_match))
    collections = {c.id: c for c in db.scalars(select(Collection))}
    rows = []
    # shortcut: une lecture par parfum (N+1), suffisant pour quelques centaines de parfums.
    for p in db.scalars(query):
        detail = products.admin_out(db, p)
        active = [v for v in detail.variants if v.is_active]
        rows.append(
            AdminProductRow(
                id=p.id,
                name=p.name,
                slug=p.slug,
                collection=TaxonRef(
                    name=collections[p.collection_id].name, slug=collections[p.collection_id].slug
                ),
                status=p.status,
                volumes=[v.volume_ml for v in detail.variants],
                min_price=min((v.price for v in active), default=None),
                max_price=max((v.price for v in active), default=None),
                available=sum(v.available for v in active),
                image=detail.images[0] if detail.images else None,
            )
        )
    return rows


@admin.post("/products", status_code=201)
def create_product(data: ProductIn, user: BackOffice, db: DB) -> AdminProductOut:
    product = products.create_product(db, data.model_dump(), actor_id=user.id)
    db.commit()
    return products.admin_out(db, product)


@admin.get("/products/{product_id}")
def admin_get_product(product_id: int, _: BackOffice, db: DB) -> AdminProductOut:
    return products.admin_out(db, products.get_product(db, product_id))


@admin.patch("/products/{product_id}")
def update_product(
    product_id: int, data: ProductPatch, user: BackOffice, db: DB
) -> AdminProductOut:
    product = products.get_product(db, product_id)
    products.update_product(db, product, data.model_dump(exclude_unset=True), actor_id=user.id)
    db.commit()
    return products.admin_out(db, product)


def _change_status(
    db: DB, product_id: int, status: ProductStatus, actor_id: int
) -> AdminProductOut:
    product = products.get_product(db, product_id)
    products.set_status(db, product, status, actor_id=actor_id)
    db.commit()
    return products.admin_out(db, product)


@admin.post("/products/{product_id}/publish")
def publish_product(product_id: int, user: BackOffice, db: DB) -> AdminProductOut:
    return _change_status(db, product_id, ProductStatus.PUBLISHED, user.id)


@admin.post("/products/{product_id}/unpublish")
def unpublish_product(product_id: int, user: BackOffice, db: DB) -> AdminProductOut:
    """Repasse en brouillon : sert aussi à restaurer un parfum archivé."""
    return _change_status(db, product_id, ProductStatus.DRAFT, user.id)


@admin.post("/products/{product_id}/archive")
def archive_product(product_id: int, user: BackOffice, db: DB) -> AdminProductOut:
    return _change_status(db, product_id, ProductStatus.ARCHIVED, user.id)


@admin.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, user: BackOffice, db: DB, background: BackgroundTasks) -> None:
    keys = products.delete_product(db, products.get_product(db, product_id), actor_id=user.id)
    db.commit()
    for key in keys:  # fichiers effacés seulement une fois la suppression validée en base
        background.add_task(get_storage().delete, key)


# --- Back-office : contenances -------------------------------------------------------------------


@admin.post("/products/{product_id}/variants", status_code=201)
def add_variant(product_id: int, data: VariantIn, user: BackOffice, db: DB) -> AdminProductOut:
    product = products.get_product(db, product_id)
    products.add_variant(db, product, data.model_dump(), actor_id=user.id)
    db.commit()
    return products.admin_out(db, product)


@admin.patch("/variants/{variant_id}")
def update_variant(
    variant_id: int, data: VariantPatch, user: BackOffice, db: DB
) -> AdminProductOut:
    variant = products.get_variant(db, variant_id)
    products.update_variant(db, variant, data.model_dump(exclude_unset=True), actor_id=user.id)
    db.commit()
    return products.admin_out(db, products.get_product(db, variant.product_id))


@admin.delete("/variants/{variant_id}", status_code=204)
def delete_variant(variant_id: int, user: BackOffice, db: DB) -> None:
    products.delete_variant(db, products.get_variant(db, variant_id), actor_id=user.id)
    db.commit()


# --- Back-office : images ------------------------------------------------------------------------


@admin.post("/products/{product_id}/images", status_code=201)
def upload_image(
    product_id: int,
    user: BackOffice,
    db: DB,
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str, Form(max_length=255)] = "",
) -> ImageOut:
    product = products.get_product(db, product_id)
    data = file.file.read(images.MAX_BYTES + 1)  # lecture bornée : jamais plus de 5 Mo en mémoire
    image = products.add_image(db, product, data, alt_text.strip(), actor_id=user.id)
    db.commit()
    return products.image_out(image)


@admin.patch("/products/{product_id}/images/{image_id}")
def update_image(
    product_id: int, image_id: int, data: ImagePatch, _: BackOffice, db: DB
) -> ImageOut:
    image = products.get_image(db, products.get_product(db, product_id), image_id)
    image.alt_text = data.alt_text
    db.commit()
    return products.image_out(image)


@admin.put("/products/{product_id}/images/order")
def reorder_images(product_id: int, data: ImageOrderIn, _: BackOffice, db: DB) -> AdminProductOut:
    product = products.get_product(db, product_id)
    products.reorder_images(db, product, data.image_ids)
    db.commit()
    return products.admin_out(db, product)


@admin.delete("/products/{product_id}/images/{image_id}", status_code=204)
def delete_image(
    product_id: int, image_id: int, user: BackOffice, db: DB, background: BackgroundTasks
) -> None:
    product = products.get_product(db, product_id)
    key = products.delete_image(
        db, product, products.get_image(db, product, image_id), actor_id=user.id
    )
    db.commit()
    background.add_task(get_storage().delete, key)
