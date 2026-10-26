"""Application d'un code promo (étape 13, RG-80 à RG-86) : vérifié au récapitulatif, puis de
nouveau à la validation, code verrouillé pour que deux commandes simultanées ne dépassent pas
ses limites."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.notify import fcfa
from app.modules.promotions.models import PromoCode, PromoKind


def normalize(code: str) -> str:
    return code.strip().upper()


def uses(db: Session, promo_id: int, phone: str | None = None) -> int:
    """Commandes non annulées portant le code (RG-84 : une annulation le rend)."""
    query = select(func.count()).where(
        Order.promo_code_id == promo_id, Order.status != OrderStatus.ANNULEE
    )
    if phone is not None:
        query = query.where(Order.phone == phone)
    return db.scalar(query) or 0


def discount_for(promo: PromoCode, subtotal: int) -> int:
    if promo.kind == PromoKind.PERCENT:
        amount = subtotal * promo.value // 100  # arrondi à l'inférieur : FCFA entiers
        if promo.max_discount is not None:
            amount = min(amount, promo.max_discount)
    else:
        amount = promo.value
    return min(amount, subtotal)


def apply(
    db: Session, code: str, subtotal: int, phone: str | None, *, lock: bool = False
) -> tuple[PromoCode, int]:
    """Renvoie (code, réduction) ; AppError 422 avec un motif lisible sinon. `phone` déjà
    normalisé, ou None tant que le client ne l'a pas saisi (vérifié à la validation)."""
    query = select(PromoCode).where(PromoCode.code == normalize(code))
    promo = db.scalar(query.with_for_update() if lock else query)
    now = datetime.now(UTC)
    if (
        promo is None
        or not promo.is_active
        or (promo.starts_at is not None and now < promo.starts_at)
        or (promo.ends_at is not None and now >= promo.ends_at)
    ):
        raise AppError(422, "PROMO_INVALID", "Ce code promo n'est pas valable.")
    if promo.min_subtotal is not None and subtotal < promo.min_subtotal:
        raise AppError(
            422,
            "PROMO_MINIMUM",
            f"Ce code est valable à partir de {fcfa(promo.min_subtotal)} d'articles.",
        )
    if promo.max_uses is not None and uses(db, promo.id) >= promo.max_uses:
        raise AppError(422, "PROMO_EXHAUSTED", "Ce code promo a déjà été entièrement utilisé.")
    if phone is not None and uses(db, promo.id, phone):
        raise AppError(
            422, "PROMO_ALREADY_USED", "Ce code promo a déjà été utilisé avec ce numéro."
        )
    return promo, discount_for(promo, subtotal)
