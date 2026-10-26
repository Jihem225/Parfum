import threading
import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import engine
from app.core.errors import AppError
from app.core.models import AuditLog
from app.main import app
from app.modules.auth.models import UserRole
from app.modules.cart import service as cart_service
from app.modules.cart.models import Cart, CartItem
from app.modules.catalog.models import (
    Collection,
    Gender,
    OlfactoryFamily,
    Product,
    ProductStatus,
    ProductVariant,
)
from app.modules.delivery import courier
from app.modules.delivery.models import Commune
from app.modules.inventory.models import StockMovement
from app.modules.orders import router as orders_router
from app.modules.orders import service
from app.modules.orders.models import Order, OrderEvent, OrderItem
from app.modules.orders.schemas import CheckoutIn
from app.modules.payments.models import Payment
from tests.test_cart import add, perfume, register, shop, vid  # noqa: F401
from tests.test_products import ADMIN, set_stock, taxons  # noqa: F401
from tests.test_staff import login_owner_with_totp, make_staff

API = "/api/v1"


@pytest.fixture
def cocody(db: Session) -> Commune:
    commune = Commune(name="Cocody", delivery_fee=1500, delay_label="24 h")
    db.add(commune)
    db.flush()
    return commune


@pytest.fixture
def mails(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, str]]:
    sent: list[tuple[str, str, str]] = []
    for module in (orders_router, courier):
        monkeypatch.setattr(module, "send_email", lambda *a: sent.append(a))
    monkeypatch.setattr(settings, "shop_notification_email", "shop@ex.com")
    return sent


def checkout(shop: TestClient, commune: Commune, **overrides: Any) -> Any:  # noqa: F811
    cart = shop.get(f"{API}/cart").json()
    body = {
        "customer_name": "Aya Kouassi",
        "phone": "+225 07 08 12 34 56",
        "email": "aya@exemple.com",
        "commune_id": commune.id,
        "address_line": "Riviera 3, villa 12",
        "landmark": "Près de la pharmacie",
        "accept_terms": True,
        "expected_total": cart["subtotal"] + commune.delivery_fee,
        "idempotency_key": uuid.uuid4().hex,
        **overrides,
    }
    return shop.post(f"{API}/orders", json=body)


def stock(db: Session, variant_id: int) -> tuple[int, int]:
    v = db.get_one(ProductVariant, variant_id)
    db.refresh(v)
    return v.stock_physical, v.stock_reserved


# --- Communes ------------------------------------------------------------------------------------


def test_owner_manages_served_communes(client: TestClient, db: Session) -> None:
    login_owner_with_totp(client, db)
    r = client.post(
        f"{API}/admin/communes",
        json={"name": "Yopougon", "delivery_fee": 2000, "delay_label": "48 h"},
    )
    assert r.status_code == 201
    commune = r.json()
    client.post(
        f"{API}/admin/communes",
        json={"name": "Abobo", "delivery_fee": 2500, "delay_label": "48 h", "position": 9},
    )
    assert (
        client.post(
            f"{API}/admin/communes",
            json={"name": "Yopougon", "delivery_fee": 1, "delay_label": "x"},
        ).status_code
        == 409
    )
    r = client.patch(f"{API}/admin/communes/{commune['id']}", json={"delivery_fee": 2500})
    assert r.status_code == 200 and r.json()["delivery_fee"] == 2500
    logged = db.scalars(select(AuditLog).where(AuditLog.action == "commune.update")).one()
    assert (logged.before or {})["delivery_fee"] == 2000
    client.patch(f"{API}/admin/communes/{commune['id']}", json={"is_active": False})
    assert [c["name"] for c in client.get(f"{API}/delivery/communes").json()] == ["Abobo"]


def test_managers_cannot_change_delivery_settings(manager: TestClient) -> None:
    r = manager.post(
        f"{API}/admin/communes", json={"name": "Bingerville", "delivery_fee": 1, "delay_label": "x"}
    )
    assert r.status_code == 403


# --- Commande en invité --------------------------------------------------------------------------


