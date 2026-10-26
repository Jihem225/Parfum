import threading
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.core.db import engine
from app.core.errors import AppError
from app.modules.cart import service as cart_service
from app.modules.catalog.models import ProductVariant
from app.modules.delivery.models import Commune
from app.modules.orders import service
from app.modules.orders.models import Order
from app.modules.orders.schemas import CheckoutIn
from app.modules.promotions.models import PromoCode, PromoKind
from tests.conftest import Outbox
from tests.test_cart import add, perfume, shop, vid  # noqa: F401
from tests.test_delivery import owner  # noqa: F401
from tests.test_orders import checkout, cocody, last_bottle, mails  # noqa: F401
from tests.test_products import taxons  # noqa: F401

API = "/api/v1"
PROMOS = f"{API}/admin/promo-codes"


def promo(db: Session, code: str = "BIENVENUE", **fields: Any) -> PromoCode:
    """Code de 10 % par défaut ; `fields` remplace n'importe quelle colonne."""
    created = PromoCode(code=code, **{"kind": PromoKind.PERCENT, "value": 10} | fields)
    db.add(created)
    db.flush()
    return created


def preview(shop: TestClient, commune: Commune, code: str, phone: str = "") -> Any:  # noqa: F811
    body = {"commune_id": commune.id, "promo_code": code, "phone": phone}
    return shop.post(f"{API}/checkout/preview", json=body).json()


def order_with(shop: TestClient, commune: Commune, code: str, phone: str = "0708123456") -> Any:  # noqa: F811
    total = preview(shop, commune, code)["total"]
    return checkout(shop, commune, promo_code=code, phone=phone, expected_total=total)


def test_owner_manages_codes_and_manager_only_reads(
    owner: TestClient,  # noqa: F811
    manager: TestClient,
) -> None:
    body = {"code": " bienvenue10 ", "kind": "PERCENT", "value": 10, "max_discount": 5000}
    created = owner.post(PROMOS, json=body)
    assert created.status_code == 201
    assert (created.json()["code"], created.json()["uses"]) == ("BIENVENUE10", 0)
    assert owner.post(PROMOS, json=body).json()["error"]["code"] == "CODE_TAKEN"
    assert owner.post(PROMOS, json=body | {"code": "X1", "value": 95}).status_code == 422
    fixed_cap = body | {"code": "FIXE", "kind": "FIXED", "value": 5000}
    assert owner.post(PROMOS, json=fixed_cap).status_code == 422  # plafond : pourcentages seuls

    pid = created.json()["id"]
    updated = owner.put(
        f"{PROMOS}/{pid}", json={"kind": "FIXED", "value": 3000, "is_active": False}
    )
    assert (updated.json()["value"], updated.json()["is_active"]) == (3000, False)
    assert [p["code"] for p in manager.get(PROMOS).json()] == ["BIENVENUE10"]
    assert manager.post(PROMOS, json=body | {"code": "AUTRE"}).status_code == 403
    assert manager.delete(f"{PROMOS}/{pid}").status_code == 403
    assert owner.delete(f"{PROMOS}/{pid}").status_code == 204  # jamais utilisé


def test_preview_explains_a_refused_code_and_keeps_the_full_total(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
) -> None:
    add(shop, vid(perfume), 2)  # 76 000
    promo(db, "DIX", value=10, max_discount=5000)
    ok = preview(shop, cocody, " dix ")
    assert (ok["promo_code"], ok["discount"], ok["total"]) == ("DIX", 5000, 72500)  # plafonné
    assert ok["promo_error"] is None

    promo(db, "VIEUX", ends_at=datetime.now(UTC) - timedelta(days=1))
    promo(db, "PLUSTARD", starts_at=datetime.now(UTC) + timedelta(days=1))
    promo(db, "ARRET", is_active=False)
    promo(db, "GROS", min_subtotal=100_000)
    for code in ("INCONNU", "VIEUX", "PLUSTARD", "ARRET"):
        refused = preview(shop, cocody, code)
        assert refused["promo_error"] == "Ce code promo n'est pas valable."
        assert (refused["discount"], refused["total"]) == (0, 77500)
    assert preview(shop, cocody, "GROS")["promo_error"] == (
        "Ce code est valable à partir de 100 000 FCFA d'articles."
    )


def test_order_keeps_the_discount_and_charges_the_reduced_total(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    mails: Outbox,  # noqa: F811
    db: Session,
) -> None:
    add(shop, vid(perfume))  # 38 000
    code = promo(db, "FIXE", kind=PromoKind.FIXED, value=8000)
    order = order_with(shop, cocody, "fixe").json()
    assert (order["subtotal"], order["discount"], order["total"]) == (38000, 8000, 31500)
    assert order["promo_code"] == "FIXE"
    assert db.scalars(select(Order.promo_code_id)).one() == code.id
    assert "Code promo FIXE : −8 000 FCFA" in mails[1][2]
    assert "Total à encaisser : 31 500 FCFA" in mails[1][2]


