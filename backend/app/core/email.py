import logging

import httpx

from app.core.config import settings

log = logging.getLogger("parfums.email")


def send_email(to: str, subject: str, body: str) -> None:
    """Envoi via Resend ; sans clé, l'e-mail est affiché dans la console (développement).
    Un échec est journalisé sans interrompre l'action qui l'a déclenché."""
    if not settings.resend_api_key:
        if settings.app_env == "production":
            log.error("RESEND_API_KEY absente : e-mail « %s » non envoyé à %s", subject, to)
        else:
            log.warning("E-mail (console) à %s — %s\n%s", to, subject, body)
        return
    try:
        httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.email_from, "to": [to], "subject": subject, "text": body},
            timeout=10,
        ).raise_for_status()
    except httpx.HTTPError:
        log.exception("Échec d'envoi de l'e-mail « %s » à %s", subject, to)
