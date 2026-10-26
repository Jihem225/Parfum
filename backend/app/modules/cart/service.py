"""Panier : il ne réserve pas de stock (RG-21) ; prix et disponibilités sont relus à chaque
affichage et revérifiés à la commande."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core import security
from app.core.errors import AppError
from app.modules.auth.models import User
from app.modules.cart.models import Cart, CartItem
from app.modules.cart.schemas import CartLine, CartOut
from app.modules.catalog.models import Product, ProductImage, ProductStatus, ProductVariant
from app.modules.catalog.products import image_out

MAX_QUANTITY = 5  # RG-22 : par contenance et par commande
MAX_LINES = 20  # garde-fou contre les paniers géants
COD_LIMIT = 300_000  # RG-23 : plafond d'une commande payée à la livraison (FCFA)
GUEST_TTL = timedelta(days=90)


def find(db: Session, user: User | None, raw_token: str | None) -> Cart | None:
    """Panier du compte si connecté, sinon celui du cookie visiteur. Verrouillé : les
    modifications d'un même panier s'exécutent l'une après l'autre (double clic)."""
    if user is not None:
        where = Cart.user_id == user.id
    elif raw_token:
        where = Cart.token_hash == security.sha256(raw_token)
    else:
        return None
    return db.scalar(select(Cart).where(where).with_for_update())


def get_or_create(db: Session, user: User | None, raw_token: str | None) -> tuple[Cart, str | None]:
    """Renvoie le panier et, pour un nouveau panier visiteur, le jeton à poser en cookie."""
    if user is not None:
        db.execute(insert(Cart).values(user_id=user.id).on_conflict_do_nothing())
    cart = find(db, user, raw_token)
    if cart is not None:
        return cart, None
    raw, digest = security.new_token()
    cart = Cart(token_hash=digest)
    db.add(cart)
    db.flush()
    return cart, raw


def _sellable(db: Session, variant_id: int) -> ProductVariant:
    row = db.execute(
        select(ProductVariant, Product.status).join(Product).where(ProductVariant.id == variant_id)
    ).first()
    if row is None or not row[0].is_active or row[1] != ProductStatus.PUBLISHED:
        raise AppError(409, "UNAVAILABLE", "Ce parfum n'est plus disponible.")
    return row[0]


def set_quantity(db: Session, cart: Cart, variant_id: int, quantity: int, *, add: bool) -> None:
    variant = _sellable(db, variant_id)
    item = db.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id)
    )
    if item is None:
        lines = db.scalar(select(func.count()).where(CartItem.cart_id == cart.id)) or 0
        if lines >= MAX_LINES:
            raise AppError(409, "CART_FULL", f"Le panier est limité à {MAX_LINES} articles.")
    total = quantity + (item.quantity if item is not None and add else 0)
    if total > MAX_QUANTITY:
        raise AppError(
            409,
            "MAX_QUANTITY",
            f"{MAX_QUANTITY} unités maximum par contenance.",
            {"max_quantity": MAX_QUANTITY},
        )
    available = variant.stock_physical - variant.stock_reserved
    if total > available:
        raise AppError(
            409,
            "INSUFFICIENT_STOCK",
            "Quantité indisponible." if available > 0 else "Ce parfum est en rupture de stock.",
            {"max_quantity": max(available, 0)},
        )
    if item is None:
        db.add(CartItem(cart_id=cart.id, variant_id=variant_id, quantity=total))
    else:
        item.quantity = total
    cart.updated_at = datetime.now(UTC)


def remove(db: Session, cart: Cart, variant_id: int) -> None:
    db.execute(
        delete(CartItem).where(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id)
    )
    cart.updated_at = datetime.now(UTC)


def merge(db: Session, raw_token: str | None, user: User) -> None:
    """À la connexion, le panier visiteur rejoint celui du compte (RG-20). Les quantités
    s'additionnent dans la limite de 5 ; le stock sera revérifié à la commande."""
    guest = find(db, None, raw_token)
    if guest is None or guest.user_id is not None:
        return
    account = find(db, user, None)
    if account is None:
        guest.user_id, guest.token_hash = user.id, None
        return
    existing = {
        i.variant_id: i for i in db.scalars(select(CartItem).where(CartItem.cart_id == account.id))
    }
    for item in db.scalars(select(CartItem).where(CartItem.cart_id == guest.id)):
        if item.variant_id in existing:
            mine = existing[item.variant_id]
            mine.quantity = min(MAX_QUANTITY, mine.quantity + item.quantity)
        elif len(existing) < MAX_LINES:
            existing[item.variant_id] = CartItem(
                cart_id=account.id, variant_id=item.variant_id, quantity=item.quantity
            )
            db.add(existing[item.variant_id])
    db.delete(guest)
    account.updated_at = datetime.now(UTC)


def view(db: Session, cart: Cart | None) -> CartOut:
    rows = (
        db.execute(
            select(CartItem, ProductVariant, Product)
            .join(ProductVariant, ProductVariant.id == CartItem.variant_id)
            .join(Product)
            .where(CartItem.cart_id == cart.id)
            .order_by(CartItem.id)
        ).all()
        if cart is not None
        else []
    )
    first_images: dict[int, ProductImage] = {}
    for img in db.scalars(
        select(ProductImage)
        .where(ProductImage.product_id.in_({p.id for _, _, p in rows}))
        .order_by(ProductImage.position)
    ):
        first_images.setdefault(img.product_id, img)

    lines = []
    for item, variant, product in rows:
        available = max(variant.stock_physical - variant.stock_reserved, 0)
        sellable = variant.is_active and product.status == ProductStatus.PUBLISHED
        image = first_images.get(product.id)
        lines.append(
            CartLine(
                variant_id=variant.id,
                product_name=product.name,
                product_slug=product.slug,
                volume_ml=variant.volume_ml,
                sku=variant.sku,
                unit_price=variant.price,
                quantity=item.quantity,
                line_total=variant.price * item.quantity,
                max_quantity=min(MAX_QUANTITY, available) if sellable else 0,
                image=image_out(image) if image else None,
                issue=None
                if sellable and item.quantity <= available
                else ("INSUFFICIENT_STOCK" if sellable else "UNAVAILABLE"),
            )
        )
    subtotal = sum(line.line_total for line in lines if line.issue != "UNAVAILABLE")
    return CartOut(
        items=lines,
        item_count=sum(line.quantity for line in lines),
        subtotal=subtotal,
        exceeds_cod_limit=subtotal > COD_LIMIT,
        can_checkout=bool(lines)
        and subtotal <= COD_LIMIT
        and all(line.issue is None for line in lines),
    )
