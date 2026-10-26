"""Importe tous les modèles pour que Base.metadata soit complet (Alembic, tests)."""

from app.core.models import AuditLog, EmailMessage, RateLimitHit
from app.modules.auth.models import PasswordResetToken, User, UserSession
from app.modules.cart.models import Cart, CartItem
from app.modules.catalog.models import (
    Collection,
    OlfactoryFamily,
    Product,
    ProductImage,
    ProductVariant,
)
from app.modules.contact.models import ContactMessage
from app.modules.customers.models import Address
from app.modules.delivery.models import Commune
from app.modules.inventory.models import StockMovement
from app.modules.orders.models import Order, OrderEvent, OrderItem
from app.modules.payments.models import CashRemittance, Payment
from app.modules.settings.models import Setting

__all__ = [
    "Address",
    "AuditLog",
    "Cart",
    "CartItem",
    "CashRemittance",
    "Collection",
    "Commune",
    "ContactMessage",
    "EmailMessage",
    "OlfactoryFamily",
    "Order",
    "OrderEvent",
    "OrderItem",
    "PasswordResetToken",
    "Payment",
    "Product",
    "ProductImage",
    "ProductVariant",
    "RateLimitHit",
    "Setting",
    "StockMovement",
    "User",
    "UserSession",
]
