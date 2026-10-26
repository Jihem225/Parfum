"""Back-office des parfums : fiche, contenances, images, cycle de publication."""

import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import images
from app.core.audit import audit
from app.core.errors import AppError
from app.core.slug import slugify
from app.core.storage import get_storage
from app.modules.catalog.models import (
    Collection,
    OlfactoryFamily,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
)
from app.modules.catalog.schemas import AdminProductOut, AdminVariantOut, ImageOut, StockStatus
from app.modules.inventory.models import StockMovement
from app.modules.orders.models import OrderItem

LOW_STOCK_DISPLAY = 5  # RG-16 : « Plus que N » à partir de ce seuil

_CONFLICTS = {
    "uq_products_slug": ("SLUG_TAKEN", "Cette adresse (slug) est déjà utilisée."),
    "uq_product_variants_sku": ("SKU_TAKEN", "Ce SKU est déjà utilisé."),
    "uq_product_variants_product_id": ("VOLUME_TAKEN", "Cette contenance existe déjà."),
}


def stock_status(available: int) -> tuple[StockStatus, int | None]:
    if available <= 0:
        return "OUT", None
    if available <= LOW_STOCK_DISPLAY:
        return "LOW", available
    return "IN_STOCK", None


def image_out(image: ProductImage) -> ImageOut:
    return ImageOut(
        id=image.id,
        url=get_storage().url(image.storage_key),
        alt_text=image.alt_text,
        position=image.position,
    )


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None) or ""
        code, message = _CONFLICTS.get(
            constraint, ("CONFLICT", "Conflit avec une donnée existante.")
        )
        raise AppError(409, code, message) from exc


def _snapshot(obj: Product | ProductVariant, keys: tuple[str, ...]) -> dict[str, Any]:
    values = {k: getattr(obj, k) for k in keys}
    return {k: v.value if isinstance(v, enum.Enum) else v for k, v in values.items()}


PRODUCT_KEYS = ("name", "slug", "collection_id", "family_id", "gender", "status")
VARIANT_KEYS = ("volume_ml", "sku", "price", "cost_price", "low_stock_threshold", "is_active")


def get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise AppError(404, "NOT_FOUND", "Parfum introuvable.")
    return product


def _check_taxons(db: Session, collection_id: int | None, family_id: int | None) -> None:
    if collection_id is not None and db.get(Collection, collection_id) is None:
        raise AppError(422, "UNKNOWN_COLLECTION", "Collection inconnue.")
    if family_id is not None and db.get(OlfactoryFamily, family_id) is None:
        raise AppError(422, "UNKNOWN_FAMILY", "Famille olfactive inconnue.")


def create_product(db: Session, data: dict[str, Any], *, actor_id: int) -> Product:
    _check_taxons(db, data["collection_id"], data["family_id"])
    slug = data.pop("slug", None) or slugify(data["name"])
    product = Product(slug=slug, status=ProductStatus.DRAFT, **data)
    db.add(product)
    _flush(db)
    audit(
        db,
        actor_id=actor_id,
        action="product.create",
        entity_type="product",
        entity_id=product.id,
        after=_snapshot(product, PRODUCT_KEYS),
    )
    return product


def update_product(
    db: Session, product: Product, changes: dict[str, Any], *, actor_id: int
) -> None:
    _check_taxons(db, changes.get("collection_id"), changes.get("family_id"))
    before = _snapshot(product, PRODUCT_KEYS)
    for key, value in changes.items():
        setattr(product, key, value)
    _flush(db)
    audit(
        db,
        actor_id=actor_id,
        action="product.update",
        entity_type="product",
        entity_id=product.id,
        before=before,
        after=_snapshot(product, PRODUCT_KEYS),
    )


def publication_problems(db: Session, product: Product) -> list[str]:
    """RG-03 : au moins une contenance active avec un prix, et au moins une image."""
    problems = []
    if not db.scalar(
        select(exists().where(ProductVariant.product_id == product.id, ProductVariant.is_active))
    ):
        problems.append("Ajoutez au moins une contenance active avec un prix.")
    if not db.scalar(select(exists().where(ProductImage.product_id == product.id))):
        problems.append("Ajoutez au moins une image.")
    return problems


def set_status(db: Session, product: Product, status: ProductStatus, *, actor_id: int) -> None:
    if status == ProductStatus.PUBLISHED:
        problems = publication_problems(db, product)
        if problems:
            raise AppError(
                409, "NOT_PUBLISHABLE", "Ce parfum ne peut pas encore être publié.", problems
            )
        product.published_at = product.published_at or datetime.now(UTC)
    before = product.status.value
    product.status = status
    audit(
        db,
        actor_id=actor_id,
        action=f"product.status.{status.value.lower()}",
        entity_type="product",
        entity_id=product.id,
        before={"status": before},
        after={"status": status.value},
    )


def _variants_have_history(db: Session, variant_ids: list[int]) -> bool:
    if not variant_ids:
        return False
    return bool(
        db.scalar(select(exists().where(StockMovement.variant_id.in_(variant_ids))))
        or db.scalar(select(exists().where(OrderItem.variant_id.in_(variant_ids))))
    )


