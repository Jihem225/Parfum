"""Informations de la boutique (F-47) : affichées sur le site, modifiables par le Propriétaire."""

from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, StringConstraints
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.validators import Phone
from app.modules.auth.deps import DB, Owner
from app.modules.auth.schemas import Email
from app.modules.settings.models import Setting

public = APIRouter(tags=["boutique"])
admin = APIRouter(prefix="/admin/settings", tags=["admin: paramètres"])

SHOP_KEY = "shop"


class ShopInfo(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)] = (
        "Projet Parfums"  # nom provisoire
    )
    phone: Phone | None = None
    whatsapp: Phone | None = None
    email: Email | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] = ""
    opening_hours: Annotated[str, StringConstraints(strip_whitespace=True, max_length=120)] = ""


def _shop(db: Session) -> ShopInfo:
    row = db.get(Setting, SHOP_KEY)
    return ShopInfo.model_validate(row.value) if row else ShopInfo()


@public.get("/shop")
def shop_info(db: DB) -> ShopInfo:
    return _shop(db)


@admin.put("/shop")
def update_shop_info(data: ShopInfo, user: Owner, db: DB) -> ShopInfo:
    before = _shop(db).model_dump(mode="json")
    after = data.model_dump(mode="json")
    row = db.get(Setting, SHOP_KEY)
    if row is None:
        db.add(Setting(key=SHOP_KEY, value=after))
    else:
        row.value = after
    audit(
        db,
        actor_id=user.id,
        action="settings.shop",
        entity_type="settings",
        entity_id=SHOP_KEY,
        before=before,
        after=after,
    )
    db.commit()
    return data
