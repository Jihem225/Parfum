from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints

CommuneName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=80)]
Fee = Annotated[int, Field(ge=0, le=100_000)]
DelayLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=60)]


class CommuneIn(BaseModel):
    name: CommuneName
    delivery_fee: Fee
    delay_label: DelayLabel  # ex. « 24 h »
    is_active: bool = True
    position: Annotated[int, Field(ge=0, le=10_000)] = 0


class CommunePatch(BaseModel):
    name: CommuneName | None = None
    delivery_fee: Fee | None = None
    delay_label: DelayLabel | None = None
    is_active: bool | None = None
    position: Annotated[int, Field(ge=0, le=10_000)] | None = None


class CommuneOut(BaseModel):
    id: int
    name: str
    delivery_fee: int
    delay_label: str
    is_active: bool
    position: int