def delete_product(db: Session, product: Product, *, actor_id: int) -> list[str]:
    """Renvoie les clés d'images à effacer du stockage une fois la transaction validée."""
    variant_ids = list(
        db.scalars(select(ProductVariant.id).where(ProductVariant.product_id == product.id))
    )
    if _variants_have_history(db, variant_ids):
        raise AppError(
            409, "HAS_HISTORY", "Ce parfum a un historique (stock ou commandes) : archivez-le."
        )
    keys = list(
        db.scalars(select(ProductImage.storage_key).where(ProductImage.product_id == product.id))
    )
    audit(
        db,
        actor_id=actor_id,
        action="product.delete",
        entity_type="product",
        entity_id=product.id,
        before=_snapshot(product, PRODUCT_KEYS),
    )
    db.delete(product)
    return keys


def get_variant(db: Session, variant_id: int) -> ProductVariant:
    variant = db.get(ProductVariant, variant_id)
    if variant is None:
        raise AppError(404, "NOT_FOUND", "Contenance introuvable.")
    return variant


def add_variant(
    db: Session, product: Product, data: dict[str, Any], *, actor_id: int
) -> ProductVariant:
    variant = ProductVariant(product_id=product.id, **data)
    db.add(variant)
    _flush(db)
    audit(
        db,
        actor_id=actor_id,
        action="variant.create",
        entity_type="variant",
        entity_id=variant.id,
        after=_snapshot(variant, VARIANT_KEYS),
    )
    return variant


def update_variant(
    db: Session, variant: ProductVariant, changes: dict[str, Any], *, actor_id: int
) -> None:
    before = _snapshot(variant, VARIANT_KEYS)
    for key, value in changes.items():
        setattr(variant, key, value)
    _flush(db)
    # Les changements de prix sont tracés (RG-53) comme toute modification de contenance.
    audit(
        db,
        actor_id=actor_id,
        action="variant.update",
        entity_type="variant",
        entity_id=variant.id,
        before=before,
        after=_snapshot(variant, VARIANT_KEYS),
    )


def delete_variant(db: Session, variant: ProductVariant, *, actor_id: int) -> None:
    if _variants_have_history(db, [variant.id]):
        raise AppError(409, "HAS_HISTORY", "Cette contenance a un historique : désactivez-la.")
    audit(
        db,
        actor_id=actor_id,
        action="variant.delete",
        entity_type="variant",
        entity_id=variant.id,
        before=_snapshot(variant, VARIANT_KEYS),
    )
    db.delete(variant)


def add_image(
    db: Session, product: Product, data: bytes, alt_text: str, *, actor_id: int
) -> ProductImage:
    webp = images.to_webp(data)
    key = f"products/{product.id}/{uuid.uuid4().hex}.webp"
    get_storage().put(key, webp, "image/webp")
    position = db.scalar(
        select(func.coalesce(func.max(ProductImage.position) + 1, 0)).where(
            ProductImage.product_id == product.id
        )
    )
    image = ProductImage(
        product_id=product.id, storage_key=key, alt_text=alt_text, position=position
    )
    db.add(image)
    db.flush()
    audit(
        db,
        actor_id=actor_id,
        action="image.add",
        entity_type="product",
        entity_id=product.id,
        after={"image_id": image.id},
    )
    return image


def get_image(db: Session, product: Product, image_id: int) -> ProductImage:
    image = db.get(ProductImage, image_id)
    if image is None or image.product_id != product.id:
        raise AppError(404, "NOT_FOUND", "Image introuvable.")
    return image


def delete_image(db: Session, product: Product, image: ProductImage, *, actor_id: int) -> str:
    audit(
        db,
        actor_id=actor_id,
        action="image.delete",
        entity_type="product",
        entity_id=product.id,
        before={"image_id": image.id},
    )
    db.delete(image)
    return image.storage_key


def reorder_images(db: Session, product: Product, image_ids: list[int]) -> None:
    current = {
        i.id: i
        for i in db.scalars(select(ProductImage).where(ProductImage.product_id == product.id))
    }
    if sorted(image_ids) != sorted(current):
        raise AppError(422, "INVALID_ORDER", "La liste doit contenir toutes les images du parfum.")
    for position, image_id in enumerate(image_ids):
        current[image_id].position = position


def admin_out(db: Session, product: Product) -> AdminProductOut:
    variants = db.scalars(
        select(ProductVariant)
        .where(ProductVariant.product_id == product.id)
        .order_by(ProductVariant.volume_ml)
    )
    product_images = db.scalars(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.position)
    )
    return AdminProductOut(
        id=product.id,
        name=product.name,
        slug=product.slug,
        collection_id=product.collection_id,
        family_id=product.family_id,
        gender=product.gender,
        description=product.description,
        top_notes=product.top_notes,
        heart_notes=product.heart_notes,
        base_notes=product.base_notes,
        status=product.status,
        published_at=product.published_at,
        variants=[
            AdminVariantOut(
                id=v.id,
                volume_ml=v.volume_ml,
                sku=v.sku,
                price=v.price,
                cost_price=v.cost_price,
                stock_physical=v.stock_physical,
                stock_reserved=v.stock_reserved,
                available=v.stock_physical - v.stock_reserved,
                low_stock_threshold=v.low_stock_threshold,
                is_active=v.is_active,
            )
            for v in variants
        ],
        images=[image_out(i) for i in product_images],
    )
