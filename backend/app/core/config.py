from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
    frontend_origin: str = "http://localhost:3000"


settings = Settings()  # type: ignore[call-arg]  # valeurs lues dans l'environnement
