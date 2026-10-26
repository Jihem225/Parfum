from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.main import app
from app.modules.auth.models import User
from app.modules.delivery.models import Commune
from app.modules.inventory.models import StockMovement
from tests.test_cart import add, perfume, register, shop, vid  # noqa: F401
from tests.test_cash import deliver, moussa, shipped  # noqa: F401
from tests.test_orders import checkout, cocody, stock  # noqa: F401
from tests.test_products import taxons  # noqa: F401
from tests.test_staff import login_owner_with_totp

API = "/api/v1"


@pytest.fixture
def owner(client: TestClient, db: Session) -> Iterator[TestClient]:
    with TestClient(app) as http:
        http.get(f"{API}/health")
        http.headers["X-CSRF-Token"] = http.cookies["csrf"]
        login_owner_with_totp(http, db)
        yield http


def fail(http: TestClient, number: str, reason: str) -> Any:
    return http.post(f"{API}/courier/deliveries/{number}/failed", json={"reason": reason})


def movements(db: Session, variant_id: int) -> list[str]:
    rows = db.scalars(
        select(StockMovement.type)
        .where(StockMovement.variant_id == variant_id)
        .order_by(StockMovement.id)
    )
    return [t.value for t in rows]


# --- Échecs et nouvelles tentatives --------------------------------------------------------------


def test_failed_delivery_retry_then_return(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],  # noqa: F811
    db: Session,
) -> None:
    m_http, m = moussa
    order = shipped(shop, manager, cocody, m, vid(perfume), 2)
    number, url = order["number"], f"{API}/admin/orders/{order['number']}"
    r = fail(m_http, number, "REPORTEE")
    assert r.status_code == 200 and r.json()["status"] == "ECHEC_LIVRAISON"
    assert m_http.get(f"{API}/courier/deliveries").json() == []

    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON", "courier_id": m.id})
    assert r.status_code == 200 and r.json()["delivery_attempts"] == 2
    assert stock(db, vid(perfume)) == (18, 0)  # pas de seconde sortie de stock
    fail(m_http, number, "INJOIGNABLE")
    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON", "courier_id": m.id})
    assert r.json()["error"]["code"] == "NO_RETRY"  # RG-44 : 2 tentatives maximum
    detail = manager.get(url).json()
    reasons = [e["failure_reason"] for e in detail["events"] if e["failure_reason"]]
    assert reasons == ["REPORTEE", "INJOIGNABLE"]

    v = vid(perfume)
    bad = manager.post(f"{url}/return", json={"items": [{"variant_id": v, "restocked": 1}]})
    assert bad.json()["error"]["code"] == "INVALID_RETURN"  # 2 flacons à contrôler
    r = manager.post(
        f"{url}/return",
        json={"items": [{"variant_id": v, "restocked": 1, "lost": 1}], "note": "Flacon fêlé"},
    )
    assert r.status_code == 200
    assert (r.json()["status"], r.json()["payment_status"]) == ("RETOURNEE", "ANNULE")
    assert stock(db, v) == (19, 0)
    assert movements(db, v)[-2:] == ["RETOUR", "PERTE"]


def test_refused_parcel_goes_straight_back(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],  # noqa: F811
) -> None:
    m_http, m = moussa
    number = shipped(shop, manager, cocody, m, vid(perfume))["number"]
    fail(m_http, number, "REFUS")
    r = manager.post(
        f"{API}/admin/orders/{number}/transition", json={"to": "EN_LIVRAISON", "courier_id": m.id}
    )
    assert r.json()["error"]["code"] == "NO_RETRY"
    assert fail(m_http, number, "REFUS").status_code == 409  # déjà en échec


# --- Retour d'une commande livrée ----------------------------------------------------------------


