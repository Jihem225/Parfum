from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import AuditLog
from app.main import app
from app.modules.auth.models import User, UserRole
from app.modules.delivery.models import Commune
from app.modules.orders.models import Order
from app.modules.payments.models import Payment
from tests.test_cart import add, perfume, register, shop, vid  # noqa: F401
from tests.test_orders import checkout, cocody, mails, stock  # noqa: F401
from tests.test_products import taxons  # noqa: F401
from tests.test_staff import PASSWORD, make_staff

API = "/api/v1"


def browser_for(db: Session, email: str) -> Iterator[tuple[TestClient, User]]:
    courier = make_staff(db, email, UserRole.COURIER)
    with TestClient(app) as http:
        http.get(f"{API}/health")
        http.headers["X-CSRF-Token"] = http.cookies["csrf"]
        assert (
            http.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD}).status_code
            == 200
        )
        yield http, courier


@pytest.fixture
def moussa(client: TestClient, db: Session) -> Iterator[tuple[TestClient, User]]:
    yield from browser_for(db, "moussa@exemple.com")


@pytest.fixture
def ibrahim(client: TestClient, db: Session) -> Iterator[tuple[TestClient, User]]:
    yield from browser_for(db, "ibrahim@exemple.com")


def shipped(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    commune: Commune,
    courier: User,
    variant_id: int,
    quantity: int = 1,
) -> dict[str, Any]:
    """Une commande confirmée, préparée et confiée au livreur."""
    add(shop, variant_id, quantity)
    order: dict[str, Any] = checkout(shop, commune).json()
    url = f"{API}/admin/orders/{order['number']}"
    manager.post(f"{url}/calls", json={"result": "CONFIRMEE"})
    manager.post(f"{url}/transition", json={"to": "EN_PREPARATION"})
    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON", "courier_id": courier.id})
    assert r.status_code == 200, r.json()
    return order


def deliver(http: TestClient, number: str, amount: int) -> Any:
    return http.post(
        f"{API}/courier/deliveries/{number}/delivered", json={"amount_collected": amount}
    )


# --- Récapitulatif de commande ------------------------------------------------------------------


def test_checkout_preview(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
) -> None:
    empty = shop.post(f"{API}/checkout/preview", json={"commune_id": cocody.id}).json()
    assert empty["can_order"] is False
    add(shop, vid(perfume), 2)
    preview = shop.post(f"{API}/checkout/preview", json={"commune_id": cocody.id}).json()
    assert (preview["delivery_fee"], preview["total"], preview["can_order"]) == (1500, 77500, True)
    assert preview["delivery_delay_label"] == "24 h"
    assert checkout(shop, cocody, expected_total=preview["total"]).status_code == 201
    r = shop.post(f"{API}/checkout/preview", json={"commune_id": 999_999})
    assert r.json()["error"]["code"] == "COMMUNE_NOT_SERVED"


# --- Livraison et encaissement -------------------------------------------------------------------


def test_courier_sees_and_closes_only_own_deliveries(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],
    ibrahim: tuple[TestClient, User],
    db: Session,
    mails: list[tuple[str, str, str]],  # noqa: F811
) -> None:
    (m_http, m), (i_http, i) = moussa, ibrahim
    mine = shipped(shop, manager, cocody, m, vid(perfume), 2)
    shipped(shop, manager, cocody, i, vid(perfume))
    deliveries = m_http.get(f"{API}/courier/deliveries").json()
    assert [d["number"] for d in deliveries] == [mine["number"]]
    assert deliveries[0]["amount_to_collect"] == 77500
    assert deliveries[0]["phone"] == "0708123456"
    assert deliver(i_http, mine["number"], 77500).status_code == 404  # pas sa commande

    r = deliver(m_http, mine["number"], 77000)
    assert r.status_code == 422
    assert r.json()["error"]["message"] == "Le montant encaissé doit être exactement 77 500 FCFA."
    r = deliver(m_http, mine["number"], 77500)
    assert r.status_code == 200 and r.json()["status"] == "LIVREE"
    order = db.scalars(select(Order).where(Order.number == mine["number"])).one()
    payment = db.scalars(select(Payment).where(Payment.order_id == order.id)).one()
    assert (payment.status.value, payment.collected_by) == ("ENCAISSE", m.id)
    assert payment.collected_at is not None
    assert stock(db, vid(perfume)) == (17, 0)  # déjà sorti au départ en livraison
    assert mails[-1][1] == f"Commande {mine['number']} livrée"
    assert m_http.get(f"{API}/courier/deliveries").json() == []
    assert deliver(m_http, mine["number"], 77500).status_code == 409


