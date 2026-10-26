import random
from datetime import UTC, datetime

from sqlalchemy import text

from app.core.db import engine
from app.core.errors import AppError


def _window_start(window_seconds: int) -> datetime:
    now = int(datetime.now(UTC).timestamp())
    return datetime.fromtimestamp(now - now % window_seconds, UTC)


def record_hit(key: str, window_seconds: int) -> int:
    """Incrémente le compteur de la fenêtre courante et renvoie sa valeur.
    Connexion à part : le compteur survit même si la requête échoue ensuite."""
    with engine.begin() as conn:
        count = conn.execute(
            text(
                "INSERT INTO rate_limit_hits (key, window_start, count) VALUES (:k, :w, 1) "
                "ON CONFLICT (key, window_start) "
                "DO UPDATE SET count = rate_limit_hits.count + 1 RETURNING count"
            ),
            {"k": key, "w": _window_start(window_seconds)},
        ).scalar_one()
        if random.random() < 0.01:  # noqa: S311  # ménage occasionnel, pas de la cryptographie
            conn.execute(
                text("DELETE FROM rate_limit_hits WHERE window_start < now() - interval '1 day'")
            )
    return int(count)


def hits(key: str, window_seconds: int) -> int:
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT count FROM rate_limit_hits WHERE key = :k AND window_start = :w"),
            {"k": key, "w": _window_start(window_seconds)},
        ).scalar_one_or_none()
    return int(count or 0)


def too_many() -> AppError:
    return AppError(429, "RATE_LIMITED", "Trop de tentatives. Réessayez dans quelques minutes.")


def limit(key: str, max_hits: int, window_seconds: int) -> None:
    if record_hit(key, window_seconds) > max_hits:
        raise too_many()
