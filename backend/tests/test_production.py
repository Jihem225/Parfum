from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.core import storage
from app.core.config import Settings, settings

SAFE: dict[str, Any] = {
    "app_env": "production",
    "database_url": "postgresql+psycopg://db/parfums",
    "secret_key": "x" * 48,
    "frontend_origin": "https://boutique.exemple.ci",
    "cookie_secure": True,
    "s3_bucket": "images",
    "trusted_proxy_hops": 1,
}


def test_safe_production_settings_are_accepted() -> None:
    Settings(**SAFE)


def test_render_database_url_uses_psycopg3() -> None:
    url = Settings(**{**SAFE, "database_url": "postgresql://u:p@host/parfums"}).database_url
    assert url == "postgresql+psycopg://u:p@host/parfums"


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"cookie_secure": False}, "COOKIE_SECURE"),
        ({"frontend_origin": "http://boutique.exemple.ci"}, "FRONTEND_ORIGIN"),
        ({"secret_key": "court"}, "SECRET_KEY"),
        ({"s3_bucket": ""}, "S3_"),
        ({"trusted_proxy_hops": 0}, "TRUSTED_PROXY_HOPS"),
    ],
)
def test_unsafe_production_settings_refuse_to_start(override: dict[str, Any], reason: str) -> None:
    with pytest.raises(ValidationError, match=reason):
        Settings(**{**SAFE, **override})


def test_r2_storage_uploads_with_long_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    client = MagicMock()
    monkeypatch.setattr("boto3.client", lambda *a, **k: client)
    monkeypatch.setattr(settings, "s3_bucket", "images")
    monkeypatch.setattr(settings, "s3_public_base_url", "https://images.exemple.ci/")
    r2 = storage.S3Storage()
    r2.put("products/1/a.webp", b"x", "image/webp")
    r2.delete("products/1/a.webp")
    kwargs = client.put_object.call_args.kwargs
    assert (kwargs["Bucket"], kwargs["Key"], kwargs["ContentType"]) == (
        "images",
        "products/1/a.webp",
        "image/webp",
    )
    assert "immutable" in kwargs["CacheControl"]
    client.delete_object.assert_called_once_with(Bucket="images", Key="products/1/a.webp")
    assert r2.url("products/1/a.webp") == "https://images.exemple.ci/products/1/a.webp"
