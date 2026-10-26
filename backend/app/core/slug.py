import re
import unicodedata
from typing import Annotated

from pydantic import StringConstraints


def slugify(value: str) -> str:
    """« Bois & Épices » → « bois-epices » : adresses lisibles et stables (RG-05)."""
    ascii_text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")


Slug = Annotated[
    str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", min_length=1, max_length=140)
]
