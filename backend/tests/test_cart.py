from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import security
from app.main import app
from app.modules.cart.models import Cart
from tests.test_products import ADMIN, make_product, set_stock, taxons  # noqa: F401

CART = "/api/v1/cart"


@pytest.fixture
def shop(client: TestClient) -> Iterator[TestClient]:
    """Navigateur d'un visiteur, distinct de celui du Gestionnaire."""
    with TestClient(app) as http:
        http.get("/api/v1/health")
        http.headers["X-CSRF-Token"] = http.cookies["csrf"]
        yield http


@pytest.fixture
def perfume(manager: TestClient, taxons: dict[str, int], db: Session) -> dict[str, Any]:  # noqa: F811
    product = make_product(manager, taxons, "Ambre Nuit", variants=((50, 38000), (100, 65000)))
    set_stock(db, product, physical=20)
    return product


def vid(product: dict[str, Any], index: int = 0) -> int:
    return int(product["variants"][index]["id"])


def add(shop: TestClient, variant_id: int, quantity: int = 1) -> Any:
    return shop.post(f"{CART}/items", json={"variant_id": variant_id, "quantity": quantity})


def register(shop: TestClient, email: str = "aya@exemple.com") -> None:
    r = shop.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "motdepasse-solide",
            "full_name": "Aya K.",
            "phone": "0708123456",
        },
    )
    assert r.status_code == 201


def test_guest_cart_lives_in_an_httponly_cookie(
    shop: TestClient, perfume: dict[str, Any], db: Session
) -> None:
    assert shop.get(CART).json()["items"] == []
    r = add(shop, vid(perfume), 2)
    assert r.status_code == 201
    assert "httponly" in r.headers["set-cookie"].lower()
    cart = r.json()
    assert cart["subtotal"] == 76000 and cart["item_count"] == 2 and cart["can_checkout"]
    line = cart["items"][0]
    assert (line["product_name"], line["volume_ml"], line["unit_price"]) == (
        "Ambre Nuit",
        50,
        38000,
    )
    assert line["image"]["url"].endswith(".webp")
    # Seule l'empreinte du jeton est en base.
    raw = shop.cookies["cart"]
    assert db.scalar(select(Cart).where(Cart.token_hash == security.sha256(raw))) is not None
    assert shop.get(CART).json()["subtotal"] == 76000  # retrouvé au retour du visiteur


def test_other_visitors_do_not_see_the_cart(
    shop: TestClient, perfume: dict[str, Any], client: TestClient
) -> None:
    add(shop, vid(perfume))
    with TestClient(app) as stranger:
        assert stranger.get(CART).json()["items"] == []


def test_quantities_add_up_to_five(shop: TestClient, perfume: dict[str, Any]) -> None:
    add(shop, vid(perfume), 3)
    r = add(shop, vid(perfume), 3)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "MAX_QUANTITY"
    assert add(shop, vid(perfume), 2).json()["items"][0]["quantity"] == 5
    assert shop.patch(f"{CART}/items/{vid(perfume)}", json={"quantity": 6}).status_code == 422
    r = shop.patch(f"{CART}/items/{vid(perfume)}", json={"quantity": 1})
    assert r.status_code == 200 and r.json()["items"][0]["quantity"] == 1
    r = shop.delete(f"{CART}/items/{vid(perfume)}")
    assert r.status_code == 200 and r.json()["items"] == []


def test_cannot_exceed_available_stock(
    shop: TestClient, perfume: dict[str, Any], db: Session
) -> None:
    set_stock(db, perfume, physical=3, reserved=1)
    r = add(shop, vid(perfume), 3)
    assert r.status_code == 409
    assert r.json()["error"] == {
        "code": "INSUFFICIENT_STOCK",
        "message": "Quantité indisponible.",
        "details": {"max_quantity": 2},
    }
    set_stock(db, perfume, physical=1, reserved=1)
    assert (
        add(shop, vid(perfume)).json()["error"]["message"] == "Ce parfum est en rupture de stock."
    )


def test_unpublished_or_inactive_perfumes_cannot_be_added(
    shop: TestClient, manager: TestClient, perfume: dict[str, Any]
) -> None:
    manager.patch(f"{ADMIN}/variants/{vid(perfume, 1)}", json={"is_active": False})
    assert add(shop, vid(perfume, 1)).json()["error"]["code"] == "UNAVAILABLE"
    manager.post(f"{ADMIN}/products/{perfume['id']}/unpublish")
    assert add(shop, vid(perfume)).json()["error"]["code"] == "UNAVAILABLE"
    assert add(shop, 999_999).json()["error"]["code"] == "UNAVAILABLE"


def test_cart_reflects_catalog_changes(
    shop: TestClient, manager: TestClient, perfume: dict[str, Any], db: Session
) -> None:
    add(shop, vid(perfume), 2)
    add(shop, vid(perfume, 1), 1)
    manager.patch(f"{ADMIN}/variants/{vid(perfume)}", json={"price": 40000})
    cart = shop.get(CART).json()
    assert cart["items"][0]["unit_price"] == 40000  # le prix n'est jamais figé dans le panier
    assert cart["subtotal"] == 2 * 40000 + 65000

    set_stock(db, perfume, physical=1)
    manager.patch(f"{ADMIN}/variants/{vid(perfume, 1)}", json={"is_active": False})
    cart = shop.get(CART).json()
    first, second = cart["items"]
    assert (first["issue"], first["max_quantity"]) == ("INSUFFICIENT_STOCK", 1)
    assert (second["issue"], second["max_quantity"]) == ("UNAVAILABLE", 0)
    assert cart["subtotal"] == 80000 and not cart["can_checkout"]


def test_cash_on_delivery_ceiling(shop: TestClient, perfume: dict[str, Any]) -> None:
    add(shop, vid(perfume, 1), 4)  # 260 000 FCFA
    assert shop.get(CART).json()["can_checkout"]
    cart = add(shop, vid(perfume, 1), 1).json()  # 325 000 FCFA > 300 000
    assert cart["exceeds_cod_limit"] and not cart["can_checkout"]


def test_guest_cart_joins_the_account_at_login(
    shop: TestClient, perfume: dict[str, Any], db: Session
) -> None:
    register(shop)
    add(shop, vid(perfume), 4)  # panier du compte
    shop.post("/api/v1/auth/logout")
    assert shop.get(CART).json()["items"] == []
    add(shop, vid(perfume), 3)  # panier visiteur sur le même appareil
    add(shop, vid(perfume, 1), 1)
    r = shop.post(
        "/api/v1/auth/login", json={"email": "aya@exemple.com", "password": "motdepasse-solide"}
    )
    assert r.status_code == 200
    assert "cart" not in shop.cookies
    cart = shop.get(CART).json()
    assert [(i["volume_ml"], i["quantity"]) for i in cart["items"]] == [(50, 5), (100, 1)]
    assert db.scalar(select(func.count()).select_from(Cart)) == 1  # panier visiteur supprimé


def test_guest_cart_is_kept_when_signing_up(shop: TestClient, perfume: dict[str, Any]) -> None:
    add(shop, vid(perfume), 2)
    register(shop, "kofi@exemple.com")
    assert shop.get(CART).json()["items"][0]["quantity"] == 2
