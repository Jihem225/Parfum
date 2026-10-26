"""Catalogue d'exemple (développement, tests E2E) : uv run python -m app.scripts.seed_demo

Noms, prix, stocks et communes sont FICTIFS. Refusé en production ; sans effet si des parfums
existent déjà."""

import io
import os
import sys
import uuid
from datetime import UTC, datetime

from PIL import Image, ImageDraw
from sqlalchemy import func, select

from app import models  # noqa: F401  (enregistre toutes les tables)
from app.core import security
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.storage import get_storage
from app.modules.auth.models import User, UserRole
from app.modules.auth.service import find_by_email
from app.modules.catalog.models import (
    Collection,
    Gender,
    OlfactoryFamily,
    Product,
    ProductImage,
    ProductStatus,
    ProductVariant,
)
from app.modules.delivery.models import Commune
from app.modules.inventory.models import MovementType, StockMovement
from app.modules.promotions.models import PromoCode, PromoKind

COLLECTIONS = [("Signatures", "signatures"), ("Bois & Épices", "bois-epices")]
FAMILIES = [
    ("Ambré", "ambre"),
    ("Floral", "floral"),
    ("Boisé", "boise"),
    ("Hespéridé", "hesperide"),
]
# nom, collection, famille, genre, (tête, cœur, fond), couleur du jus, [(ml, prix, stock)]
PRODUCTS = [
    (
        "Ambre Lagune",
        "signatures",
        "ambre",
        Gender.MIXTE,
        ("Bergamote, mandarine verte", "Fleur d'oranger, labdanum", "Ambre, vanille, santal"),
        (196, 138, 69),
        [(30, 25000, 12), (50, 38000, 8), (100, 61000, 3)],
    ),
    (
        "Néroli d'Assinie",
        "signatures",
        "hesperide",
        Gender.FEMME,
        ("Néroli, citron", "Jasmin, fleur de tiaré", "Musc blanc"),
        (214, 190, 120),
        [(30, 22000, 10), (50, 34000, 6)],
    ),
    (
        "Oud Cocody",
        "bois-epices",
        "boise",
        Gender.HOMME,
        ("Cardamome, poivre rose", "Oud, rose", "Cuir, patchouli"),
        (110, 72, 50),
        [(50, 45000, 4), (100, 72000, 0)],
    ),
    (
        "Vétiver Plateau",
        "bois-epices",
        "boise",
        Gender.MIXTE,
        ("Pamplemousse", "Vétiver, iris", "Cèdre, ambrette"),
        (120, 130, 95),
        [(50, 36000, 9)],
    ),
    (
        "Fleur de Bassam",
        "signatures",
        "floral",
        Gender.FEMME,
        ("Poire, litchi", "Tubéreuse, frangipanier", "Benjoin"),
        (225, 170, 160),
        [(30, 24000, 2), (50, 37000, 7)],
    ),
]
COMMUNES = [
    ("Cocody", 1500, "24 h"),
    ("Plateau", 1500, "24 h"),
    ("Marcory", 2000, "24 h"),
    ("Yopougon", 2500, "48 h"),
]


def bottle(color: tuple[int, int, int]) -> bytes:
    """Silhouette de flacon en attendant les vraies photos."""
    image = Image.new("RGB", (800, 1000), (250, 250, 248))
    draw = ImageDraw.Draw(image)
    draw.rectangle((340, 180, 460, 280), fill=(60, 52, 45))
    draw.rounded_rectangle((220, 280, 580, 820), radius=40, fill=color)
    out = io.BytesIO()
    image.save(out, "WEBP", quality=82)
    return out.getvalue()


def seed_test_staff() -> None:
    """Comptes de test des parcours E2E, seulement si SEED_STAFF_PASSWORD et
    SEED_MANAGER_TOTP_SECRET sont fournis (CI) : un Gestionnaire avec double authentification
    et un livreur."""
    password = os.environ.get("SEED_STAFF_PASSWORD")
    secret = os.environ.get("SEED_MANAGER_TOTP_SECRET")
    if not password or not secret:
        return
    with SessionLocal() as db:
        for email, name, role, totp in (
            ("gestion-e2e@exemple.com", "Gestion Test", UserRole.MANAGER, secret),
            ("livreur-e2e@exemple.com", "Livreur Test", UserRole.COURIER, None),
        ):
            if find_by_email(db, email):
                continue
            db.add(
                User(
                    email=email,
                    password_hash=security.hash_password(password),
                    full_name=name,
                    phone="0102030405",
                    role=role,
                    totp_secret=security.encrypt(totp) if totp else None,
                )
            )
        db.commit()
    print("Comptes de test E2E prêts (gestionnaire, livreur).")


def main() -> int:
    if settings.app_env == "production":
        print("Refusé : données d'exemple interdites en production.", file=sys.stderr)
        return 1
    seed_test_staff()
    storage = get_storage()
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Product)):
            print("Des parfums existent déjà : rien n'est ajouté.")
            return 0
        collections = {slug: Collection(name=n, slug=slug) for n, slug in COLLECTIONS}
        families = {slug: OlfactoryFamily(name=n, slug=slug) for n, slug in FAMILIES}
        db.add_all([*collections.values(), *families.values()])
        db.add_all(Commune(name=n, delivery_fee=f, delay_label=d) for n, f, d in COMMUNES)
        db.add(
            PromoCode(
                code="BIENVENUE10",
                kind=PromoKind.PERCENT,
                value=10,
                max_discount=5000,
                note="Exemple fictif",
            )
        )
        db.flush()
        for name, coll, fam, gender, notes, color, variants in PRODUCTS:
            slug = name.lower().replace("'", "-").replace(" ", "-").replace("é", "e")
            product = Product(
                name=name,
                slug=slug,
                collection_id=collections[coll].id,
                family_id=families[fam].id,
                gender=gender,
                top_notes=notes[0],
                heart_notes=notes[1],
                base_notes=notes[2],
                description="[Exemple] Description du parfum à rédiger.",
                status=ProductStatus.PUBLISHED,
                published_at=datetime.now(UTC),
            )
            db.add(product)
            db.flush()
            key = f"products/{product.id}/{uuid.uuid4().hex}.webp"
            storage.put(key, bottle(color), "image/webp")
            db.add(ProductImage(product_id=product.id, storage_key=key, alt_text=name, position=0))
            for ml, price, stock in variants:
                variant = ProductVariant(
                    product_id=product.id,
                    volume_ml=ml,
                    sku=f"{slug[:12].upper().strip('-')}-{ml:03d}",
                    price=price,
                    stock_physical=stock,
                )
                db.add(variant)
                db.flush()
                if stock:  # RG-11 : le stock ne bouge jamais sans mouvement
                    db.add(
                        StockMovement(
                            variant_id=variant.id,
                            type=MovementType.ENTREE,
                            delta_physical=stock,
                            reason="Données d'exemple",
                        )
                    )
        db.commit()
    print(
        f"Catalogue d'exemple créé : {len(PRODUCTS)} parfums, {len(COMMUNES)} communes, "
        "code promo BIENVENUE10 (fictifs)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
