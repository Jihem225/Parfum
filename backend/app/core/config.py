from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
    secret_key: str
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    resend_api_key: str = ""
    email_from: str = "Projet Parfums <no-reply@example.com>"


settings = Settings()  # type: ignore[call-arg]  # valeurs lues dans l'environnement