def test_one_use_per_phone_and_global_limit_cancellation_gives_it_back(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    manager: TestClient,
    db: Session,
) -> None:
    promo(db, "DEUX", max_uses=2)
    add(shop, vid(perfume))
    first = order_with(shop, cocody, "DEUX", phone="0708123456").json()
    add(shop, vid(perfume))
    again = order_with(shop, cocody, "DEUX", phone="+225 07 08 12 34 56")
    assert again.json()["error"]["code"] == "PROMO_ALREADY_USED"
    assert preview(shop, cocody, "DEUX", phone="07 08 12 34 56")["promo_error"] == (
        "Ce code promo a déjà été utilisé avec ce numéro."
    )
    assert order_with(shop, cocody, "DEUX", phone="0102030405").status_code == 201
    add(shop, vid(perfume))
    exhausted = order_with(shop, cocody, "DEUX", phone="0506070809")
    assert exhausted.json()["error"]["code"] == "PROMO_EXHAUSTED"

    # RG-84 : la commande annulée rend son utilisation (au client comme au total).
    cancel = {"to": "ANNULEE", "note": "Client injoignable"}
    assert manager.post(f"{API}/admin/orders/{first['number']}/transition", json=cancel).is_success
    assert order_with(shop, cocody, "DEUX", phone="0708123456").status_code == 201
    listed = manager.get(PROMOS).json()[0]
    assert (listed["uses"], listed["discount_total"]) == (2, 7600)


def test_a_code_cannot_make_the_order_free(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    db: Session,
) -> None:
    free_delivery = Commune(name="Plateau", delivery_fee=0, delay_label="24 h")
    db.add(free_delivery)
    db.flush()
    promo(db, "TOUT", kind=PromoKind.FIXED, value=50_000)
    add(shop, vid(perfume))
    assert preview(shop, free_delivery, "TOUT")["discount"] == 38000  # jamais plus que les articles
    body = {"promo_code": "TOUT", "expected_total": 1}
    refused = checkout(shop, free_delivery, **body)
    assert refused.json()["error"]["code"] == "PROMO_INVALID"


def test_used_code_cannot_be_deleted(
    owner: TestClient,  # noqa: F811
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    db: Session,
) -> None:
    used = promo(db, "UTILISE")
    add(shop, vid(perfume))
    assert order_with(shop, cocody, "UTILISE").status_code == 201
    assert owner.delete(f"{PROMOS}/{used.id}").json()["error"]["code"] == "PROMO_USED"


@pytest.fixture
def limited_code(last_bottle: dict[str, Any]) -> Iterator[str]:  # noqa: F811
    """Code limité à 2 utilisations, réellement validé en base, avec du stock pour tous."""
    with Session(engine) as setup:
        setup.execute(
            update(ProductVariant)
            .where(ProductVariant.id == last_bottle["variant"])
            .values(stock_physical=10)
        )
        setup.add(PromoCode(code="TEST-CONCURRENCE", kind=PromoKind.FIXED, value=100, max_uses=2))
        setup.commit()
    try:
        yield "TEST-CONCURRENCE"
    finally:
        with Session(engine) as cleanup:
            code = PromoCode.code == "TEST-CONCURRENCE"
            ids = cleanup.scalars(select(PromoCode.id).where(code)).all()
            cleanup.execute(
                update(Order).where(Order.promo_code_id.in_(ids)).values(promo_code_id=None)
            )
            cleanup.execute(delete(PromoCode).where(code))
            cleanup.commit()


def test_simultaneous_orders_respect_the_global_limit(
    last_bottle: dict[str, Any],  # noqa: F811
    limited_code: str,
) -> None:
    """Huit clients (téléphones différents) valident en même temps : deux seulement ont le code."""
    start = threading.Barrier(len(last_bottle["tokens"]))
    results: list[str] = []

    def buy(index: int, token: str) -> None:
        data = CheckoutIn(
            customer_name="Client Test",
            phone=f"07000000{index:02d}",
            commune_id=last_bottle["commune"],
            address_line="Adresse de test",
            accept_terms=True,
            expected_total=1900,  # 1 000 − 100 + 1 000
            idempotency_key=uuid.uuid4().hex,
            promo_code=limited_code,
        )
        with Session(engine) as db:
            start.wait()
            try:
                service.checkout(db, data, cart=cart_service.find(db, None, token), user=None)
                db.commit()
                results.append("ok")
            except AppError as exc:
                db.rollback()
                results.append(exc.code)

    threads = [
        threading.Thread(target=buy, args=(i, t)) for i, t in enumerate(last_bottle["tokens"])
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["PROMO_EXHAUSTED"] * 6 + ["ok"] * 2