def test_guest_order(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
    mails: list[tuple[str, str, str]],
) -> None:
    add(shop, vid(perfume), 2)
    add(shop, vid(perfume, 1), 1)
    r = checkout(shop, cocody)
    assert r.status_code == 201, r.json()
    order = r.json()
    assert order["number"].startswith("PP-")
    assert order["status"] == "EN_ATTENTE_CONFIRMATION"
    assert order["phone"] == "0708123456"
    assert (order["subtotal"], order["delivery_fee"], order["total"]) == (141000, 1500, 142500)
    assert [(i["sku"], i["quantity"], i["line_total"]) for i in order["items"]] == [
        ("AMBRE-NUIT-50", 2, 76000),
        ("AMBRE-NUIT-100", 1, 65000),
    ]
    assert order["can_cancel"] is False  # un invité annule en appelant la boutique
    assert stock(db, vid(perfume)) == (20, 2)
    saved = db.scalars(select(Order).where(Order.number == order["number"])).one()
    payment = db.scalars(select(Payment).where(Payment.order_id == saved.id)).one()
    assert (payment.status.value, payment.amount) == ("A_ENCAISSER", 142500)
    assert shop.get(f"{API}/cart").json()["items"] == []
    assert [m[0] for m in mails] == ["aya@exemple.com", "shop@ex.com"]
    assert "142 500 FCFA" in mails[1][2] and "2 × Ambre Nuit 50 ml" in mails[1][2]


def test_order_is_a_frozen_copy(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
) -> None:
    add(shop, vid(perfume))
    number = checkout(shop, cocody).json()["number"]
    manager.patch(f"{ADMIN}/variants/{vid(perfume)}", json={"price": 99000})
    cocody.delivery_fee = 5000
    db.flush()
    order = shop.post(f"{API}/orders/track", json={"number": number, "phone": "0708123456"}).json()
    assert (order["items"][0]["unit_price"], order["delivery_fee"]) == (38000, 1500)


def test_double_submit_creates_one_order(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
) -> None:
    add(shop, vid(perfume), 2)
    key = uuid.uuid4().hex
    first = checkout(shop, cocody, idempotency_key=key, expected_total=77500)
    second = checkout(shop, cocody, idempotency_key=key, expected_total=77500)
    assert first.json()["number"] == second.json()["number"]
    assert db.scalar(select(func.count()).select_from(Order)) == 1
    assert stock(db, vid(perfume)) == (20, 2)


@pytest.mark.parametrize(
    ("overrides", "status", "code"),
    [
        ({"accept_terms": False}, 422, "TERMS_REQUIRED"),
        ({"phone": "12345"}, 422, "VALIDATION_ERROR"),
        ({"expected_total": 1}, 409, "PRICE_CHANGED"),
        ({"commune_id": 999_999}, 422, "COMMUNE_NOT_SERVED"),
    ],
)
def test_checkout_is_refused(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
    overrides: dict[str, Any],
    status: int,
    code: str,
) -> None:
    add(shop, vid(perfume))
    r = checkout(shop, cocody, **overrides)
    assert (r.status_code, r.json()["error"]["code"]) == (status, code)
    assert stock(db, vid(perfume)) == (20, 0)
    assert len(shop.get(f"{API}/cart").json()["items"]) == 1  # le panier reste intact


def test_validation_messages_are_in_french(
    shop: TestClient,  # noqa: F811
    cocody: Commune,
) -> None:
    r = checkout(shop, cocody, email="pas-un-email", expected_total=0, accept_terms="peut-être")
    messages = {d["field"]: d["message"] for d in r.json()["error"]["details"]}
    assert messages == {
        "email": "Adresse e-mail invalide.",
        "expected_total": "Doit être supérieur à 0.",
        "accept_terms": "Oui ou non attendu.",
    }


def test_price_change_is_reported_with_the_new_total(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
) -> None:
    add(shop, vid(perfume))
    displayed = 38000 + 1500
    manager.patch(f"{ADMIN}/variants/{vid(perfume)}", json={"price": 40000})
    r = checkout(shop, cocody, expected_total=displayed)
    assert r.status_code == 409
    assert r.json()["error"]["details"] == {"subtotal": 40000, "delivery_fee": 1500, "total": 41500}


