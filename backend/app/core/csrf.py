import secrets
from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from app.core.config import settings
from app.core.errors import error_response

CSRF_COOKIE = "csrf"
CSRF_HEADER = "x-csrf-token"
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
# Avis des prestataires de paiement : sans cookie, authentifiés par leur propre signature.
_EXEMPT_PATHS = {"/api/v1/payments/notifications"}


async def csrf_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Double soumission : toute requête qui modifie quelque chose doit renvoyer en en-tête la
    valeur du cookie `csrf`, qu'un site tiers ne peut pas lire."""
    cookie = request.cookies.get(CSRF_COOKIE)
    if request.method not in _SAFE_METHODS and request.url.path not in _EXEMPT_PATHS:
        origin = request.headers.get("origin")
        header = request.headers.get(CSRF_HEADER)
        if (
            (origin and origin != settings.frontend_origin)
            or not cookie
            or not header
            or not secrets.compare_digest(cookie, header)
        ):
            return error_response(403, "CSRF_FAILED", "Requête refusée. Rechargez la page.")
    response = await call_next(request)
    if not cookie:
        response.set_cookie(
            CSRF_COOKIE,
            secrets.token_urlsafe(32),
            max_age=365 * 24 * 3600,
            secure=settings.cookie_secure,
            httponly=False,  # lu par le frontend pour être renvoyé en en-tête
            samesite="lax",
        )
    return response
