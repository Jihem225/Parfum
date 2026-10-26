from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

from app.core.slug import Slug

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
Description = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Position = Annotated[int, Field(ge=0, le=10_000)]


class CollectionIn(BaseModel):
    name: Name
    slug: Slug | None = None  # déduit du nom si absent
    description: Description | None = None
    position: Position = 0
    is_active: bool = True


class CollectionPatch(BaseModel):
    name: Name | None = None
    slug: Slug | None = None
    description: Description | None = None
    position: Position | None = None
    is_active: bool | None = None


class CollectionOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    position: int
    is_active: bool
    product_count: int  # parfums publiés


class FamilyIn(BaseModel):
    name: Name
    slug: Slug | None = None
    position: Position = 0


class FamilyPatch(BaseModel):
    name: Name | None = None
    slug: Slug | None = None
    position: Position | None = None


class FamilyOut(BaseModel):
    id: int
    name: str
    slug: str
    position: int
    product_count: int  # parfums publiés