def test_delivered_order_return_and_refund(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    owner: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],  # noqa: F811
    db: Session,
) -> None:
    m_http, m = moussa
    number = shipped(shop, manager, cocody, m, vid(perfume))["number"]
    deliver(m_http, number, 39500)
    url = f"{API}/admin/orders/{number}/return"
    body = {"items": [{"variant_id": vid(perfume), "restocked": 1}], "note": "Client insatisfait"}
    assert manager.post(url, json=body).status_code == 403  # Propriétaire seulement
    assert owner.post(url, json=body).json()["error"]["code"] == "CASH_NOT_REMITTED"
    manager.post(
        f"{API}/admin/remittances",
        json={"courier_id": m.id, "expected_amount": 39500, "received_amount": 39500},
    )
    assert owner.post(url, json=body).json()["error"]["code"] == "REFUND_REQUIRED"
    assert owner.post(url, json={**body, "refund_amount": 40000}).status_code == 422
    r = owner.post(url, json={**body, "refund_amount": 38000})
    assert r.status_code == 200
    detail = r.json()
    assert (detail["status"], detail["payment_status"]) == ("RETOURNEE", "REMBOURSE")
    assert detail["events"][-1]["note"] == "Client insatisfait — remboursé : 38 000 FCFA"
    assert stock(db, vid(perfume)) == (20, 0)


# --- Profil et adresses --------------------------------------------------------------------------


def test_profile(shop: TestClient) -> None:  # noqa: F811
    register(shop)
    r = shop.patch(
        f"{API}/me/profile", json={"full_name": "Aya Kouassi", "phone": "+225 01 02 03 04 05"}
    )
    assert (r.json()["full_name"], r.json()["phone"]) == ("Aya Kouassi", "0102030405")
    assert shop.patch(f"{API}/me/profile", json={"phone": "123"}).status_code == 422
    assert shop.get(f"{API}/me/profile").json()["email"] == "aya@exemple.com"


def address(commune: Commune, **fields: Any) -> dict[str, Any]:
    return {
        "recipient_name": "Aya Kouassi",
        "phone": "0708123456",
        "commune_id": commune.id,
        "address_line": "Riviera 3, villa 12",
        **fields,
    }


def test_address_book(shop: TestClient, cocody: Commune, db: Session) -> None:  # noqa: F811
    register(shop)
    first = shop.post(f"{API}/me/addresses", json=address(cocody, label="Maison")).json()
    assert first[0]["is_default"] is True  # la première sert par défaut
    book = shop.post(
        f"{API}/me/addresses", json=address(cocody, label="Bureau", is_default=True)
    ).json()
    assert [(a["label"], a["is_default"]) for a in book] == [("Bureau", True), ("Maison", False)]
    home = book[1]["id"]
    book = shop.patch(
        f"{API}/me/addresses/{home}", json={"is_default": True, "landmark": "Portail vert"}
    ).json()
    assert [(a["label"], a["is_default"], a["landmark"]) for a in book][0] == (
        "Maison",
        True,
        "Portail vert",
    )

    book = shop.delete(f"{API}/me/addresses/{home}").json()
    assert [(a["label"], a["is_default"]) for a in book] == [("Bureau", True)]

    closed = Commune(name="Anyama", delivery_fee=3000, delay_label="72 h", is_active=False)
    db.add(closed)
    db.flush()
    r = shop.post(f"{API}/me/addresses", json=address(closed))
    assert r.json()["error"]["code"] == "COMMUNE_NOT_SERVED"

    with TestClient(app) as other:
        other.get(f"{API}/health")
        other.headers["X-CSRF-Token"] = other.cookies["csrf"]
        register(other, "kofi@exemple.com")
        assert other.get(f"{API}/me/addresses").json() == []
        assert other.delete(f"{API}/me/addresses/{book[0]['id']}").status_code == 404


def test_address_limit(shop: TestClient, cocody: Commune) -> None:  # noqa: F811
    register(shop)
    for _ in range(10):
        assert shop.post(f"{API}/me/addresses", json=address(cocody)).status_code == 201
    r = shop.post(f"{API}/me/addresses", json=address(cocody))
    assert r.json()["error"]["code"] == "TOO_MANY_ADDRESSES"
