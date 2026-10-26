import re
from typing import Annotated

from pydantic import AfterValidator, StringConstraints


def normalize_ci_phone(value: str) -> str:
    """« +225 07 08 12 34 56 » → « 0708123456 ». Plan à 10 chiffres (2021) : mobiles en 0…,
    fixes en 2… (27 22 …)."""
    digits = re.sub(r"^(\+|00)225", "", re.sub(r"[\s.\-()]", "", value))
    if not re.fullmatch(r"[02]\d{9}", digits):
        raise ValueError(
            "Numéro ivoirien attendu : 10 chiffres, par exemple 07 08 12 34 56 ou 27 22 00 00 00."
        )
    return digits


def normalize_email(value: str) -> str:
    return value.strip().lower()


Phone = Annotated[str, StringConstraints(max_length=30), AfterValidator(normalize_ci_phone)]
Password = Annotated[str, StringConstraints(min_length=10, max_length=128)]
PersonName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
