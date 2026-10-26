"""Prestataires de mobile money, derrière deux opérations : ouvrir la page de paiement hébergée et
lire un avis de paiement signé. Le prestataire réel n'est pas encore choisi : seule la simulation
existe (développement, CI), refusée en production par la configuration."""

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlencode

from app.core.config import settings
from app.core.errors import AppError


@dataclass(frozen=True)
class Notification:
    order_number: str
    amount: int
    paid: bool
    provider_ref: str


class Provider(Protocol):
    def checkout_url(self, order_number: str, amount: int, return_url: str) -> str: ...

    def read(self, body: bytes, headers: Mapping[str, str]) -> Notification:
        """Vérifie la signature sur les octets reçus, puis décode ; AppError 401 sinon."""
        ...


def sign(body: bytes) -> str:
    return hmac.new(settings.payment_webhook_secret.encode(), body, hashlib.sha256).hexdigest()


class Simulation:
    """Page de paiement factice du frontend (« aucun argent réel ») ; avis signés en HMAC-SHA256
    avec PAYMENT_WEBHOOK_SECRET, comme le font les vrais prestataires."""

    def checkout_url(self, order_number: str, amount: int, return_url: str) -> str:
        query = urlencode({"numero": order_number, "montant": amount, "retour": return_url})
        return f"{settings.frontend_origin}/paiement/simulation?{query}"

    def read(self, body: bytes, headers: Mapping[str, str]) -> Notification:
        signature = headers.get("x-signature", "")
        if not settings.payment_webhook_secret or not hmac.compare_digest(sign(body), signature):
            raise AppError(401, "BAD_SIGNATURE", "Signature de l'avis de paiement invalide.")
        data = json.loads(body)
        return Notification(
            order_number=str(data["order_number"]),
            amount=int(data["amount"]),
            paid=data["status"] == "paid",
            provider_ref=str(data["id"]),
        )


def get_provider() -> Provider | None:
    return Simulation() if settings.payment_provider == "simulation" else None
