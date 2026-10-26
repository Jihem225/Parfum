"""Les règles critiques sont garanties par la base elle-même, même si le code se trompe."""

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Address,
    Cart,
    CartItem,
    CashRemittance,
    Collection,
    Commune,
    OlfactoryFamily,
    Order,
    OrderItem,
    Product,
    ProductVariant,
    User,
)
from app.modules.auth.models import UserRole
from app.modules.catalog.models import Gender


def make_user(db: Session, email: str = "aya@exemple.com", **kw: Any) -> User:
    user = User(
        email=email,
        password_hash="pas-un-vrai-hash",  # noqa: S106
        full_name="Aya K.",
        phone="0708123456",
        **kw,
    )
    db.add(user)
    db.flush()
    return user


def make_variant(db: Session, sku: str = "AMB-LAG-050", **kw: Any) -> ProductVariant:
    collection = Collection(name="Signatures", slug=f"signatures-{sku}")
    family = OlfactoryFamily(name="Ambré", slug=f"ambre-{sku}")
    db.add_all([collection, family])
    db.flush()
    product = Product(
        name="Ambre Lagune",
        slug=f"ambre-lagune-{sku}",
        collection_id=collection.id,
        family_id=family.id,
        gender=Gender.MIXTE,
    )
    db.add(product)
    db.flush()
    values: dict[str, Any] = {"volume_ml": 50, "price": 38000, "stock_physical": 10} | kw
    variant = ProductVariant(product_id=product.id, sku=sku, **values)
    db.add(variant)
    db.flush()
    return variant


def make_order(db: Session, **kw: Any) -> Order:
    values: dict[str, Any] = {
        "number": "PP-10001",
        "idempotency_key": "cle-1",
        "customer_name": "Aya K.",
        "phone": "0708123456",
        "commune_name": "Cocody",
        "address_line": "Riviera 3",
        "delivery_fee": 1500,
        "delivery_delay_label": "24 h",
        "subtotal": 38000,
        "total": 39500,
    } | kw
    order = Order(**values)
    db.add(order)
    db.flush()
    return order


def test_reservation_cannot_exceed_physical_stock(db: Session) -> None:
    variant = make_variant(db, stock_physical=3)
    variant.stock_reserved = 4
    with pytest.raises(IntegrityError, match="reserved_within_physical"):
        db.flush()


def test_reserved_stock_cannot_be_negative(db: Session) -> None:
    variant = make_variant(db)
    variant.stock_reserved = -1
    with pytest.raises(IntegrityError, match="reserved_positive"):
        db.flush()


def test_price_must_be_positive(db: Session) -> None:
    with pytest.raises(IntegrityError, match="price_positive"):
        make_variant(db, price=0)


def test_sku_is_unique(db: Session) -> None:
    first = make_variant(db, sku="AMB-LAG-050", volume_ml=50)
    db.add(ProductVariant(product_id=first.product_id, sku="AMB-LAG-050", volume_ml=100, price=1))
    with pytest.raises(IntegrityError, match="uq_product_variants_sku"):
        db.flush()


def test_email_is_unique_regardless_of_case(db: Session) -> None:
    make_user(db, email="aya@exemple.com")
    with pytest.raises(IntegrityError, match="uq_users_email_lower"):
        make_user(db, email="AYA@Exemple.com")


def test_order_total_must_equal_subtotal_plus_delivery_fee(db: Session) -> None:
    with pytest.raises(IntegrityError, match="total_consistent"):
        make_order(db, subtotal=38000, delivery_fee=1500, total=38000)


def test_order_line_total_must_match_price_times_quantity(db: Session) -> None:
    variant = make_variant(db)
    order = make_order(db)
    db.add(
        OrderItem(
            order_id=order.id,
            variant_id=variant.id,
            product_name="Ambre Lagune",
            volume_ml=50,
            sku=variant.sku,
            unit_price=38000,
            quantity=2,
            line_total=38000,
        )
    )
    with pytest.raises(IntegrityError, match="line_total_consistent"):
        db.flush()


def test_ordered_variant_cannot_be_deleted(db: Session) -> None:
    """RG-04 : l'historique commercial survit ; on archive au lieu de supprimer."""
    variant = make_variant(db)
    order = make_order(db)
    db.add(
        OrderItem(
            order_id=order.id,
            variant_id=variant.id,
            product_name="Ambre Lagune",
            volume_ml=50,
            sku=variant.sku,
            unit_price=38000,
            quantity=1,
            line_total=38000,
        )
    )
    db.flush()
    with pytest.raises(IntegrityError, match="fk_order_items_variant_id_product_variants"):
        db.execute(text("DELETE FROM product_variants WHERE id = :id"), {"id": variant.id})


def test_only_one_default_address_per_user(db: Session) -> None:
    user = make_user(db)
    commune = Commune(name="Cocody", delivery_fee=1500, delay_label="24 h")
    db.add(commune)
    db.flush()
    for label in ("Maison", "Bureau"):
        db.add(
            Address(
                user_id=user.id,
                label=label,
                recipient_name="Aya K.",
                phone="0708123456",
                commune_id=commune.id,
                address_line="Riviera 3",
                is_default=True,
            )
        )
    with pytest.raises(IntegrityError, match="uq_addresses_default_per_user"):
        db.flush()


def test_cart_quantity_is_limited_to_five(db: Session) -> None:
    variant = make_variant(db)
    cart = Cart(token_hash="a" * 64)
    db.add(cart)
    db.flush()
    db.add(CartItem(cart_id=cart.id, variant_id=variant.id, quantity=6))
    with pytest.raises(IntegrityError, match="quantity_range"):
        db.flush()


def test_cash_remittance_difference_is_consistent(db: Session) -> None:
    courier = make_user(db, email="koffi@exemple.com", role=UserRole.COURIER)
    manager = make_user(db, email="awa@exemple.com", role=UserRole.MANAGER)
    db.add(
        CashRemittance(
            courier_id=courier.id,
            received_by=manager.id,
            expected_amount=141500,
            received_amount=139500,
            difference=0,
        )
    )
    with pytest.raises(IntegrityError, match="difference_consistent"):
        db.flush()


def test_unknown_status_is_rejected_by_the_database(db: Session) -> None:
    with pytest.raises(IntegrityError, match="ck_contact_messages_messagestatus"):
        db.execute(
            text("INSERT INTO contact_messages (name, message, status) VALUES ('A', 'B', 'X')")
        )


def test_order_numbers_start_at_10001(db: Session) -> None:
    assert db.execute(text("SELECT nextval('order_number_seq')")).scalar_one() >= 10001
