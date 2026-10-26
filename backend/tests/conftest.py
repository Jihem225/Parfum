import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Les tests tournent toujours sur une base dédiée, jamais sur la base de développement.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost/parfums_test"
)
os.environ["APP_ENV"] = "test"
os.environ.setdefault("SECRET_KEY", "secret-de-test-uniquement")
os.environ["COOKIE_SECURE"] = "false"
os.environ["RESEND_API_KEY"] = ""

from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import engine, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")


@pytest.fixture(autouse=True)
def _reset_rate_limits() -> None:
    # Les compteurs s'écrivent hors de la transaction du test : on les vide à chaque test.
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rate_limit_hits"))


@pytest.fixture
def db() -> Iterator[Session]:
    """Session dans une transaction annulée à la fin du test : la base reste propre."""
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """Client HTTP branché sur la session de test, avec le jeton CSRF déjà récupéré."""

    def _db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _db
    with TestClient(app) as http:
        http.get("/api/v1/health")
        http.headers["X-CSRF-Token"] = http.cookies["csrf"]
        yield http
    app.dependency_overrides.clear()
