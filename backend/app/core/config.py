from typing import Literal, Self

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
    secret_key: str
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    # Proxys qui ajoutent une adresse à X-Forwarded-For : 1 derrière Render, 2 avec Cloudflare.
    trusted_proxy_hops: int = 0
    resend_api_key: str = ""
    email_from: str = "Projet Parfums <no-reply@example.com>"
    shop_notification_email: str = ""  # destinataire des alertes (stock bas, nouvelles commandes)
    order_number_prefix: str = "PP"  # provisoire (RG-28)
    # Mobile money : "" = désactivé ; "simulation" = faux paiements (développement, CI ; refusé en
    # production). Les vrais prestataires s'ajoutent dans app/modules/payments/providers.py.
    payment_provider: Literal["", "simulation"] = ""
    payment_webhook_secret: str = ""  # signature des avis de paiement du prestataire
    media_dir: str = "media"  # stockage local des images (développement)
    media_base_url: str = "/media"
    # Cloudflare R2 (API S3) : si S3_BUCKET est défini, les images y vont au lieu du disque.
    s3_endpoint_url: str = ""
    s3_bucket: str = ""
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_public_base_url: str = ""

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3(cls, url: str) -> str:
        # Render fournit postgresql://… ; SQLAlchemy prendrait alors psycopg2, non installé.
        return url.replace("postgresql://", "postgresql+psycopg://", 1)

    @model_validator(mode="after")
    def _refuse_unsafe_production(self) -> Self:
        if self.app_env != "production":
            return self
        missing = [
            message
            for broken, message in (
                (not self.cookie_secure, "COOKIE_SECURE=true"),
                (not self.frontend_origin.startswith("https://"), "FRONTEND_ORIGIN en https://"),
                (len(self.secret_key) < 32, "SECRET_KEY d'au moins 32 caractères"),
                (not self.s3_bucket, "S3_* (le disque de l'hébergeur est effacé au déploiement)"),
                (
                    self.trusted_proxy_hops < 1,
                    "TRUSTED_PROXY_HOPS ≥ 1 (sinon limites par IP globales)",
                ),
                (self.payment_provider == "simulation", "PAYMENT_PROVIDER sans simulation"),
            )
            if broken
        ]
        if missing:
            raise ValueError("Configuration de production incomplète : " + " ; ".join(missing))
        return self


settings = Settings()  # type: ignore[call-arg]  # valeurs lues dans l'environnement
