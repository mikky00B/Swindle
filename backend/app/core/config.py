from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


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
    token_encryption_key: str = Field(default="dev-only-token-key", alias="TOKEN_ENCRYPTION_KEY")
    database_url: str = Field(default="postgresql+psycopg://swindle:swindle@localhost:5432/swindle", alias="DATABASE_URL")

    model_config = SettingsConfigDict(env_file=(ROOT_DIR / ".env", ROOT_DIR / "backend" / ".env"), extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        origins = {self.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"}
        origins.update(origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip())
        return sorted(origins)


@lru_cache
def get_settings() -> Settings:
    return Settings()
