"""E-mails par file d'envoi (table `email_outbox`) : `queue_email` les écrit dans la transaction
de l'action (rien n'est perdu si l'envoi échoue ou si l'action est annulée), la tâche de fond les
envoie via Resend et réessaie en cas d'échec. Sans clé Resend hors production, l'e-mail est
affiché dans la console (développement)."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

import httpx
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.models import EmailMessage, EmailStatus

log = logging.getLogger("parfums.email")

Message = tuple[str, str, str]  # destinataire, objet, texte
# Délai avant chaque nouvel essai : 6 essais en tout, sur un peu plus de 4 heures.
RETRY_DELAYS = tuple(timedelta(minutes=m) for m in (1, 5, 15, 60, 180))
KEEP_SENT = timedelta(days=30)  # trace des envois (destinataire, objet), puis effacée


class PermanentError(Exception):
    """Refus définitif du fournisseur (adresse invalide…) : inutile de réessayer."""


def queue_email(db: Session, to: str, subject: str, body: str) -> None:
    db.add(EmailMessage(to_address=to, subject=subject[:300], body=body))


def queue(db: Session, *messages: Message | None) -> None:
    for message in messages:
        if message is not None:
            queue_email(db, *message)


def _deliver(to: str, subject: str, body: str) -> None:
    if not settings.resend_api_key:
        if settings.app_env == "production":
            raise PermanentError("RESEND_API_KEY absente")
        log.warning("E-mail (console) à %s — %s\n%s", to, subject, body)
        return
    response = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={"from": settings.email_from, "to": [to], "subject": subject, "text": body},
        timeout=10,
    )
    if 400 <= response.status_code < 500 and response.status_code != 429:
        raise PermanentError(f"Resend {response.status_code} : {response.text[:300]}")
    response.raise_for_status()


def attempt(message: EmailMessage, now: datetime) -> None:
    """Un essai d'envoi ; met à jour l'état du message (sans valider la transaction)."""
    message.attempts += 1
    try:
        _deliver(message.to_address, message.subject, message.body)
    except Exception as error:  # réseau, Resend indisponible, refus…
        message.last_error = f"{type(error).__name__} : {error}"[:500]
        retry = not isinstance(error, PermanentError) and message.attempts <= len(RETRY_DELAYS)
        if retry:
            message.next_attempt_at = now + RETRY_DELAYS[message.attempts - 1]
            log.warning("E-mail %s à réessayer : %s", message.id, message.last_error)
        else:
            message.status = EmailStatus.FAILED
            log.error("E-mail %s abandonné (« %s ») : %s", message.id, message.subject, error)
        return
    message.status = EmailStatus.SENT
    message.sent_at = now
    message.body = ""  # le contenu (liens à usage unique, adresses) n'est plus utile
    message.last_error = None


def send_due(db: Session, now: datetime, limit: int = 50) -> int:
    """Envoie les e-mails arrivés à échéance, un par transaction (verrou SKIP LOCKED : plusieurs
    processus peuvent tourner sans double envoi). Renvoie le nombre d'essais."""
    done = 0
    while done < limit:
        message = db.scalars(
            select(EmailMessage)
            .where(EmailMessage.status == EmailStatus.PENDING, EmailMessage.next_attempt_at <= now)
            .order_by(EmailMessage.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        ).first()
        if message is None:
            break
        attempt(message, now)
        db.commit()
        done += 1
    return done


def purge_sent(db: Session, now: datetime) -> None:
    db.execute(
        delete(EmailMessage).where(
            EmailMessage.status == EmailStatus.SENT, EmailMessage.sent_at < now - KEEP_SENT
        )
    )
    db.commit()


_last_purge = datetime.min.replace(tzinfo=UTC)


def _run_once() -> None:
    global _last_purge
    now = datetime.now(UTC)
    with SessionLocal() as db:
        send_due(db, now)
        if now - _last_purge > timedelta(hours=1):
            purge_sent(db, now)
            _last_purge = now


async def send_forever(every_seconds: int = 5) -> None:
    while True:
        try:
            await run_in_threadpool(_run_once)
        except Exception:  # la boucle doit survivre à une base momentanément indisponible
            log.exception("Échec de la file d'envoi des e-mails")
        await asyncio.sleep(every_seconds)
