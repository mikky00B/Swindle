from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]

DEVELOPMENT_DEFAULTS = {
    "token_encryption_key": "dev-only-token-key",
    "lichess_client_id": "swindle-local",
}


class Settings(BaseSettings):
    app_name: str = "Swindle"
    app_env: str = Field(default="development", alias="APP_ENV")
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = Field(default="http://localhost:5173", alias="FRONTEND_ORIGIN")
    cors_allowed_origins: str = Field(default="", alias="CORS_ALLOWED_ORIGINS")
    lichess_client_id: str = Field(default="swindle-local", alias="LICHESS_CLIENT_ID")
    lichess_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/integrations/lichess/callback",
        alias="LICHESS_REDIRECT_URI",
    )
    lichess_scopes: str = Field(default="", alias="LICHESS_SCOPES")
    lichess_oauth_authorize_url: str = Field(default="https://lichess.org/oauth", alias="LICHESS_OAUTH_AUTHORIZE_URL")
    lichess_oauth_token_url: str = Field(default="https://lichess.org/api/token", alias="LICHESS_OAUTH_TOKEN_URL")
    lichess_api_base_url: str = Field(default="https://lichess.org", alias="LICHESS_API_BASE_URL")
    chesscom_api_base_url: str = Field(default="https://api.chess.com/pub", alias="CHESSCOM_API_BASE_URL")
    token_encryption_key: str = Field(default="dev-only-token-key", alias="TOKEN_ENCRYPTION_KEY")
    database_url: str = Field(default="postgresql+psycopg://swindle:swindle@localhost:5432/swindle", alias="DATABASE_URL")

    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", ROOT_DIR / "backend" / ".env"), extra="ignore")

    @model_validator(mode="after")
    def _reject_development_defaults_in_production(self) -> "Settings":
        if self.app_env != "production":
            return self
        insecure = [name for name, default in DEVELOPMENT_DEFAULTS.items() if getattr(self, name) == default]
        if insecure:
            joined = ", ".join(name.upper() for name in insecure)
            raise ValueError(
                f"Refusing to start with development defaults in production: set {joined} to real values."
            )
        return self

    @property
    def allowed_origins(self) -> list[str]:
        origins = {self.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"}
        origins.update(origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip())
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
