import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("parfums")


class AppError(Exception):
    """Erreur métier : code stable (le frontend s'aiguille dessus) + message lisible."""

    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status, self.code, self.message, self.details = status, code, message, details


def error_response(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return JSONResponse({"error": body}, status_code=status)


_VALIDATION_MESSAGES = {
    "missing": "Champ obligatoire.",
    "string_too_short": "Trop court : {min_length} caractères minimum.",
    "string_too_long": "Trop long : {max_length} caractères maximum.",
    "string_pattern_mismatch": "Format invalide.",
    "string_type": "Texte attendu.",
    "int_parsing": "Nombre entier attendu.",
    "int_type": "Nombre entier attendu.",
    "int_from_float": "Nombre entier attendu.",
    "bool_parsing": "Oui ou non attendu.",
    "bool_type": "Oui ou non attendu.",
    "greater_than": "Doit être supérieur à {gt}.",
    "greater_than_equal": "Doit être supérieur ou égal à {ge}.",
    "less_than": "Doit être inférieur à {lt}.",
    "less_than_equal": "Doit être inférieur ou égal à {le}.",
    "literal_error": "Valeur non autorisée.",
    "enum": "Valeur non autorisée.",
    "json_invalid": "Requête mal formée.",
}


def _field_message(err: dict[str, Any]) -> str:
    ctx = err.get("ctx") or {}
    if err["type"] == "value_error" and "error" in ctx:
        return str(ctx["error"])  # nos propres messages, déjà en français
    if err["type"] == "value_error" and "reason" in ctx:
        return "Adresse e-mail invalide."  # seul EmailStr renseigne « reason »
    template = _VALIDATION_MESSAGES.get(err["type"])
    return template.format(**ctx) if template else "Valeur invalide."


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in e["loc"][1:]), "message": _field_message(e)}
            for e in exc.errors()
        ]
        return error_response(422, "VALIDATION_ERROR", "Certaines données sont invalides.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        codes = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        return error_response(
            exc.status_code, codes.get(exc.status_code, "HTTP_ERROR"), str(exc.detail)
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("Erreur inattendue sur %s %s", request.method, request.url.path)
        return error_response(500, "INTERNAL_ERROR", "Une erreur inattendue est survenue.")
