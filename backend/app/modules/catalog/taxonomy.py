"""Collections et familles olfactives : même cycle de vie, une seule implémentation."""

from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.errors import AppError
from app.core.slug import slugify
from app.modules.catalog.models import Collection, OlfactoryFamily, Product, ProductStatus

Taxon = Collection | OlfactoryFamily
TaxonModel = type[Collection] | type[OlfactoryFamily]

_LABELS: dict[str, tuple[str, str, str]] = {
    # modèle → (nom d'entité pour l'audit, colonne produit, message « encore utilisé »)
    "collections": ("collection", "collection_id", "Cette collection contient encore des parfums."),
    "olfactory_families": ("family", "family_id", "Cette famille classe encore des parfums."),
}


def _label(model: TaxonModel) -> tuple[str, str, str]:
    return _LABELS[model.__tablename__]


def product_counts(db: Session, model: TaxonModel) -> dict[int, int]:
    column = getattr(Product, _label(model)[1])
    rows = db.execute(
        select(column, func.count())
        .where(Product.status == ProductStatus.PUBLISHED)
        .group_by(column)
    )
    return {taxon_id: count for taxon_id, count in rows}


def snapshot(taxon: Taxon) -> dict[str, Any]:
    keys = ("name", "slug", "position", "description", "is_active")
    return {k: getattr(taxon, k) for k in keys if hasattr(taxon, k)}


def _save(db: Session, taxon: Taxon) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "SLUG_TAKEN", "Cette adresse (slug) est déjà utilisée.") from exc


def create[T: (Collection, OlfactoryFamily)](
    db: Session, model: type[T], data: dict[str, Any], *, actor_id: int
) -> T:
    slug = data.pop("slug", None) or slugify(data["name"])
    if not slug:
        raise AppError(422, "INVALID_SLUG", "Impossible de déduire une adresse de ce nom.")
    taxon = model(slug=slug, **data)
    db.add(taxon)
    _save(db, taxon)
    entity = _label(model)[0]
    audit(
        db,
        actor_id=actor_id,
        action=f"{entity}.create",
        entity_type=entity,
        entity_id=taxon.id,
        after=snapshot(taxon),
    )
    return taxon


def update[T: (Collection, OlfactoryFamily)](
    db: Session, taxon: T, changes: dict[str, Any], *, actor_id: int
) -> T:
    before = snapshot(taxon)
    for key, value in changes.items():
        setattr(taxon, key, value)
    _save(db, taxon)
    entity = _label(type(taxon))[0]
    audit(
        db,
        actor_id=actor_id,
        action=f"{entity}.update",
        entity_type=entity,
        entity_id=taxon.id,
        before=before,
        after=snapshot(taxon),
    )
    return taxon


def delete(db: Session, taxon: Taxon, *, actor_id: int) -> None:
    entity, column, in_use = _label(type(taxon))
    # Un parfum archivé compte aussi : l'historique commercial doit rester rattaché (RG-04).
    if db.scalar(select(exists().where(getattr(Product, column) == taxon.id))):
        raise AppError(409, "IN_USE", in_use)
    audit(
        db,
        actor_id=actor_id,
        action=f"{entity}.delete",
        entity_type=entity,
        entity_id=taxon.id,
        before=snapshot(taxon),
    )
    db.delete(taxon)
