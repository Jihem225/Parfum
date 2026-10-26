from typing import Annotated

from pydantic import BaseModel, StringConstraints

from app.core.validators import PersonName, Phone
from app.modules.orders.schemas import AddressLine

Label = Annotated[str, StringConstraints(strip_whitespace=True, max_length=60)]
Landmark = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]


class ProfilePatch(BaseModel):
    full_name: PersonName | None = None
    phone: Phone | None = None


class AddressIn(BaseModel):
    label: Label = ""  # « Maison », « Bureau »…
    recipient_name: PersonName
    phone: Phone
    commune_id: int
    address_line: AddressLine
    landmark: Landmark = ""
    is_default: bool = False


class AddressPatch(BaseModel):
    label: Label | None = None
    recipient_name: PersonName | None = None
    phone: Phone | None = None
    commune_id: int | None = None
    address_line: AddressLine | None = None
    landmark: Landmark | None = None
    is_default: bool | None = None


class AddressOut(BaseModel):
    id: int
    label: str | None
    recipient_name: str
    phone: str
    commune_id: int
    commune_name: str
    commune_served: bool  # commune désactivée depuis : adresse inutilisable pour commander
    address_line: str
    landmark: str | None
    is_default: bool
