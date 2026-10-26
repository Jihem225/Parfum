from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.validators import normalize_ci_phone
from app.modules.auth.models import PasswordResetToken, User, UserSession

API = "/api/v1/auth"
NEW_CUSTOMER = {
    "email": "Aya@Exemple.com",
    "password": "motdepasse-solide",
    "full_name": "Aya Kouassi",
    "phone": "+225 07 08 12 34 56",
}


def register(client: TestClient, **overrides: Any) -> Any:
    return client.post(f"{API}/register", json=NEW_CUSTOMER | overrides)


def login(client: TestClient, email: str, password: str, **extra: Any) -> Any:
    return client.post(f"{API}/login", json={"email": email, "password": password, **extra})


# --- Validation des numéros ivoiriens -------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0708123456", "0708123456"),
        ("+225 07 08 12 34 56", "0708123456"),
        ("00225-05.44.21.87.90", "0544218790"),
    ],
)
def test_phone_is_normalized(raw: str, expected: str) -> None:
    assert normalize_ci_phone(raw) == expected


@pytest.mark.parametrize("raw", ["708123456", "07081234567", "+33 6 12 34 56 78", "abc"])
def test_invalid_phone_is_rejected(raw: str) -> None:
    with pytest.raises(ValueError, match="10 chiffres"):
        normalize_ci_phone(raw)


# --- Inscription, connexion, session ----------------------------------------------------------


def test_register_opens_a_customer_session(client: TestClient) -> None:
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "aya@exemple.com"  # e-mail normalisé
    assert body["phone"] == "0708123456"
    assert body["role"] == "CUSTOMER"
    assert "session" in response.cookies
    assert client.get(f"{API}/me").json()["id"] == body["id"]


def test_session_cookie_is_http_only(client: TestClient) -> None:
    set_cookie = register(client).headers["set-cookie"].lower()
    assert "session=" in set_cookie and "httponly" in set_cookie and "samesite=lax" in set_cookie


def test_password_is_hashed_with_argon2(client: TestClient, db: Session) -> None:
    register(client)
    user = db.scalar(select(User).where(User.email == "aya@exemple.com"))
    assert user is not None and user.password_hash.startswith("$argon2id$")


def test_register_refuses_duplicate_email_whatever_the_case(client: TestClient) -> None:
    register(client)
    response = register(client, email="AYA@exemple.COM")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_TAKEN"


def test_register_validates_input_with_french_messages(client: TestClient) -> None:
    response = register(client, password="court", phone="123")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    messages = {d["field"]: d["message"] for d in error["details"]}
    assert messages["password"] == "Trop court : 10 caractères minimum."
    assert "10 chiffres" in messages["phone"]


def test_login_and_logout(client: TestClient) -> None:
    register(client)
    client.post(f"{API}/logout")
    assert client.get(f"{API}/me").status_code == 401
    response = login(client, "aya@exemple.com", NEW_CUSTOMER["password"])
    assert response.status_code == 200
    assert client.get(f"{API}/me").status_code == 200
    assert client.post(f"{API}/logout").status_code == 204
    assert client.get(f"{API}/me").json()["error"]["code"] == "AUTH_REQUIRED"


def test_wrong_password_and_unknown_email_get_the_same_answer(client: TestClient) -> None:
    register(client)
    wrong = login(client, "aya@exemple.com", "mauvais-mot-de-passe")
    unknown = login(client, "personne@exemple.com", "mauvais-mot-de-passe")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_login_is_blocked_after_five_failures(client: TestClient) -> None:
    register(client)
    for _ in range(5):
        assert login(client, "aya@exemple.com", "mauvais-mot-de-passe").status_code == 401
    # Même le bon mot de passe est refusé pendant le blocage.
    blocked = login(client, "aya@exemple.com", NEW_CUSTOMER["password"])
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"


def test_mutation_without_csrf_token_is_refused(client: TestClient) -> None:
    del client.headers["X-CSRF-Token"]
    response = register(client)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_mutation_from_another_site_is_refused(client: TestClient) -> None:
    response = client.post(
        f"{API}/register", json=NEW_CUSTOMER, headers={"Origin": "https://pirate.example"}
    )
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_deactivated_account_loses_access_immediately(client: TestClient, db: Session) -> None:
    register(client)
    db.execute(update(User).where(User.email == "aya@exemple.com").values(is_active=False))
    assert client.get(f"{API}/me").status_code == 401


def test_expired_session_is_refused(client: TestClient, db: Session) -> None:
    register(client)
    db.execute(update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
    assert client.get(f"{API}/me").status_code == 401


# --- Mot de passe oublié / modification --------------------------------------------------------


def test_forgot_password_answers_the_same_for_unknown_email(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr("app.modules.auth.router.send_email", lambda *a: sent.append(a))
    register(client)
    known = client.post(f"{API}/forgot-password", json={"email": "aya@exemple.com"})
    unknown = client.post(f"{API}/forgot-password", json={"email": "x@exemple.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(sent) == 1 and sent[0][0] == "aya@exemple.com"


def test_reset_password_flow(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr("app.modules.auth.router.send_email", lambda *a: sent.append(a))
    register(client)
    client.post(f"{API}/forgot-password", json={"email": "aya@exemple.com"})
    token = sent[0][2].split("token=")[1].split()[0]

    response = client.post(
        f"{API}/reset-password", json={"token": token, "password": "nouveau-mot-de-passe"}
    )
    assert response.status_code == 200
    assert client.get(f"{API}/me").status_code == 401  # toutes les sessions sont fermées
    assert login(client, "aya@exemple.com", "nouveau-mot-de-passe").status_code == 200

    reused = client.post(
        f"{API}/reset-password", json={"token": token, "password": "encore-un-autre-mdp"}
    )
    assert reused.json()["error"]["code"] == "INVALID_TOKEN"  # usage unique


def test_expired_reset_link_is_refused(
    client: TestClient, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[str, str, str]] = []
    monkeypatch.setattr("app.modules.auth.router.send_email", lambda *a: sent.append(a))
    register(client)
    client.post(f"{API}/forgot-password", json={"email": "aya@exemple.com"})
    db.execute(
        update(PasswordResetToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    token = sent[0][2].split("token=")[1].split()[0]
    response = client.post(
        f"{API}/reset-password", json={"token": token, "password": "nouveau-mot-de-passe"}
    )
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_change_password_requires_the_current_one(client: TestClient) -> None:
    register(client)
    bad = client.post(
        f"{API}/change-password",
        json={"current_password": "pas-le-bon-mdp", "new_password": "nouveau-mot-de-passe"},
    )
    assert bad.json()["error"]["code"] == "INVALID_PASSWORD"
    ok = client.post(
        f"{API}/change-password",
        json={"current_password": NEW_CUSTOMER["password"], "new_password": "nouveau-mot-de-passe"},
    )
    assert ok.status_code == 200
    assert client.get(f"{API}/me").status_code == 200  # la session courante reste ouverte