def test_inactive_commune_empty_cart_and_stale_cart(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
) -> None:
    assert checkout(shop, cocody, expected_total=1).json()["error"]["code"] == "CART_EMPTY"
    add(shop, vid(perfume), 3)
    set_stock(db, perfume, physical=2)
    r = checkout(shop, cocody)
    assert r.json()["error"]["code"] == "CART_CHANGED"
    assert r.json()["error"]["details"]["items"][0]["max_quantity"] == 2
    set_stock(db, perfume, physical=20)
    cocody.is_active = False
    db.flush()
    assert checkout(shop, cocody).json()["error"]["code"] == "COMMUNE_NOT_SERVED"


def test_cash_on_delivery_ceiling_includes_delivery_fee(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    db: Session,
) -> None:
    far = Commune(name="Bingerville", delivery_fee=40000, delay_label="72 h")
    db.add(far)
    db.flush()
    add(shop, vid(perfume, 1), 4)  # 260 000 + 40 000 = 300 000 : accepté
    assert checkout(shop, far).status_code == 201
    add(shop, vid(perfume), 1)
    add(shop, vid(perfume, 1), 4)  # 298 000 + 40 000 > 300 000
    assert checkout(shop, far).json()["error"]["code"] == "COD_LIMIT"


def test_guest_tracking(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
) -> None:
    add(shop, vid(perfume))
    number = checkout(shop, cocody).json()["number"]
    r = shop.post(f"{API}/orders/track", json={"number": number.lower(), "phone": "07 08 12 34 56"})
    assert r.status_code == 200
    assert [h["status"] for h in r.json()["history"]] == ["EN_ATTENTE_CONFIRMATION"]
    wrong_phone = shop.post(f"{API}/orders/track", json={"number": number, "phone": "0101010101"})
    wrong_number = shop.post(f"{API}/orders/track", json={"number": "PP-1", "phone": "0708123456"})
    assert wrong_phone.status_code == wrong_number.status_code == 404
    assert wrong_phone.json() == wrong_number.json()  # ne dit pas lequel est faux


# --- Espace client -------------------------------------------------------------------------------


