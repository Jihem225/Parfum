import json
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.main import app
from app.modules.auth.models import User
from app.modules.delivery.models import Commune
from app.modules.orders import service
from app.modules.orders.models import EventKind, Order, OrderEvent
from app.modules.payments.models import Payment, PaymentStatus
from app.modules.payments.providers import sign
from tests.test_cart import add, perfume, register, shop, vid  # noqa: F401
from tests.test_cash import deliver, moussa  # noqa: F401
from tests.test_orders import checkout, cocody, mails, stock  # noqa: F401
from tests.test_products import taxons  # noqa: F401
from tests.test_staff import login_owner_with_totp

API = "/api/v1"
MOBILE = {"payment_method": "MOBILE_MONEY"}


@pytest.fixture
def mobile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "payment_provider", "simulation")
    monkeypatch.setattr(settings, "payment_webhook_secret", "secret-de-test")


def payment_of(db: Session, number: str) -> Payment:
    order = db.scalars(select(Order).where(Order.number == number)).one()
    db.refresh(order)
    paid = service.payment(db, order)
    db.refresh(paid)
    return paid


def simulate(http: TestClient, order: dict[str, Any], paid: bool = True) -> Any:
    body = {"token": order["payment_token"], "paid": paid}
    return http.post(f"{API}/payments/simulation/{order['number']}", json=body)


def test_mobile_money_is_refused_while_disabled(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
) -> None:
    add(shop, vid(perfume))
    assert shop.get(f"{API}/cart").json()["mobile_money"] is False
    r = checkout(shop, cocody, **MOBILE)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "PAYMENT_UNAVAILABLE"


def test_paid_order_is_confirmed_without_a_call(
    mobile: None,
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
    mails: list[tuple[str, str, str]],  # noqa: F811
) -> None:
    add(shop, vid(perfume))
    order = checkout(shop, cocody, **MOBILE).json()
    assert (order["status"], order["payment_method"]) == ("EN_ATTENTE_PAIEMENT", "MOBILE_MONEY")
    assert stock(db, vid(perfume)) == (20, 1)  # réservé dès la commande
    assert mails == []  # rien tant que ce n'est pas payé
    url = f"{API}/orders/{order['number']}/payment"
    assert shop.post(url, json={"token": "x" * 32}).status_code == 404
    link = shop.post(url, json={"token": order["payment_token"]}).json()["url"]
    assert "/paiement/simulation?numero=" in link

    # Avis falsifié, envoyé sans cookie ni jeton CSRF : la signature seule décide.
    forged = json.dumps(
        {"id": "x", "order_number": order["number"], "amount": order["total"], "status": "paid"}
    ).encode()
    with TestClient(app) as provider:
        r = provider.post(
            f"{API}/payments/notifications", content=forged, headers={"x-signature": "0" * 64}
        )
        assert r.status_code == 401

        assert simulate(shop, order, paid=False).json()["payment_status"] == "A_PAYER"
        state = simulate(shop, order).json()
        assert state == {"order_status": "CONFIRMEE", "payment_status": "PAYE"}
        replay = provider.post(
            f"{API}/payments/notifications", content=forged, headers={"x-signature": sign(forged)}
        )
        assert replay.status_code == 200  # rejoué : accepté, sans effet

    paid = payment_of(db, order["number"])
    assert paid.status == PaymentStatus.PAYE and (paid.provider_ref or "").startswith("sim-")
    assert [subject for _, subject, _ in mails] == [
        f"Commande {order['number']} confirmée",
        f"Nouvelle commande {order['number']} — {order['total']:,} FCFA".replace(",", " "),
    ]
    assert "Payée par mobile money" in mails[1][2]
    state = shop.get(url, params={"token": order["payment_token"]}).json()
    assert state["order_status"] == "CONFIRMEE"


def test_amount_mismatch_is_refused(
    mobile: None,
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
) -> None:
    add(shop, vid(perfume))
    order = checkout(shop, cocody, **MOBILE).json()
    body = json.dumps(
        {"id": "x", "order_number": order["number"], "amount": 100, "status": "paid"}
    ).encode()
    r = shop.post(
        f"{API}/payments/notifications", content=body, headers={"x-signature": sign(body)}
    )
    assert r.json()["error"]["code"] == "AMOUNT_MISMATCH"
    assert payment_of(db, order["number"]).status == PaymentStatus.A_PAYER


