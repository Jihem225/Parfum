import io
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.models import AuditLog
from app.modules.catalog.models import ProductVariant

ADMIN = "/api/v1/admin"
SHOP = "/api/v1/catalog"


def png(width: int = 800, height: int = 1000, **save: Any) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (196, 138, 69)).save(out, "PNG", **save)
    return out.getvalue()


@pytest.fixture
def taxons(manager: TestClient) -> dict[str, int]:
    return {
        "signatures": manager.post(f"{ADMIN}/collections", json={"name": "Signatures"}).json()[
            "id"
        ],
        "bois": manager.post(f"{ADMIN}/collections", json={"name": "Bois & Épices"}).json()["id"],
        "ambre": manager.post(f"{ADMIN}/families", json={"name": "Ambré"}).json()["id"],
        "floral": manager.post(f"{ADMIN}/families", json={"name": "Floral"}).json()["id"],
    }


def make_product(
    manager: TestClient,
    taxons: dict[str, int],
    name: str,
    *,
    collection: str = "signatures",
    family: str = "ambre",
    gender: str = "MIXTE",
    variants: tuple[tuple[int, int], ...] = ((50, 38000),),
    publish: bool = True,
    **fields: Any,
) -> dict[str, Any]:
    product = manager.post(
        f"{ADMIN}/products",
        json={
            "name": name,
            "collection_id": taxons[collection],
            "family_id": taxons[family],
            "gender": gender,
            **fields,
        },
    ).json()
    for volume, price in variants:
        sku = f"{product['slug'][:20].upper()}-{volume}"
        r = manager.post(
            f"{ADMIN}/products/{product['id']}/variants",
            json={"volume_ml": volume, "sku": sku, "price": price},
        )
        assert r.status_code == 201, r.json()
    upload = manager.post(
        f"{ADMIN}/products/{product['id']}/images",
        files={"file": ("flacon.png", png(), "image/png")},
    )
    assert upload.status_code == 201, upload.json()
    if publish:
        assert manager.post(f"{ADMIN}/products/{product['id']}/publish").status_code == 200
    result: dict[str, Any] = manager.get(f"{ADMIN}/products/{product['id']}").json()
    return result


def set_stock(db: Session, product: dict[str, Any], physical: int, reserved: int = 0) -> None:
    for v in product["variants"]:
        db.execute(
            update(ProductVariant)
            .where(ProductVariant.id == v["id"])
            .values(stock_physical=physical, stock_reserved=reserved)
        )


# --- Back-office ---------------------------------------------------------------------------------


