import threading
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import engine
from app.core.errors import AppError
from app.core.models import AuditLog
from app.modules.catalog.models import (
    Collection,
    Gender,
    OlfactoryFamily,
    Product,
    ProductVariant,
)
from app.modules.inventory import service
from app.modules.inventory.models import StockMovement
from tests.conftest import Outbox

ADMIN = "/api/v1/admin"
STOCK = f"{ADMIN}/stock"


def variants(manager: TestClient, *stocks: int, threshold: int = 5) -> list[int]:
    """Un parfum en brouillon avec une contenance par stock initial demandé."""
    collection = manager.post(f"{ADMIN}/collections", json={"name": "Signatures"}).json()
    family = manager.post(f"{ADMIN}/families", json={"name": "Ambré"}).json()
    product = manager.post(
        f"{ADMIN}/products",
        json={
            "name": "Ambre Nuit",
            "collection_id": collection["id"],
            "family_id": family["id"],
            "gender": "MIXTE",
        },
    ).json()
    ids = []
    for i, stock in enumerate(stocks):
        r = manager.post(
            f"{ADMIN}/products/{product['id']}/variants",
            json={
                "volume_ml": 30 + 20 * i,
                "sku": f"AMB-{i}",
                "price": 30000,
                "initial_stock": stock,
                "low_stock_threshold": threshold,
            },
        )
        assert r.status_code == 201, r.json()
        ids.append(r.json()["variants"][i]["id"])
    return ids


def stock(db: Session, variant_id: int) -> tuple[int, int]:
    v = db.get_one(ProductVariant, variant_id)
    db.refresh(v)
    return v.stock_physical, v.stock_reserved


def moves(db: Session, variant_id: int) -> list[tuple[str, int, int]]:
    rows = db.scalars(
        select(StockMovement)
        .where(StockMovement.variant_id == variant_id)
        .order_by(StockMovement.id)
    )
    return [(m.type.value, m.delta_physical, m.delta_reserved) for m in rows]


# --- Back-office ---------------------------------------------------------------------------------


def test_initial_stock_is_an_entry_movement(manager: TestClient, db: Session) -> None:
    [v] = variants(manager, 12)
    assert stock(db, v) == (12, 0)
    history = manager.get(f"{STOCK}/movements", params={"variant_id": v}).json()
    assert history["total"] == 1
    entry = history["items"][0]
    assert (entry["type"], entry["delta_physical"], entry["reason"]) == (
        "ENTREE",
        12,
        "Stock initial",
    )
    assert entry["author"] == "Awa Koné"


def test_entry_and_adjustment(manager: TestClient, db: Session) -> None:
    [v] = variants(manager, 0)
    r = manager.post(
        f"{STOCK}/movements",
        json={"variant_id": v, "type": "ENTREE", "quantity": 20, "reason": "Livraison n° 42"},
    )
    assert r.status_code == 201
    assert (r.json()["stock_physical"], r.json()["available"]) == (20, 20)
    r = manager.post(
        f"{STOCK}/movements",
        json={"variant_id": v, "type": "AJUSTEMENT", "quantity": -2, "reason": "Flacons cassés"},
    )
    assert r.status_code == 201 and r.json()["stock_physical"] == 18
    assert moves(db, v) == [("ENTREE", 20, 0), ("AJUSTEMENT", -2, 0)]
    logged = db.scalars(
        select(AuditLog).where(AuditLog.action == "stock.adjust", AuditLog.entity_id == str(v))
    ).one()
    assert logged.before == {"stock_physical": 20}
    assert logged.after == {"stock_physical": 18, "reason": "Flacons cassés"}


@pytest.mark.parametrize(
    "body",
    [
        {"type": "AJUSTEMENT", "quantity": -1, "reason": "  "},  # motif obligatoire
        {"type": "ENTREE", "quantity": -3},  # une entrée est positive
        {"type": "ENTREE", "quantity": 0},
        {"type": "PERTE", "quantity": 1, "reason": "x"},  # réservé aux retours de commande
    ],
)
def test_invalid_movements_are_refused(manager: TestClient, body: dict[str, Any]) -> None:
    [v] = variants(manager, 5)
    assert manager.post(f"{STOCK}/movements", json={"variant_id": v, **body}).status_code == 422


def test_adjustment_cannot_go_below_reserved(manager: TestClient, db: Session) -> None:
    [v] = variants(manager, 5)
    service.reserve(db, {v: 4}, order_id=None)
    r = manager.post(
        f"{STOCK}/movements",
        json={"variant_id": v, "type": "AJUSTEMENT", "quantity": -2, "reason": "Inventaire"},
    )
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "BELOW_RESERVED"
    assert stock(db, v) == (5, 4)
    r = manager.post(
        f"{STOCK}/movements",
        json={"variant_id": v, "type": "AJUSTEMENT", "quantity": -1, "reason": "Inventaire"},
    )
    assert r.status_code == 201 and r.json()["available"] == 0


def test_low_stock_list(manager: TestClient, db: Session) -> None:
    low, ok, inactive = variants(manager, 3, 50, 0)
    manager.patch(f"{ADMIN}/variants/{inactive}", json={"is_active": False})
    rows = manager.get(STOCK, params={"low_only": True}).json()
    assert [r["variant_id"] for r in rows] == [low]
    assert len(manager.get(STOCK, params={"q": "amb-1"}).json()) == 1