def test_manager_can_close_a_delivery_for_the_courier(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
) -> None:
    courier = make_staff(db, "moussa@exemple.com", UserRole.COURIER)
    order = shipped(shop, manager, cocody, courier, vid(perfume))
    assert deliver(manager, order["number"], 39500).status_code == 200
    detail = manager.get(f"{API}/admin/orders/{order['number']}").json()
    assert detail["payment_status"] == "ENCAISSE"
    assert detail["events"][-1]["note"] == "Encaissé : 39 500 FCFA"

    add(shop, vid(perfume))
    pending = checkout(shop, cocody).json()  # en attente : ne peut pas être « livrée »
    r = deliver(manager, pending["number"], pending["total"])
    assert r.json()["error"]["code"] == "INVALID_TRANSITION"


# --- Remise de caisse ----------------------------------------------------------------------------


def test_cash_remittance(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],
    db: Session,
) -> None:
    m_http, m = moussa
    first = shipped(shop, manager, cocody, m, vid(perfume), 2)  # 77 500
    second = shipped(shop, manager, cocody, m, vid(perfume, 1))  # 66 500
    deliver(m_http, first["number"], 77500)
    assert manager.get(f"{API}/admin/couriers/{m.id}/pending-cash").json()["amount"] == 77500
    deliver(m_http, second["number"], 66500)

    overview = manager.get(f"{API}/admin/couriers/pending-cash").json()
    assert [(c["courier"]["full_name"], c["amount"]) for c in overview] == [("Awa Koné", 144000)]
    assert [o["number"] for o in overview[0]["orders"]] == [first["number"], second["number"]]

    remit = {"courier_id": m.id, "expected_amount": 77500, "received_amount": 143500}
    r = manager.post(f"{API}/admin/remittances", json=remit)
    assert r.json()["error"]["code"] == "EXPECTED_CHANGED"
    assert r.json()["error"]["details"] == {"expected_amount": 144000}
    remit["expected_amount"] = 144000
    r = manager.post(f"{API}/admin/remittances", json=remit)
    assert r.json()["error"]["code"] == "NOTE_REQUIRED"  # un écart doit être expliqué
    r = manager.post(f"{API}/admin/remittances", json={**remit, "note": "Manque 500 F, monnaie"})
    assert r.status_code == 201
    remittance = r.json()
    assert (remittance["expected_amount"], remittance["difference"]) == (144000, -500)
    assert remittance["order_numbers"] == [first["number"], second["number"]]
    assert remittance["received_by"]["full_name"] == "Awa Koné"

    assert manager.get(f"{API}/admin/couriers/pending-cash").json() == []
    statuses = db.scalars(select(Payment.status).where(Payment.remittance_id == remittance["id"]))
    assert {s.value for s in statuses} == {"REMIS"}
    r = manager.post(f"{API}/admin/remittances", json={**remit, "note": "x"})
    assert r.json()["error"]["code"] == "NOTHING_TO_REMIT"
    logged = db.scalars(select(AuditLog).where(AuditLog.action == "cash.remittance")).one()
    assert (logged.after or {})["difference"] == -500
    listed = manager.get(f"{API}/admin/remittances", params={"courier_id": m.id}).json()
    assert listed["total"] == 1 and listed["items"][0]["note"] == "Manque 500 F, monnaie"


def test_exact_remittance_needs_no_note(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],
) -> None:
    m_http, m = moussa
    order = shipped(shop, manager, cocody, m, vid(perfume))
    deliver(m_http, order["number"], 39500)
    r = manager.post(
        f"{API}/admin/remittances",
        json={"courier_id": m.id, "expected_amount": 39500, "received_amount": 39500},
    )
    assert r.status_code == 201 and r.json()["difference"] == 0


def test_access_rules(
    shop: TestClient,  # noqa: F811
    moussa: tuple[TestClient, User],
) -> None:
    m_http, _ = moussa
    assert m_http.get(f"{API}/admin/remittances").status_code == 403
    assert m_http.get(f"{API}/admin/couriers/pending-cash").status_code == 403
    assert shop.get(f"{API}/courier/deliveries").status_code == 401
    register(shop)
    assert shop.get(f"{API}/courier/deliveries").status_code == 403


def test_managers_list_active_couriers(
    manager: TestClient,
    moussa: tuple[TestClient, User],
    db: Session,
) -> None:
    m_http, m = moussa
    gone = make_staff(db, "ancien@exemple.com", UserRole.COURIER)
    gone.is_active = False
    db.flush()
    assert manager.get(f"{API}/admin/couriers").json() == [
        {"id": m.id, "full_name": "Awa Koné", "phone": "0708123456"}
    ]
    assert m_http.get(f"{API}/admin/couriers").status_code == 403
