from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core import rate_limit
from app.core.config import settings
from app.core.errors import AppError
from app.modules.auth.deps import DB, client_ip, get_optional_user
from app.modules.auth.models import User
from app.modules.cart import service
from app.modules.cart.schemas import CartItemIn, CartOut, QuantityIn

router = APIRouter(prefix="/cart", tags=["panier"])

CART_COOKIE = "cart"
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def _remember(response: Response, raw: str) -> None:
    """Cookie visiteur prolongé à chaque modification : le panier survit à la fermeture."""
    response.set_cookie(
        CART_COOKIE,
        raw,
        max_age=int(service.GUEST_TTL.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.get("")
def get_cart(request: Request, user: OptionalUser, db: DB) -> CartOut:
    return service.view(db, service.find(db, user, request.cookies.get(CART_COOKIE)))


@router.post("/items", status_code=201)
def add_item(
    data: CartItemIn, request: Request, response: Response, user: OptionalUser, db: DB
) -> CartOut:
    raw = request.cookies.get(CART_COOKIE)
    if user is None and service.find(db, None, raw) is None:
        rate_limit.limit(f"cart:ip:{client_ip(request)}", 30, 3600)  # création de paniers visiteur
    cart, new_raw = service.get_or_create(db, user, raw)
    service.set_quantity(db, cart, data.variant_id, data.quantity, add=True)
    db.commit()
    if user is None:
        _remember(response, new_raw or raw or "")
    return service.view(db, cart)


@router.patch("/items/{variant_id}")
def update_item(
    variant_id: int,
    data: QuantityIn,
    request: Request,
    response: Response,
    user: OptionalUser,
    db: DB,
) -> CartOut:
    raw = request.cookies.get(CART_COOKIE)
    cart = service.find(db, user, raw)
    if cart is None:
        raise AppError(404, "NOT_FOUND", "Panier introuvable.")
    service.set_quantity(db, cart, variant_id, data.quantity, add=False)
    db.commit()
    if user is None and raw:
        _remember(response, raw)
    return service.view(db, cart)


@router.delete("/items/{variant_id}")
def remove_item(variant_id: int, request: Request, user: OptionalUser, db: DB) -> CartOut:
    cart = service.find(db, user, request.cookies.get(CART_COOKIE))
    if cart is not None:
        service.remove(db, cart, variant_id)
        db.commit()
    return service.view(db, cart)
