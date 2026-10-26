from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import email
from app.core.config import settings
from app.core.email import queue_email, send_due
from app.core.models import AuditLog, EmailMessage, EmailStatus
from app.modules.delivery.models import Commune
from tests.conftest import Outbox
from tests.test_cart import add, perfume, shop, vid  # noqa: F401
from tests.test_orders import checkout, cocody, mails  # noqa: F401
from tests.test_products import taxons  # noqa: F401

API = "/api/v1"
NOW = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


@pytest.fixture
def resend(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Faux Resend : rejoue les codes HTTP de la liste, dans l'ordre (200 une fois vide)."""
    codes: list[int] = []
    monkeypatch.setattr(settings, "resend_api_key", "re_test")

    def post(url: str, **_: Any) -> httpx.Response:
        code = codes.pop(0) if codes else 200
        if code == 0:
            raise httpx.ConnectError("réseau coupé")
        return httpx.Response(code, text="réponse", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    return codes


def queued(db: Session, to: str = "aya@exemple.com") -> EmailMessage:
    queue_email(db, to, "Commande PP-10001 reçue", "Lien : https://exemple.com/x?token=secret")
    db.flush()
    message = db.scalars(select(EmailMessage).order_by(EmailMessage.id.desc())).first()
    assert message is not None
    message.next_attempt_at = NOW
    return message


def test_order_email_is_queued_with_the_order_and_not_without_it(
    shop: TestClient,  # noqa: F811
    perfume: dict[str, Any],  # noqa: F811
    cocody: Commune,  # noqa: F811
    mails: Outbox,  # noqa: F811
    db: Session,
) -> None:
    add(shop, vid(perfume))
    refused = checkout(shop, cocody, expected_total=1)  # total périmé : commande refusée
    assert refused.status_code == 409
    assert mails == []  # transaction annulée : aucun e-mail
    assert checkout(shop, cocody).status_code == 201
    assert [m[0] for m in mails] == ["aya@exemple.com", "shop@ex.com"]
    statuses = db.scalars(select(EmailMessage.status)).all()
    assert statuses == [EmailStatus.PENDING, EmailStatus.PENDING]


def test_sent_email_forgets_its_content(db: Session, resend: list[int]) -> None:
    message = queued(db)
    assert send_due(db, NOW) == 1
    assert (message.status, message.attempts, message.sent_at) == (EmailStatus.SENT, 1, NOW)
    assert message.body == ""  # plus de lien à usage unique en base
    assert send_due(db, NOW) == 0  # rien à renvoyer


def test_temporary_failures_are_retried_then_abandoned(db: Session, resend: list[int]) -> None:
    message = queued(db)
    resend.extend([0, 503, 429])
    now = NOW
    for expected_delay in (1, 5, 15):
        assert send_due(db, now) == 1
        assert message.status == EmailStatus.PENDING
        assert message.next_attempt_at == now + timedelta(minutes=expected_delay)
        assert send_due(db, now) == 0  # pas avant l'échéance
        now = message.next_attempt_at
    assert send_due(db, now) == 1  # 4e essai : envoyé
    assert (message.status, message.attempts) == (EmailStatus.SENT, 4)

    other = queued(db)
    resend.extend([503] * 6)
    now = NOW
    for _ in range(6):
        assert send_due(db, now) == 1
        now = other.next_attempt_at
    assert (other.status, other.attempts) == (EmailStatus.FAILED, 6)
    assert other.last_error and "503" in other.last_error
    assert other.body.startswith("Lien")  # gardé pour un renvoi


def test_refused_address_is_not_retried(db: Session, resend: list[int]) -> None:
    message = queued(db, to="adresse-invalide")
    resend.append(422)
    send_due(db, NOW)
    assert (message.status, message.attempts) == (EmailStatus.FAILED, 1)
    assert message.last_error and "422" in message.last_error


def test_production_without_resend_key_fails_visibly(
    db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "app_env", "production")
    message = queued(db)
    send_due(db, NOW)
    assert message.status == EmailStatus.FAILED
    assert message.last_error and "RESEND_API_KEY" in message.last_error


def test_sent_emails_are_purged_after_30_days(db: Session, resend: list[int]) -> None:
    old, recent = queued(db), queued(db)
    send_due(db, NOW)
    old.sent_at = NOW - timedelta(days=31)
    email.purge_sent(db, NOW)
    remaining = db.scalars(select(EmailMessage.id)).all()
    assert remaining == [recent.id]


def test_back_office_lists_and_retries_failed_emails(
    manager: TestClient, db: Session, resend: list[int]
) -> None:
    message = queued(db)
    resend.append(422)
    send_due(db, NOW)
    page = manager.get(f"{API}/admin/emails").json()
    assert [e["id"] for e in page["items"]] == [message.id]
    assert page["items"][0]["last_error"].startswith("PermanentError")
    assert "body" not in page["items"][0]  # le contenu (liens) ne sort pas de la base
    assert manager.get(f"{API}/admin/dashboard").json()["failed_emails"] == 1

    r = manager.post(f"{API}/admin/emails/{message.id}/retry")
    assert (r.json()["status"], r.json()["attempts"]) == ("PENDING", 0)
    assert manager.post(f"{API}/admin/emails/{message.id}/retry").status_code == 409
    assert db.scalars(select(AuditLog.action).where(AuditLog.action == "email.retry")).one()
    db.refresh(message)
    send_due(db, datetime.now(UTC))
    assert message.status == EmailStatus.SENT


def test_emails_are_back_office_only(client: TestClient) -> None:
    assert client.get(f"{API}/admin/emails").status_code == 401
    assert client.post(f"{API}/admin/emails/1/retry").status_code == 401
