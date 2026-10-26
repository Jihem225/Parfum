from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import AuditLog
from app.core.slug import slugify
from app.modules.catalog.models import Gender, Product, ProductStatus


def test_slugify() -> None:
    assert slugify("Bois & Épices") == "bois-epices"
    assert slugify("  Fleurs de lagune ") == "fleurs-de-lagune"
    assert slugify("Néroli d'Assinie") == "neroli-d-assinie"


def test_collection_lifecycle(manager: TestClient, db: Session) -> None:
    created = manager.post("/api/v1/admin/collections", json={"name": "Bois & Épices"})
    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == "bois-epices" and body["is_active"] is True

    renamed = manager.patch(
        f"/api/v1/admin/collections/{body['id']}", json={"name": "Bois et Épices", "position": 2}
    )
    assert renamed.json()["name"] == "Bois et Épices"
    assert renamed.json()["slug"] == "bois-epices"  # l'adresse ne change pas avec le nom (RG-05)

    log = db.scalar(select(AuditLog).where(AuditLog.action == "collection.update"))
    assert log is not None and log.before is not None and log.after is not None
    assert log.before["name"] == "Bois & Épices" and log.after["name"] == "Bois et Épices"

    assert manager.delete(f"/api/v1/admin/collections/{body['id']}").status_code == 204
    assert manager.get("/api/v1/admin/collections").json() == []


def test_duplicate_slug_is_refused(manager: TestClient) -> None:
    manager.post("/api/v1/admin/collections", json={"name": "Signatures"})
    response = manager.post("/api/v1/admin/collections", json={"name": "Signatures !"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SLUG_TAKEN"
    # La session reste utilisable après le refus.
    assert manager.post("/api/v1/admin/collections", json={"name": "Autre"}).status_code == 201


def test_invalid_slug_is_refused(manager: TestClient) -> None:
    response = manager.post("/api/v1/admin/collections", json={"name": "X Y", "slug": "Pas Bon"})
    assert response.status_code == 422


def test_customers_cannot_edit_the_catalog(client: TestClient) -> None:
    assert client.post("/api/v1/admin/collections", json={"name": "X"}).status_code == 401
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "aya@exemple.com",
            "password": "motdepasse-solide",
            "full_name": "Aya K.",
            "phone": "0708123456",
        },
    )
    response = client.post("/api/v1/admin/collections", json={"name": "Pirate"})
    assert response.status_code == 403


def test_shop_lists_only_active_collections_in_order(manager: TestClient) -> None:
    manager.post("/api/v1/admin/collections", json={"name": "Fleurs de lagune", "position": 2})
    manager.post("/api/v1/admin/collections", json={"name": "Signatures", "position": 1})
    hidden = manager.post(
        "/api/v1/admin/collections", json={"name": "Brouillon", "is_active": False}
    ).json()

    names = [c["name"] for c in manager.get("/api/v1/catalog/collections").json()]
    assert names == ["Signatures", "Fleurs de lagune"]
    assert manager.get("/api/v1/catalog/collections/signatures").status_code == 200
    assert manager.get(f"/api/v1/catalog/collections/{hidden['slug']}").status_code == 404


def _product(db: Session, collection_id: int, family_id: int, status: ProductStatus) -> None:
    db.add(
        Product(
            name=f"Parfum {status}",
            slug=f"parfum-{status.lower()}",
            collection_id=collection_id,
            family_id=family_id,
            gender=Gender.MIXTE,
            status=status,
        )
    )
    db.flush()


def test_counts_only_published_products_and_protects_used_taxons(
    manager: TestClient, db: Session
) -> None:
    collection = manager.post("/api/v1/admin/collections", json={"name": "Signatures"}).json()
    family = manager.post("/api/v1/admin/families", json={"name": "Ambré"}).json()
    _product(db, collection["id"], family["id"], ProductStatus.PUBLISHED)
    _product(db, collection["id"], family["id"], ProductStatus.DRAFT)

    assert manager.get("/api/v1/catalog/collections").json()[0]["product_count"] == 1
    assert manager.get("/api/v1/catalog/families").json()[0]["product_count"] == 1

    for url in (
        f"/api/v1/admin/collections/{collection['id']}",
        f"/api/v1/admin/families/{family['id']}",
    ):
        response = manager.delete(url)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "IN_USE"


def test_family_lifecycle(manager: TestClient) -> None:
    created = manager.post("/api/v1/admin/families", json={"name": "Hespéridé", "position": 3})
    assert created.status_code == 201 and created.json()["slug"] == "hesperide"
    family_id = created.json()["id"]
    assert (
        manager.patch(f"/api/v1/admin/families/{family_id}", json={"position": 1}).json()[
            "position"
        ]
        == 1
    )
    assert [f["name"] for f in manager.get("/api/v1/catalog/families").json()] == ["Hespéridé"]
    assert manager.delete(f"/api/v1/admin/families/{family_id}").status_code == 204
    assert manager.get("/api/v1/admin/families/999999").status_code == 405
    assert manager.patch("/api/v1/admin/families/999999", json={}).status_code == 404