def test_customer_orders_and_cancels(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
    mails: list[tuple[str, str, str]],
) -> None:
    register(shop)
    add(shop, vid(perfume), 2)
    created = checkout(shop, cocody).json()
    assert created["can_cancel"] is True
    number = created["number"]
    assert [o["number"] for o in shop.get(f"{API}/me/orders").json()] == [number]
    assert shop.get(f"{API}/me/orders/{number}").json()["total"] == 77500
    r = shop.post(f"{API}/me/orders/{number}/cancel", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "ANNULEE" and r.json()["can_cancel"] is False
    assert stock(db, vid(perfume)) == (20, 0)  # réservation libérée
    saved = db.scalars(select(Order).where(Order.number == number)).one()
    assert saved.cancel_reason == "Annulée par le client"
    assert db.scalars(select(Payment.status).where(Payment.order_id == saved.id)).one() == "ANNULE"
    assert mails[-1][1] == f"Commande {number} annulée"
    assert shop.post(f"{API}/me/orders/{number}/cancel", json={}).status_code == 409

    with TestClient(app) as other:
        other.get(f"{API}/health")
        other.headers["X-CSRF-Token"] = other.cookies["csrf"]
        register(other, "kofi@exemple.com")
        assert other.get(f"{API}/me/orders/{number}").status_code == 404
        assert other.get(f"{API}/me/orders").json() == []


# --- Back-office ---------------------------------------------------------------------------------


def test_order_processing(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
    mails: list[tuple[str, str, str]],
) -> None:
    add(shop, vid(perfume), 2)
    number = checkout(shop, cocody).json()["number"]
    url = f"{API}/admin/orders/{number}"
    for _ in range(3):
        detail = manager.post(f"{url}/calls", json={"result": "PAS_DE_REPONSE"}).json()
    assert detail["unanswered_calls"] == 3 and detail["should_cancel"] is True
    detail = manager.post(
        f"{url}/calls", json={"result": "CONFIRMEE", "note": "OK pour demain"}
    ).json()
    assert detail["status"] == "CONFIRMEE" and detail["should_cancel"] is False
    assert detail["events"][-2]["note"] == "OK pour demain"
    assert detail["events"][-1]["author"] == "Awa Koné"
    assert mails[-1][1] == f"Commande {number} confirmée"

    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON"})
    assert r.json()["error"]["code"] == "INVALID_TRANSITION"  # pas avant la préparation
    assert manager.post(f"{url}/transition", json={"to": "EN_PREPARATION"}).status_code == 200
    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON"})
    assert r.json()["error"]["code"] == "COURIER_REQUIRED"
    not_a_courier = make_staff(db, "gestion2@exemple.com", UserRole.MANAGER)
    r = manager.post(
        f"{url}/transition", json={"to": "EN_LIVRAISON", "courier_id": not_a_courier.id}
    )
    assert r.status_code == 422
    courier = make_staff(db, "livreur@exemple.com", UserRole.COURIER)
    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON", "courier_id": courier.id})
    assert r.status_code == 200
    detail = r.json()
    assert (detail["courier"]["id"], detail["delivery_attempts"]) == (courier.id, 1)
    assert stock(db, vid(perfume)) == (18, 0)  # sortie vente
    assert mails[-1][1] == f"Commande {number} en route"
    r = manager.post(f"{url}/transition", json={"to": "ANNULEE", "note": "Trop tard"})
    assert r.json()["error"]["code"] == "INVALID_TRANSITION"  # RG-32
    assert [(h["status"]) for h in detail["history"]] == [
        "EN_ATTENTE_CONFIRMATION",
        "CONFIRMEE",
        "EN_PREPARATION",
        "EN_LIVRAISON",
    ]
    audits = db.scalars(select(AuditLog.after).where(AuditLog.action == "order.status")).all()
    assert [a["status"] for a in audits if a] == ["CONFIRMEE", "EN_PREPARATION", "EN_LIVRAISON"]


def test_staff_cancellation_needs_a_reason(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
    db: Session,
) -> None:
    add(shop, vid(perfume), 2)
    number = checkout(shop, cocody).json()["number"]
    url = f"{API}/admin/orders/{number}/transition"
    assert manager.post(url, json={"to": "ANNULEE"}).json()["error"]["code"] == "REASON_REQUIRED"
    r = manager.post(url, json={"to": "ANNULEE", "note": "Injoignable après 3 appels"})
    assert r.json()["cancel_reason"] == "Injoignable après 3 appels"
    assert r.json()["payment_status"] == "ANNULE"
    assert stock(db, vid(perfume)) == (20, 0)
    assert manager.post(url, json={"to": "LIVREE"}).status_code == 422  # étape 6.9


def test_order_list_filters(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,
) -> None:
    add(shop, vid(perfume))
    first = checkout(shop, cocody).json()["number"]
    add(shop, vid(perfume))
    second = checkout(shop, cocody, customer_name="Kofi Yao", phone="0102030405").json()["number"]
    manager.post(f"{API}/admin/orders/{first}/calls", json={"result": "CONFIRMEE"})

    def numbers(**params: Any) -> list[str]:
        return [
            o["number"] for o in manager.get(f"{API}/admin/orders", params=params).json()["items"]
        ]

    assert numbers() == [second, first]
    assert numbers(status="CONFIRMEE") == [first]
    assert numbers(q="kofi") == [second]
    assert numbers(q="02 03 04") == [second]
    assert numbers(q=first) == [first]
    assert numbers(commune="Cocody") == [second, first]
    assert numbers(date_from="2000-01-01", date_to="2000-01-02") == []


def test_customers_and_couriers_cannot_process_orders(
    shop: TestClient,  # noqa: F811
    client: TestClient,
    db: Session,
) -> None:
    register(shop)
    assert shop.get(f"{API}/admin/orders").status_code == 403
    make_staff(db, "livreur@exemple.com", UserRole.COURIER)
    r = client.post(
        f"{API}/auth/login",
        json={"email": "livreur@exemple.com", "password": "motdepasse-du-proprio"},
    )
    assert r.status_code == 200
    assert client.get(f"{API}/admin/orders").status_code == 403


# --- Concurrence réelle --------------------------------------------------------------------------


@pytest.fixture
def last_bottle() -> Iterator[dict[str, Any]]:
    """Données réellement validées en base (visibles des autres connexions), nettoyées ensuite."""
    with Session(engine) as setup:
        collection = Collection(name="Concurrence", slug="test-concurrence")
        family = OlfactoryFamily(name="Concurrence", slug="test-concurrence")
        commune = Commune(name="Test-Concurrence", delivery_fee=1000, delay_label="24 h")
        setup.add_all([collection, family, commune])
        setup.flush()
        product = Product(
            name="Dernier flacon",
            slug="test-dernier-flacon",
            collection_id=collection.id,
            family_id=family.id,
            gender=Gender.MIXTE,
            status=ProductStatus.PUBLISHED,
        )
        setup.add(product)
        setup.flush()
        variant = ProductVariant(
            product_id=product.id, volume_ml=50, sku="TEST-DERNIER", price=1000, stock_physical=1
        )
        setup.add(variant)
        setup.flush()
        tokens, cart_ids = [], []
        for _ in range(8):
            cart, raw = cart_service.get_or_create(setup, None, None)
            setup.add(CartItem(cart_id=cart.id, variant_id=variant.id, quantity=1))
            tokens.append(raw)
            cart_ids.append(cart.id)
        setup.commit()
        ids = {
            "collection": collection.id,
            "family": family.id,
            "commune": commune.id,
            "product": product.id,
            "variant": variant.id,
        }
    try:
        yield {**ids, "tokens": tokens}
    finally:
        with Session(engine) as cleanup:
            orders = select(Order.id).join(OrderItem).where(OrderItem.variant_id == ids["variant"])
            order_ids = list(cleanup.scalars(orders))
            cleanup.execute(delete(StockMovement).where(StockMovement.variant_id == ids["variant"]))
            for model in (OrderEvent, Payment, OrderItem):
                cleanup.execute(delete(model).where(model.order_id.in_(order_ids)))
            cleanup.execute(delete(Order).where(Order.id.in_(order_ids)))
            cleanup.execute(delete(Cart).where(Cart.id.in_(cart_ids)))
            cleanup.execute(delete(ProductVariant).where(ProductVariant.id == ids["variant"]))
            cleanup.execute(delete(Product).where(Product.id == ids["product"]))
            cleanup.execute(delete(Collection).where(Collection.id == ids["collection"]))
            cleanup.execute(delete(OlfactoryFamily).where(OlfactoryFamily.id == ids["family"]))
            cleanup.execute(delete(Commune).where(Commune.id == ids["commune"]))
            cleanup.commit()


def test_simultaneous_checkouts_on_the_last_bottle(last_bottle: dict[str, Any]) -> None:
    """US-06 : huit clients valident en même temps la dernière unité, un seul réussit."""
    start = threading.Barrier(len(last_bottle["tokens"]))
    results: list[str] = []

    def buy(token: str) -> None:
        data = CheckoutIn(
            customer_name="Client Test",
            phone="0708123456",
            commune_id=last_bottle["commune"],
            address_line="Adresse de test",
            accept_terms=True,
            expected_total=2000,
            idempotency_key=uuid.uuid4().hex,
        )
        with Session(engine) as db:
            start.wait()
            try:
                cart = cart_service.find(db, None, token)
                service.checkout(db, data, cart=cart, user=None)
                db.commit()
                results.append("ok")
            except AppError as exc:
                db.rollback()
                results.append(exc.code)

    threads = [threading.Thread(target=buy, args=(t,)) for t in last_bottle["tokens"]]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # Les perdants voient soit le manque à la réservation, soit un panier déjà signalé.
    assert results.count("ok") == 1
    assert set(results) - {"ok"} <= {"INSUFFICIENT_STOCK", "CART_CHANGED"}
    with Session(engine) as check:
        variant = check.get_one(ProductVariant, last_bottle["variant"])
        assert (variant.stock_physical, variant.stock_reserved) == (1, 1)
        orders = check.scalar(
            select(func.count())
            .select_from(OrderItem)
            .where(OrderItem.variant_id == last_bottle["variant"])
        )
        assert orders == 1