def test_crossing_the_threshold_sends_one_email(
    manager: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch, outbox: Outbox
) -> None:
    sent = outbox
    monkeypatch.setattr(settings, "shop_notification_email", "boutique@exemple.com")
    [v] = variants(manager, 7)

    def remove(quantity: int) -> None:
        r = manager.post(
            f"{STOCK}/movements",
            json={"variant_id": v, "type": "AJUSTEMENT", "quantity": -quantity, "reason": "Test"},
        )
        assert r.status_code == 201

    remove(1)  # 6 : au-dessus du seuil de 5
    assert sent == []
    remove(1)  # 5 : franchissement
    assert len(sent) == 1
    to, subject, body = sent[0]
    assert to == "boutique@exemple.com" and "Ambre Nuit" in subject
    assert "(AMB-0) : 5 disponible(s), seuil 5" in body
    remove(1)  # 4 : déjà sous le seuil, pas de nouvel e-mail
    assert len(sent) == 1


def test_customers_and_couriers_cannot_touch_stock(client: TestClient) -> None:
    assert client.get(STOCK).status_code == 401
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "aya@exemple.com",
            "password": "motdepasse-solide",
            "full_name": "Aya K.",
            "phone": "0708123456",
        },
    )
    assert client.get(STOCK).status_code == 403
    r = client.post(f"{STOCK}/movements", json={"variant_id": 1, "type": "ENTREE", "quantity": 5})
    assert r.status_code == 403


# --- Fonctions utilisées par les commandes ------------------------------------------------


def test_reservation_is_all_or_nothing(manager: TestClient, db: Session) -> None:
    enough, short = variants(manager, 10, 1)
    with pytest.raises(AppError) as exc:
        service.reserve(db, {short: 2, enough: 3}, order_id=None)
    assert exc.value.code == "INSUFFICIENT_STOCK"
    assert exc.value.details == [{"variant_id": short, "requested": 2, "available": 1}]
    assert stock(db, enough) == (10, 0)  # la ligne valide a été annulée elle aussi
    assert moves(db, enough) == [("ENTREE", 10, 0)]


def test_inactive_variant_cannot_be_reserved(manager: TestClient, db: Session) -> None:
    [v] = variants(manager, 10)
    manager.patch(f"{ADMIN}/variants/{v}", json={"is_active": False})
    with pytest.raises(AppError):
        service.reserve(db, {v: 1}, order_id=None)


def test_order_lifecycle_movements(manager: TestClient, db: Session) -> None:
    [v] = variants(manager, 10)
    service.reserve(db, {v: 3}, order_id=None)
    assert stock(db, v) == (10, 3)
    service.release(db, {v: 1}, order_id=None, user_id=None)
    assert stock(db, v) == (10, 2)
    service.ship(db, {v: 2}, order_id=None, user_id=None)
    assert stock(db, v) == (8, 0)
    service.restock_return(db, {v: 1}, order_id=None, user_id=None)
    assert stock(db, v) == (9, 0)
    assert moves(db, v)[1:] == [
        ("RESERVATION", 0, 3),
        ("LIBERATION", 0, -1),
        ("SORTIE_VENTE", -2, -2),
        ("RETOUR", 1, 0),
    ]
    with pytest.raises(AppError) as exc:
        service.ship(db, {v: 1}, order_id=None, user_id=None)
    assert exc.value.code == "STOCK_CONFLICT"  # rien de réservé : sortie impossible


def test_concurrent_orders_on_the_last_unit() -> None:
    """Vraies transactions simultanées (une connexion par commande) sur une vraie base."""
    with Session(engine) as setup:
        collection = Collection(name="Concurrence", slug="test-concurrence")
        family = OlfactoryFamily(name="Concurrence", slug="test-concurrence")
        setup.add_all([collection, family])
        setup.flush()
        product = Product(
            name="Dernier flacon",
            slug="test-dernier-flacon",
            collection_id=collection.id,
            family_id=family.id,
            gender=Gender.MIXTE,
        )
        setup.add(product)
        setup.flush()
        variant = ProductVariant(
            product_id=product.id, volume_ml=50, sku="TEST-DERNIER", price=1000, stock_physical=1
        )
        setup.add(variant)
        setup.commit()
        ids = (collection.id, family.id, product.id, variant.id)

    buyers = 12
    start = threading.Barrier(buyers)
    results: list[str] = []

    def buy() -> None:
        with Session(engine) as db:
            start.wait()
            try:
                service.reserve(db, {ids[3]: 1}, order_id=None)
                db.commit()
                results.append("ok")
            except AppError as exc:
                results.append(exc.code)

    try:
        threads = [threading.Thread(target=buy) for _ in range(buyers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert sorted(results) == ["INSUFFICIENT_STOCK"] * (buyers - 1) + ["ok"]
        with Session(engine) as check:
            final = check.get_one(ProductVariant, ids[3])
            assert (final.stock_physical, final.stock_reserved) == (1, 1)
            assert moves(check, ids[3]) == [("RESERVATION", 0, 1)]
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(delete(StockMovement).where(StockMovement.variant_id == ids[3]))
            cleanup.execute(delete(ProductVariant).where(ProductVariant.id == ids[3]))
            cleanup.execute(delete(Product).where(Product.id == ids[2]))
            cleanup.execute(delete(Collection).where(Collection.id == ids[0]))
            cleanup.execute(delete(OlfactoryFamily).where(OlfactoryFamily.id == ids[1]))
            cleanup.commit()
