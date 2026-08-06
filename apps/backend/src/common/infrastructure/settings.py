"""Application settings via pydantic-settings (12-factor).

Settings are loaded once at startup from environment variables and `.env` files.
They are immutable at runtime — tests create their own Settings instance with
overrides.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Top-level settings.

    Values are loaded from environment variables (and an optional `.env`).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Runtime ----
    environment: Literal["development", "test", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    debug: bool = False

    # ---- Database ----
    database_url: str = Field(
        default="postgresql+asyncpg://splashh:splashh_dev@localhost:5432/splashh",
        description="Async SQLAlchemy URL",
    )

    # ---- Cache / queue ----
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ---- JWT ----
    jwt_algorithm: Literal["RS256", "HS256"] = "RS256"
    jwt_private_key_path: Path = Field(default=Path("./secrets/jwt_private.pem"))
    jwt_public_key_path: Path = Field(default=Path("./secrets/jwt_public.pem"))
    jwt_access_token_ttl_seconds: int = 900  # 15 min
    jwt_refresh_token_ttl_seconds: int = 30 * 24 * 3600  # 30 days

    # ---- CORS ----
    cors_allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://localhost:5174"])

    # ---- Refresh-token cookie ----
    auth_refresh_cookie_name: str = "refresh_token"
    auth_refresh_cookie_secure: bool = True
    auth_refresh_cookie_samesite: str = "lax"
    auth_refresh_cookie_path: str = "/v1/auth"
    auth_refresh_cookie_max_age_seconds: int = 2_592_000  # 30 days

    # ---- Rate limiting ----
    rate_limit_default_per_minute: int = 120
    rate_limit_login_per_minute: int = 10

    # ---- SSRF allowlist ----
    ssrf_allowed_hosts: list[str] = Field(default_factory=list)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Tests can call [`Settings.cache_clear`]."""
    return Settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
