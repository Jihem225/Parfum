from typing import Any

import pyotp
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.models import AuditLog
from app.modules.auth.models import User, UserRole

PASSWORD = "motdepasse-du-proprio"


def make_staff(db: Session, email: str, role: UserRole, *, totp_secret: str | None = None) -> User:
    user = User(
        email=email,
        password_hash=security.hash_password(PASSWORD),
        full_name="Awa Koné",
        phone="0708123456",
        role=role,
        totp_secret=security.encrypt(totp_secret) if totp_secret else None,
    )
    db.add(user)
    db.flush()
    return user


def login(client: TestClient, email: str, **extra: Any) -> Any:
    return client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD, **extra})


def login_owner_with_totp(client: TestClient, db: Session) -> User:
    secret = pyotp.random_base32()
    owner = make_staff(db, "proprio@exemple.com", UserRole.OWNER, totp_secret=secret)
    assert login(client, owner.email, totp_code=pyotp.TOTP(secret).now()).status_code == 200
    return owner


def test_anonymous_and_customers_cannot_reach_the_back_office(
    client: TestClient, db: Session
) -> None:
    assert client.get("/api/v1/admin/staff").json()["error"]["code"] == "AUTH_REQUIRED"
    make_staff(db, "client@exemple.com", UserRole.CUSTOMER)
    login(client, "client@exemple.com")
    response = client.get("/api/v1/admin/staff")
    assert response.status_code == 403 and response.json()["error"]["code"] == "FORBIDDEN"


def test_manager_cannot_manage_staff(client: TestClient, db: Session) -> None:
    secret = pyotp.random_base32()
    make_staff(db, "gestion@exemple.com", UserRole.MANAGER, totp_secret=secret)
    login(client, "gestion@exemple.com", totp_code=pyotp.TOTP(secret).now())
    assert client.get("/api/v1/admin/staff").json()["error"]["code"] == "FORBIDDEN"


def test_owner_must_enable_totp_before_using_the_back_office(
    client: TestClient, db: Session
) -> None:
    make_staff(db, "proprio@exemple.com", UserRole.OWNER)
    assert login(client, "proprio@exemple.com").status_code == 200
    blocked = client.get("/api/v1/admin/staff")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "TOTP_SETUP_REQUIRED"

    setup = client.post("/api/v1/auth/totp/setup").json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/")
    wrong = client.post(
        "/api/v1/auth/totp/enable", json={"secret": setup["secret"], "code": "000000"}
    )
    assert wrong.json()["error"]["code"] == "TOTP_INVALID"
    enabled = client.post(
        "/api/v1/auth/totp/enable",
        json={"secret": setup["secret"], "code": pyotp.TOTP(setup["secret"]).now()},
    )
    assert enabled.status_code == 200
    assert len(enabled.json()["recovery_codes"]) == 8
    assert client.get("/api/v1/admin/staff").status_code == 200


def test_totp_is_required_at_login_once_enabled(client: TestClient, db: Session) -> None:
    secret = pyotp.random_base32()
    make_staff(db, "proprio@exemple.com", UserRole.OWNER, totp_secret=secret)
    assert login(client, "proprio@exemple.com").json()["error"]["code"] == "TOTP_REQUIRED"
    bad = login(client, "proprio@exemple.com", totp_code="123456")
    assert bad.json()["error"]["code"] == "TOTP_INVALID"
    ok = login(client, "proprio@exemple.com", totp_code=pyotp.TOTP(secret).now())
    assert ok.status_code == 200


def test_totp_secret_is_stored_encrypted(client: TestClient, db: Session) -> None:
    secret = pyotp.random_base32()
    owner = make_staff(db, "proprio@exemple.com", UserRole.OWNER, totp_secret=secret)
    assert owner.totp_secret is not None and secret not in owner.totp_secret
    assert security.decrypt(owner.totp_secret) == secret


def test_recovery_code_works_only_once(client: TestClient, db: Session) -> None:
    owner = make_staff(db, "proprio@exemple.com", UserRole.OWNER)
    owner.totp_secret = security.encrypt(pyotp.random_base32())
    owner.totp_recovery_codes = [security.sha256("abcdef-123456")]
    db.flush()
    assert login(client, owner.email, totp_code="abcdef-123456").status_code == 200
    client.post("/api/v1/auth/logout")
    assert login(client, owner.email, totp_code="abcdef-123456").status_code == 401


def test_owner_creates_a_collaborator_and_it_is_audited(client: TestClient, db: Session) -> None:
    owner = login_owner_with_totp(client, db)
    response = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "koffi@exemple.com",
            "full_name": "Koffi B.",
            "phone": "05 44 21 87 90",
            "role": "COURIER",
            "temporary_password": "provisoire-123",
        },
    )
    assert response.status_code == 201 and response.json()["role"] == "COURIER"
    log = db.scalar(select(AuditLog).where(AuditLog.action == "staff.create"))
    assert log is not None and log.user_id == owner.id
    assert log.after is not None and log.after["email"] == "koffi@exemple.com"


def test_collaborator_cannot_be_created_as_customer(client: TestClient, db: Session) -> None:
    login_owner_with_totp(client, db)
    response = client.post(
        "/api/v1/admin/staff",
        json={
            "email": "x@exemple.com",
            "full_name": "X Y",
            "phone": "0544218790",
            "role": "CUSTOMER",
            "temporary_password": "provisoire-123",
        },
    )
    assert response.json()["error"]["code"] == "INVALID_ROLE"


def test_last_owner_cannot_be_demoted_or_deactivated(client: TestClient, db: Session) -> None:
    owner = login_owner_with_totp(client, db)
    for change in ({"role": "MANAGER"}, {"is_active": False}):
        response = client.patch(f"/api/v1/admin/staff/{owner.id}", json=change)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "LAST_OWNER"


def test_deactivating_a_collaborator_closes_their_sessions(client: TestClient, db: Session) -> None:
    courier = make_staff(db, "koffi@exemple.com", UserRole.COURIER)
    with TestClient(client.app) as courier_client:
        courier_client.get("/api/v1/health")
        courier_client.headers["X-CSRF-Token"] = courier_client.cookies["csrf"]
        assert login(courier_client, courier.email).status_code == 200
        login_owner_with_totp(client, db)
        response = client.patch(f"/api/v1/admin/staff/{courier.id}", json={"is_active": False})
        assert response.status_code == 200
        assert courier_client.get("/api/v1/auth/me").status_code == 401
