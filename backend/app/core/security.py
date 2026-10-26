import base64
import hashlib
import secrets

import pyotp
from cryptography.fernet import Fernet
from pwdlib import PasswordHash

from app.core.config import settings

_hasher = PasswordHash.recommended()  # Argon2id
# Vérifié quand l'e-mail est inconnu : même durée de réponse, pas d'énumération des comptes.
_DUMMY_HASH = _hasher.hash("mot-de-passe-factice-pour-le-temps-constant")

_fernet = Fernet(base64.urlsafe_b64encode(hashlib.sha256(settings.secret_key.encode()).digest()))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def burn_password_check(password: str) -> None:
    _hasher.verify(password, _DUMMY_HASH)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> tuple[str, str]:
    """Jeton aléatoire : la valeur brute part chez le client, seule l'empreinte est stockée."""
    raw = secrets.token_urlsafe(32)
    return raw, sha256(raw)


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()


def new_totp_secret() -> str:
    return pyotp.random_base32()


def totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name="Projet Parfums")


def verify_totp(secret: str, code: str) -> bool:
    # shortcut: un même code reste valable pendant sa fenêtre de 30 s (pas d'anti-rejeu),
    # à ajouter si un collaborateur se connecte depuis des postes partagés.
    return pyotp.TOTP(secret).verify(code.replace(" ", ""), valid_window=1)


def new_recovery_codes(count: int = 8) -> list[str]:
    return [f"{secrets.token_hex(3)}-{secrets.token_hex(3)}" for _ in range(count)]
