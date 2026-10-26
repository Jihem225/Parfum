from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.csrf import csrf_middleware
from app.core.db import get_db
from app.core.errors import install_error_handlers
from app.modules.auth.router import router as auth_router
from app.modules.cart.router import router as cart_router
from app.modules.catalog.products_router import admin as products_admin_router
from app.modules.catalog.products_router import public as products_router
from app.modules.catalog.router import admin as catalog_admin_router
from app.modules.catalog.router import public as catalog_router
from app.modules.customers.router import router as customer_router
from app.modules.delivery.courier import router as courier_router
from app.modules.delivery.router import admin as communes_admin_router
from app.modules.delivery.router import public as delivery_router
from app.modules.inventory.router import admin as stock_admin_router
from app.modules.orders.router import admin as orders_admin_router
from app.modules.orders.router import public as orders_router
from app.modules.payments.router import admin as cash_admin_router
from app.modules.staff.router import router as staff_router

is_prod = settings.app_env == "production"
app = FastAPI(
    title="Projet Parfums — API",
    version="0.1.0",
    docs_url=None if is_prod else "/api/v1/docs",
    redoc_url=None,
    openapi_url=None if is_prod else "/api/v1/openapi.json",
)
install_error_handlers(app)
app.middleware("http")(csrf_middleware)

api = APIRouter(prefix="/api/v1")


@api.get("/health", tags=["santé"])
def health(db: Annotated[Session, Depends(get_db)]) -> JSONResponse:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse({"status": "error", "database": "unreachable"}, status_code=503)
    return JSONResponse({"status": "ok", "database": "ok"})


api.include_router(auth_router)
api.include_router(staff_router)
api.include_router(catalog_router)
api.include_router(catalog_admin_router)
api.include_router(products_router)
api.include_router(products_admin_router)
api.include_router(stock_admin_router)
api.include_router(cart_router)
api.include_router(delivery_router)
api.include_router(communes_admin_router)
api.include_router(orders_router)
api.include_router(orders_admin_router)
api.include_router(courier_router)
api.include_router(cash_admin_router)
api.include_router(customer_router)
app.include_router(api)

# Images du stockage local (développement) ; en production elles seront servies par R2.
Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")
