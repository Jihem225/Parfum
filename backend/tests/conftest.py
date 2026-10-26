import os
from collections.abc import Iterator
from pathlib import Path

import pytest

# Les tests tournent toujours sur une base dédiée, jamais sur la base de développement.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://localhost/parfums_test"
)
os.environ["APP_ENV"] = "test"

from alembic.config import Config  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from alembic import command  # noqa: E402
from app.core.db import engine  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _migrated_database() -> None:
    command.upgrade(Config(str(Path(__file__).parents[1] / "alembic.ini")), "head")


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
