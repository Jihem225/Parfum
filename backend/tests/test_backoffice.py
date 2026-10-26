from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import AuditLog
from app.modules.auth.models import User
from app.modules.contact import router as contact_router
from app.modules.delivery.models import Commune
from tests.test_cart import add, perfume, register, shop, vid  # noqa: F401
from tests.test_cash import deliver, moussa, shipped  # noqa: F401
from tests.test_delivery import fail, owner  # noqa: F401
from tests.test_orders import checkout, cocody  # noqa: F401
from tests.test_products import set_stock, taxons  # noqa: F401

API = "/api/v1"


# --- Tableau de bord -----------------------------------------------------------------------------


def test_dashboard(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    moussa: tuple[TestClient, User],  # noqa: F811
    db: Session,
) -> None:
    m_http, m = moussa
    sold = shipped(shop, manager, cocody, m, vid(perfume), 2)  # 76 000 + 1 500
    deliver(m_http, sold["number"], 77500)
    refused = shipped(shop, manager, cocody, m, vid(perfume, 1))
    fail(m_http, refused["number"], "REFUS")
    manager.post(
        f"{API}/admin/orders/{refused['number']}/return",
        json={"items": [{"variant_id": vid(perfume, 1), "restocked": 1}]},
    )
    add(shop, vid(perfume))
    checkout(shop, cocody)  # en attente de confirmation
    set_stock(db, {"variants": [{"id": vid(perfume, 1)}]}, physical=3)  # sous le seuil de 5
    shop.post(
        f"{API}/contact",
        json={"name": "Aya", "phone": "0708123456", "message": "Bonjour, avez-vous des coffrets ?"},
    )

    d = manager.get(f"{API}/admin/dashboard").json()
    assert (d["revenue"], d["delivery_fees"], d["delivered_orders"]) == (76000, 1500, 1)
    assert d["average_basket"] == 76000
    assert d["orders_created"] == 3
    assert d["orders_by_status"] == {"LIVREE": 1, "RETOURNEE": 1, "EN_ATTENTE_CONFIRMATION": 1}
    assert d["delivery_success_rate"] == 50.0
    assert d["best_sellers"] == [
        {"product_name": "Ambre Nuit", "volume_ml": 50, "quantity": 2, "revenue": 76000}
    ]
    assert d["to_process"] == {"EN_ATTENTE_CONFIRMATION": 1}
    assert d["low_stock_variants"] == 1
    assert d["cash_held_by_couriers"] == 77500
    assert d["new_contact_messages"] == 1

    past = manager.get(
        f"{API}/admin/dashboard", params={"date_from": "2020-01-01", "date_to": "2020-01-31"}
    ).json()
    assert (past["revenue"], past["orders_created"], past["delivery_success_rate"]) == (0, 0, None)
    r = manager.get(
        f"{API}/admin/dashboard", params={"date_from": "2026-02-01", "date_to": "2026-01-01"}
    )
    assert r.json()["error"]["code"] == "INVALID_PERIOD"


# --- Contact -------------------------------------------------------------------------------------


def test_contact_messages(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr(contact_router, "send_email", lambda *a: sent.append(a))
    monkeypatch.setattr(settings, "shop_notification_email", "shop@ex.com")
    r = shop.post(f"{API}/contact", json={"name": "Aya", "message": "Bonjour, une question."})
    assert r.json()["error"]["details"][0]["message"] == (
        "Indiquez un téléphone ou un e-mail pour que nous puissions répondre."
    )
    r = shop.post(
        f"{API}/contact",
        json={"name": "Aya", "email": "aya@exemple.com", "message": "Livrez-vous à Grand-Bassam ?"},
    )
    assert r.status_code == 201
    assert sent[0][:2] == ("shop@ex.com", "Nouveau message de Aya")
    inbox = manager.get(f"{API}/admin/contact-messages", params={"status": "NOUVEAU"}).json()
    assert inbox["total"] == 1
    message = inbox["items"][0]
    r = manager.patch(f"{API}/admin/contact-messages/{message['id']}", json={"status": "TRAITE"})
    assert r.json()["status"] == "TRAITE"
    assert (
        manager.get(f"{API}/admin/contact-messages", params={"status": "NOUVEAU"}).json()["total"]
        == 0
    )
    register(shop)
    assert shop.get(f"{API}/admin/contact-messages").status_code == 403


# --- Paramètres et journal -----------------------------------------------------------------------


def test_shop_settings_and_audit_log(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    owner: TestClient,  # noqa: F811
    db: Session,
) -> None:
    assert shop.get(f"{API}/shop").json()["name"] == "Projet Parfums"
    info = {
        "name": "Maison Lagune",
        "phone": "+225 27 22 00 00 00",
        "whatsapp": "07 08 12 34 56",
        "address": "Cocody, Abidjan",
        "opening_hours": "Lun-Sam 9 h-19 h",
    }
    assert manager.put(f"{API}/admin/settings/shop", json=info).status_code == 403
    r = owner.put(f"{API}/admin/settings/shop", json=info)
    assert r.status_code == 200 and r.json()["phone"] == "2722000000"
    assert shop.get(f"{API}/shop").json()["whatsapp"] == "0708123456"

    logs = owner.get(f"{API}/admin/audit-logs", params={"action": "settings"}).json()
    assert logs["total"] == 1
    entry = logs["items"][0]
    assert entry["before"]["name"] == "Projet Parfums" and entry["after"]["name"] == "Maison Lagune"
    assert entry["author"] == "Awa Koné"
    assert manager.get(f"{API}/admin/audit-logs").status_code == 403
    assert db.scalar(select(AuditLog).where(AuditLog.action == "settings.shop")) is not None


# --- Clients -------------------------------------------------------------------------------------


def test_customers(
    shop: TestClient,  # noqa: F811
    manager: TestClient,
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
) -> None:
    register(shop)  # Aya K., 0708123456
    add(shop, vid(perfume))
    number = checkout(shop, cocody).json()["number"]
    rows = manager.get(f"{API}/admin/customers").json()
    assert [(c["full_name"], c["orders_count"], c["delivered_total"]) for c in rows["items"]] == [
        ("Aya K.", 1, 0)
    ]
    assert manager.get(f"{API}/admin/customers", params={"q": "08 12 34"}).json()["total"] == 1
    assert manager.get(f"{API}/admin/customers", params={"q": "inconnu"}).json()["total"] == 0
    detail = manager.get(f"{API}/admin/customers/{rows['items'][0]['id']}").json()
    assert [o["number"] for o in detail["orders"]] == [number]
    me = manager.get(f"{API}/auth/me").json()
    assert manager.get(f"{API}/admin/customers/{me['id']}").status_code == 404  # pas un client