def test_new_product_is_a_draft_with_a_readable_slug(
    manager: TestClient, taxons: dict[str, int]
) -> None:
    response = manager.post(
        f"{ADMIN}/products",
        json={
            "name": "Néroli d'Assinie",
            "collection_id": taxons["signatures"],
            "family_id": taxons["ambre"],
            "gender": "MIXTE",
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "DRAFT"
    assert response.json()["slug"] == "neroli-d-assinie"


def test_unknown_collection_is_refused(manager: TestClient, taxons: dict[str, int]) -> None:
    response = manager.post(
        f"{ADMIN}/products",
        json={
            "name": "X Y",
            "collection_id": 999999,
            "family_id": taxons["ambre"],
            "gender": "MIXTE",
        },
    )
    assert response.json()["error"]["code"] == "UNKNOWN_COLLECTION"


def test_publication_requires_a_variant_and_an_image(
    manager: TestClient, taxons: dict[str, int]
) -> None:
    product = manager.post(
        f"{ADMIN}/products",
        json={
            "name": "Ambre Lagune",
            "collection_id": taxons["signatures"],
            "family_id": taxons["ambre"],
            "gender": "MIXTE",
        },
    ).json()
    refused = manager.post(f"{ADMIN}/products/{product['id']}/publish")
    assert refused.status_code == 409
    error = refused.json()["error"]
    assert error["code"] == "NOT_PUBLISHABLE" and len(error["details"]) == 2


def test_sku_is_normalized_and_unique(manager: TestClient, taxons: dict[str, int]) -> None:
    product = make_product(manager, taxons, "Ambre Lagune", publish=False, variants=())
    created = manager.post(
        f"{ADMIN}/products/{product['id']}/variants",
        json={"volume_ml": 30, "sku": " amb-lag-030 ", "price": 25000},
    )
    assert created.json()["variants"][0]["sku"] == "AMB-LAG-030"
    duplicate = manager.post(
        f"{ADMIN}/products/{product['id']}/variants",
        json={"volume_ml": 50, "sku": "AMB-LAG-030", "price": 38000},
    )
    assert duplicate.json()["error"]["code"] == "SKU_TAKEN"
    same_volume = manager.post(
        f"{ADMIN}/products/{product['id']}/variants",
        json={"volume_ml": 30, "sku": "AMB-LAG-031", "price": 25000},
    )
    assert same_volume.json()["error"]["code"] == "VOLUME_TAKEN"


def test_price_change_is_audited(manager: TestClient, taxons: dict[str, int], db: Session) -> None:
    product = make_product(manager, taxons, "Ambre Lagune")
    variant_id = product["variants"][0]["id"]
    manager.patch(f"{ADMIN}/variants/{variant_id}", json={"price": 40000})
    log = db.scalar(select(AuditLog).where(AuditLog.action == "variant.update"))
    assert log is not None and log.before is not None and log.after is not None
    assert (log.before["price"], log.after["price"]) == (38000, 40000)


def test_image_is_checked_and_converted_to_webp(
    manager: TestClient, taxons: dict[str, int]
) -> None:
    product = make_product(manager, taxons, "Ambre Lagune", publish=False)
    fake = manager.post(
        f"{ADMIN}/products/{product['id']}/images",
        files={"file": ("photo.jpg", b"ceci n'est pas une image", "image/jpeg")},
    )
    assert fake.json()["error"]["code"] == "INVALID_IMAGE"
    for other in ("GIF", "TIFF"):  # vraies images, mais décodeurs exclus (failles de Pillow)
        buffer = io.BytesIO()
        Image.new("RGB", (10, 10)).save(buffer, other)
        refused = manager.post(
            f"{ADMIN}/products/{product['id']}/images",
            files={"file": ("photo.jpg", buffer.getvalue(), "image/jpeg")},
        )
        assert refused.json()["error"]["code"] == "INVALID_IMAGE"

    exif = Image.Exif()
    exif[0x010F] = "Appareil secret"  # fabricant : métadonnée à supprimer
    big = manager.post(
        f"{ADMIN}/products/{product['id']}/images",
        files={"file": ("grande.png", png(3000, 1000, exif=exif), "image/png")},
    )
    assert big.status_code == 201
    stored = Path(settings.media_dir) / big.json()["url"].removeprefix(
        settings.media_base_url + "/"
    )
    with Image.open(stored) as img:
        assert img.format == "WEBP"
        assert img.size == (2000, 667)
        assert not img.getexif()


def test_too_large_upload_is_refused(manager: TestClient, taxons: dict[str, int]) -> None:
    product = make_product(manager, taxons, "Ambre Lagune", publish=False)
    response = manager.post(
        f"{ADMIN}/products/{product['id']}/images",
        files={"file": ("lourd.png", b"0" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413


def test_images_can_be_reordered(manager: TestClient, taxons: dict[str, int]) -> None:
    product = make_product(manager, taxons, "Ambre Lagune", publish=False)
    second = manager.post(
        f"{ADMIN}/products/{product['id']}/images", files={"file": ("b.png", png(), "image/png")}
    ).json()
    first_id = product["images"][0]["id"]
    reordered = manager.put(
        f"{ADMIN}/products/{product['id']}/images/order",
        json={"image_ids": [second["id"], first_id]},
    ).json()
    assert [i["id"] for i in reordered["images"]] == [second["id"], first_id]
    incomplete = manager.put(
        f"{ADMIN}/products/{product['id']}/images/order", json={"image_ids": [first_id]}
    )
    assert incomplete.json()["error"]["code"] == "INVALID_ORDER"


def test_product_without_history_can_be_deleted_with_its_files(
    manager: TestClient, taxons: dict[str, int]
) -> None:
    product = make_product(manager, taxons, "Ambre Lagune", publish=False)
    stored = Path(settings.media_dir) / product["images"][0]["url"].removeprefix(
        settings.media_base_url + "/"
    )
    assert stored.exists()
    assert manager.delete(f"{ADMIN}/products/{product['id']}").status_code == 204
    assert not stored.exists()


def test_product_with_stock_history_must_be_archived(
    manager: TestClient, taxons: dict[str, int], db: Session
) -> None:
    from app.modules.inventory.models import MovementType, StockMovement

    product = make_product(manager, taxons, "Ambre Lagune")
    db.add(
        StockMovement(
            variant_id=product["variants"][0]["id"], type=MovementType.ENTREE, delta_physical=10
        )
    )
    db.flush()
    refused = manager.delete(f"{ADMIN}/products/{product['id']}")
    assert refused.json()["error"]["code"] == "HAS_HISTORY"
    archived = manager.post(f"{ADMIN}/products/{product['id']}/archive").json()
    assert archived["status"] == "ARCHIVED"
    assert manager.get(f"{SHOP}/products/ambre-lagune").status_code == 404


def test_customers_cannot_manage_products(client: TestClient) -> None:
    assert client.post(f"{ADMIN}/products", json={}).status_code == 401


# --- Boutique ------------------------------------------------------------------------------------


@pytest.fixture
def shop(manager: TestClient, taxons: dict[str, int], db: Session) -> dict[str, dict[str, Any]]:
    items = {
        "ambre": make_product(
            manager,
            taxons,
            "Ambre Lagune",
            top_notes="Bergamote",
            base_notes="Vanille",
            variants=((30, 25000), (50, 38000), (100, 55000)),
        ),
        "neroli": make_product(
            manager,
            taxons,
            "Néroli d'Assinie",
            family="floral",
            variants=((30, 22000), (50, 34000)),
        ),
        "oud": make_product(
            manager,
            taxons,
            "Oud Cocody",
            collection="bois",
            gender="HOMME",
            variants=((50, 46000),),
        ),
        "brouillon": make_product(manager, taxons, "Brouillon Secret", publish=False),
    }
    set_stock(db, items["ambre"], physical=20)
    set_stock(db, items["neroli"], physical=2)  # 2 contenances × 2 = 4 : « Plus que 4 »
    set_stock(db, items["oud"], physical=2, reserved=2)  # tout est réservé : rupture
    return items


def names(response: Any) -> list[str]:
    return [p["name"] for p in response.json()["items"]]


def test_shop_lists_only_published_products(manager: TestClient, shop: dict[str, Any]) -> None:
    body = manager.get(f"{SHOP}/products").json()
    assert body["total"] == 3
    assert "Brouillon Secret" not in names(manager.get(f"{SHOP}/products"))


def test_search_ignores_accents_and_case(manager: TestClient, shop: dict[str, Any]) -> None:
    assert names(manager.get(f"{SHOP}/products", params={"q": "neroli"})) == ["Néroli d'Assinie"]
    assert names(manager.get(f"{SHOP}/products", params={"q": "VANILLE"})) == ["Ambre Lagune"]
    assert names(manager.get(f"{SHOP}/products", params={"q": "100%"})) == []  # joker échappé


def test_filters(manager: TestClient, shop: dict[str, Any]) -> None:
    def get(**params: Any) -> list[str]:
        return sorted(names(manager.get(f"{SHOP}/products", params=params)))

    assert get(gender="HOMME") == ["Oud Cocody"]
    assert get(collection="bois-epices") == ["Oud Cocody"]
    assert get(family="floral") == ["Néroli d'Assinie"]
    assert get(volume=100) == ["Ambre Lagune"]
    assert get(in_stock="true") == ["Ambre Lagune", "Néroli d'Assinie"]
    # Prix ET contenance sur la même contenance : 100 ml à moins de 50 000 n'existe pas.
    assert get(volume=100, max_price=50000) == []
    assert get(min_price=40000) == ["Ambre Lagune", "Oud Cocody"]


def test_sorting_and_pagination(manager: TestClient, shop: dict[str, Any]) -> None:
    by_price = names(manager.get(f"{SHOP}/products", params={"sort": "prix_croissant"}))
    assert by_price == ["Néroli d'Assinie", "Ambre Lagune", "Oud Cocody"]
    page2 = manager.get(
        f"{SHOP}/products", params={"sort": "prix_croissant", "page": 2, "page_size": 2}
    )
    assert names(page2) == ["Oud Cocody"] and page2.json()["total"] == 3


def test_cards_show_stock_status(manager: TestClient, shop: dict[str, Any]) -> None:
    cards = {p["name"]: p for p in manager.get(f"{SHOP}/products").json()["items"]}
    assert cards["Ambre Lagune"]["stock_status"] == "IN_STOCK"
    assert cards["Ambre Lagune"]["min_price"] == 25000 and cards["Ambre Lagune"]["volumes"] == [
        30,
        50,
        100,
    ]
    assert (
        cards["Néroli d'Assinie"]["stock_status"],
        cards["Néroli d'Assinie"]["low_stock_count"],
    ) == ("LOW", 4)
    assert cards["Oud Cocody"]["stock_status"] == "OUT"
    assert cards["Ambre Lagune"]["image"]["url"].endswith(".webp")


def test_product_page(manager: TestClient, shop: dict[str, Any]) -> None:
    detail = manager.get(f"{SHOP}/products/ambre-lagune").json()
    assert [v["volume_ml"] for v in detail["variants"]] == [30, 50, 100]
    assert detail["collection"] == {"name": "Signatures", "slug": "signatures"}
    assert detail["top_notes"] == "Bergamote"
    assert manager.get(f"{SHOP}/products/brouillon-secret").status_code == 404


def test_inactive_variant_is_hidden(manager: TestClient, shop: dict[str, Any]) -> None:
    variant_100 = shop["ambre"]["variants"][2]["id"]
    manager.patch(f"{ADMIN}/variants/{variant_100}", json={"is_active": False})
    detail = manager.get(f"{SHOP}/products/ambre-lagune").json()
    assert [v["volume_ml"] for v in detail["variants"]] == [30, 50]


def test_similar_products_share_the_family(
    manager: TestClient, taxons: dict[str, int], shop: dict[str, Any]
) -> None:
    make_product(manager, taxons, "Ambre Nuit", family="ambre")
    similar = manager.get(f"{SHOP}/products/ambre-lagune").json()["similar"]
    # Même famille (Ambré), le parfum lui-même exclu ; le plus récent d'abord à popularité égale.
    assert [p["name"] for p in similar] == ["Ambre Nuit", "Oud Cocody"]
