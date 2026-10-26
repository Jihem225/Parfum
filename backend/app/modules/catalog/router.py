from fastapi import APIRouter
from sqlalchemy import select

from app.core.errors import AppError
from app.modules.auth.deps import DB, BackOffice
from app.modules.catalog import taxonomy
from app.modules.catalog.models import Collection, OlfactoryFamily
from app.modules.catalog.schemas import (
    CollectionIn,
    CollectionOut,
    CollectionPatch,
    FamilyIn,
    FamilyOut,
    FamilyPatch,
)

public = APIRouter(prefix="/catalog", tags=["catalogue"])
admin = APIRouter(prefix="/admin", tags=["admin: catalogue"])


def _collection_out(c: Collection, counts: dict[int, int]) -> CollectionOut:
    return CollectionOut(
        id=c.id,
        name=c.name,
        slug=c.slug,
        description=c.description,
        position=c.position,
        is_active=c.is_active,
        product_count=counts.get(c.id, 0),
    )


def _family_out(f: OlfactoryFamily, counts: dict[int, int]) -> FamilyOut:
    return FamilyOut(
        id=f.id, name=f.name, slug=f.slug, position=f.position, product_count=counts.get(f.id, 0)
    )


def _get[T: (Collection, OlfactoryFamily)](db: DB, model: type[T], taxon_id: int) -> T:
    taxon = db.get(model, taxon_id)
    if taxon is None:
        raise AppError(404, "NOT_FOUND", "Élément introuvable.")
    return taxon


# --- Boutique (lecture publique) ---------------------------------------------------------------


@public.get("/collections")
def list_public_collections(db: DB) -> list[CollectionOut]:
    counts = taxonomy.product_counts(db, Collection)
    rows = db.scalars(
        select(Collection)
        .where(Collection.is_active)
        .order_by(Collection.position, Collection.name)
    )
    return [_collection_out(c, counts) for c in rows]


@public.get("/collections/{slug}")
def get_public_collection(slug: str, db: DB) -> CollectionOut:
    collection = db.scalar(select(Collection).where(Collection.slug == slug, Collection.is_active))
    if collection is None:
        raise AppError(404, "NOT_FOUND", "Collection introuvable.")
    return _collection_out(collection, taxonomy.product_counts(db, Collection))


@public.get("/families")
def list_public_families(db: DB) -> list[FamilyOut]:
    counts = taxonomy.product_counts(db, OlfactoryFamily)
    rows = db.scalars(
        select(OlfactoryFamily).order_by(OlfactoryFamily.position, OlfactoryFamily.name)
    )
    return [_family_out(f, counts) for f in rows]


# --- Back-office --------------------------------------------------------------------------------


@admin.get("/collections")
def list_collections(_: BackOffice, db: DB) -> list[CollectionOut]:
    counts = taxonomy.product_counts(db, Collection)
    rows = db.scalars(select(Collection).order_by(Collection.position, Collection.name))
    return [_collection_out(c, counts) for c in rows]


@admin.post("/collections", status_code=201)
def create_collection(data: CollectionIn, user: BackOffice, db: DB) -> CollectionOut:
    collection = taxonomy.create(db, Collection, data.model_dump(), actor_id=user.id)
    db.commit()
    return _collection_out(collection, {})


@admin.patch("/collections/{collection_id}")
def update_collection(
    collection_id: int, data: CollectionPatch, user: BackOffice, db: DB
) -> CollectionOut:
    collection = _get(db, Collection, collection_id)
    taxonomy.update(db, collection, data.model_dump(exclude_unset=True), actor_id=user.id)
    db.commit()
    return _collection_out(collection, taxonomy.product_counts(db, Collection))


@admin.delete("/collections/{collection_id}", status_code=204)
def delete_collection(collection_id: int, user: BackOffice, db: DB) -> None:
    taxonomy.delete(db, _get(db, Collection, collection_id), actor_id=user.id)
    db.commit()


@admin.get("/families")
def list_families(_: BackOffice, db: DB) -> list[FamilyOut]:
    return list_public_families(db)


@admin.post("/families", status_code=201)
def create_family(data: FamilyIn, user: BackOffice, db: DB) -> FamilyOut:
    family = taxonomy.create(db, OlfactoryFamily, data.model_dump(), actor_id=user.id)
    db.commit()
    return _family_out(family, {})


@admin.patch("/families/{family_id}")
def update_family(family_id: int, data: FamilyPatch, user: BackOffice, db: DB) -> FamilyOut:
    family = _get(db, OlfactoryFamily, family_id)
    taxonomy.update(db, family, data.model_dump(exclude_unset=True), actor_id=user.id)
    db.commit()
    return _family_out(family, taxonomy.product_counts(db, OlfactoryFamily))


@admin.delete("/families/{family_id}", status_code=204)
def delete_family(family_id: int, user: BackOffice, db: DB) -> None:
    taxonomy.delete(db, _get(db, OlfactoryFamily, family_id), actor_id=user.id)
    db.commit()
