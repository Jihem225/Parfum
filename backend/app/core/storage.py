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


def get_storage() -> Storage:
    # shortcut: seul le stockage local existe ; Cloudflare R2 (API S3) sera branché à l'étape 9,
    # derrière la même interface, quand le compte existera.
    return LocalStorage(Path(settings.media_dir), settings.media_base_url)
