"""Tâche de fond : annule les commandes mobile money non payées dans le délai (stock libéré)."""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi.concurrency import run_in_threadpool

from app.core.db import SessionLocal
from app.core.email import send_email
from app.modules.orders import notify, service

log = logging.getLogger("parfums.jobs")


def expire_once() -> int:
    with SessionLocal() as db:
        expired = service.expire_unpaid(db, datetime.now(UTC))
        db.commit()
    for order in expired:
        if message := notify.to_customer(order):
            send_email(*message)
    return len(expired)


async def expire_forever(every_seconds: int = 60) -> None:
    while True:
        await asyncio.sleep(every_seconds)
        try:
            if count := await run_in_threadpool(expire_once):
                log.info("%d commande(s) non payée(s) annulée(s)", count)
        except Exception:  # la boucle doit survivre à une base momentanément indisponible
            log.exception("Échec de l'annulation des commandes non payées")
