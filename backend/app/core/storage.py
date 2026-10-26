from functools import cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def delete(self, key: str) -> None: ...
    def url(self, key: str) -> str: ...


class LocalStorage:
    """Fichiers sur disque, servis par l'API sous /media. Clés toujours générées par le serveur."""

    def __init__(self, root: Path, base_url: str) -> None:
        self.root, self.base_url = root, base_url.rstrip("/")

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def delete(self, key: str) -> None:
        (self.root / key).unlink(missing_ok=True)

    def url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


class S3Storage:
    """Cloudflare R2 (API S3). Les images sont lues par le navigateur sur le domaine public du
    compartiment ; les clés contiennent un identifiant unique, d'où le cache « immutable »."""

    def __init__(self) -> None:
        import boto3  # type: ignore[import-untyped]

        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name="auto",
        )
        self.bucket, self.base_url = settings.s3_bucket, settings.s3_public_base_url.rstrip("/")

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            CacheControl="public, max-age=31536000, immutable",
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def url(self, key: str) -> str:
        return f"{self.base_url}/{key}"


@cache  # un seul client S3 par processus
def get_storage() -> Storage:
    if settings.s3_bucket:
        return S3Storage()
    return LocalStorage(Path(settings.media_dir), settings.media_base_url)
