from collections.abc import Iterator

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.db import get_db
from app.main import app

client = TestClient(app)


def test_health_reports_database_ok() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


class _BrokenSession:
    def execute(self, *_: object) -> None:
        raise OperationalError("SELECT 1", {}, Exception("connexion refusée"))


def test_health_returns_503_when_database_is_down() -> None:
    def broken_db() -> Iterator[_BrokenSession]:
        yield _BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/api/v1/health")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unreachable"}
