from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db

is_prod = settings.app_env == "production"
app = FastAPI(
    title="Projet Parfums — API",
    version="0.1.0",
    docs_url=None if is_prod else "/api/v1/docs",
    redoc_url=None,
    openapi_url=None if is_prod else "/api/v1/openapi.json",
)

api = APIRouter(prefix="/api/v1")


@api.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "error", "database": "unreachable"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "ok"})


app.include_router(api)