def test_unpaid_order_expires_then_late_payment_is_refunded(
    mobile: None,
    client: TestClient,
    manager: TestClient,
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
    mails: list[tuple[str, str, str]],  # noqa: F811
) -> None:
    add(shop, vid(perfume), 2)
    order = checkout(shop, cocody, **MOBILE).json()
    url = f"{API}/admin/orders/{order['number']}"
    r = manager.post(f"{url}/transition", json={"to": "CONFIRMEE"})
    assert r.json()["error"]["code"] == "NOT_PAID"

    assert service.expire_unpaid(db, datetime.now(UTC)) == []  # dans le délai
    later = datetime.now(UTC) + service.PAYMENT_DELAY
    assert [o.number for o in service.expire_unpaid(db, later)] == [order["number"]]
    assert stock(db, vid(perfume)) == (20, 0)  # stock libéré
    assert payment_of(db, order["number"]).status == PaymentStatus.ANNULE
    assert (
        shop.post(
            f"{API}/orders/{order['number']}/payment", json={"token": order["payment_token"]}
        ).json()["error"]["code"]
        == "NOT_PAYABLE"
    )

    # Le client paie quand même, après l'annulation : l'argent est enregistré, boutique alertée.
    assert simulate(shop, order).json() == {"order_status": "ANNULEE", "payment_status": "PAYE"}
    assert mails[-1][1].startswith("À rembourser")
    notes = db.scalars(select(OrderEvent.note).where(OrderEvent.kind == EventKind.NOTE)).all()
    assert any("à rembourser" in (n or "") for n in notes)

    assert manager.post(f"{url}/refund", json={"amount": order["total"]}).status_code == 403
    login_owner_with_totp(client, db)
    refunded = client.post(f"{url}/refund", json={"amount": order["total"], "note": "Wave"})
    assert refunded.status_code == 200, refunded.json()
    assert refunded.json()["payment_status"] == "REMBOURSE"
    again = client.post(f"{url}/refund", json={"amount": order["total"]})
    assert again.json()["error"]["code"] == "NOT_REFUNDABLE"


def test_cod_limit_does_not_apply_to_mobile_money(
    mobile: None,
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
) -> None:
    add(shop, vid(perfume, 1), 5)  # 5 × 65 000 = 325 000 FCFA
    cart = shop.get(f"{API}/cart").json()
    assert cart["exceeds_cod_limit"] and cart["can_checkout"]
    assert checkout(shop, cocody).json()["error"]["code"] == "COD_LIMIT"
    preview = shop.post(f"{API}/checkout/preview", json={"commune_id": cocody.id, **MOBILE})
    assert preview.json()["can_order"] is True
    assert checkout(shop, cocody, **MOBILE).status_code == 201


def test_courier_hands_over_a_prepaid_order_without_cash(
    mobile: None,
    manager: TestClient,
    shop: TestClient,  # noqa: F811
    moussa: tuple[TestClient, User],  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
) -> None:
    http, courier = moussa
    add(shop, vid(perfume))
    order = checkout(shop, cocody, **MOBILE).json()
    simulate(shop, order)
    url = f"{API}/admin/orders/{order['number']}"
    manager.post(f"{url}/transition", json={"to": "EN_PREPARATION"})
    r = manager.post(f"{url}/transition", json={"to": "EN_LIVRAISON", "courier_id": courier.id})
    assert r.status_code == 200, r.json()
    [delivery] = http.get(f"{API}/courier/deliveries").json()
    assert delivery["amount_to_collect"] == 0
    assert deliver(http, order["number"], order["total"]).json()["error"]["code"] == (
        "AMOUNT_MISMATCH"
    )
    assert deliver(http, order["number"], 0).status_code == 200
    assert payment_of(db, order["number"]).status == PaymentStatus.PAYE
    assert manager.get(f"{API}/admin/couriers/{courier.id}/pending-cash").json()["amount"] == 0
