# Configuration

> This document covers 12-factor configuration, pydantic-settings usage, environment layering, and validation.

## Overview

We follow the **12-factor app** methodology for configuration. Configuration is separated from code and varies across environments. We use `pydantic-settings` for type-safe configuration management.

## Configuration Layers

Configuration is layered, with later layers overriding earlier ones:

```
defaults < config.yaml < environment variables < secrets (vault)
```

| Layer | Source | Use Case |
|-------|--------|----------|
| Defaults | Code | Safe fallback values |
| config.yaml | File | Environment-specific non-secrets |
| Environment | ENV vars | CI/CD, deployment |
| Secrets | Vault/SSM | API keys, passwords |

## Settings Structure

```python
# src/common/config.py
from typing import Optional, List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Fail on unknown config
    )

    # === Application ===
    APP_NAME: str = "Splashh Sports Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production

    # === Server ===
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # === Database ===
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "splashh"
    DATABASE_USER: str = "splashh"
    DATABASE_PASSWORD: str = Field(default="", exclude=True)  # Secret
    DATABASE_URL: Optional[str] = None  # Computed

    @property
    def database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"

    # === Redis ===
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = Field(default="", exclude=True)
    REDIS_URL: Optional[str] = None

    @property
    def redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # === Security ===
    SECRET_KEY: str = Field(default="", exclude=True)
    JWT_SECRET: str = Field(default="", exclude=True)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRY_DAYS: int = 30

    # === External Services ===
    STRIPE_API_KEY: str = Field(default="", exclude=True)
    SENDGRID_API_KEY: str = Field(default="", exclude=True)
    S3_BUCKET: str = ""
    S3_REGION: str = "us-east-1"

    # === Logging ===
    LOG_LEVEL: str = "INFO"

    # === Feature Flags ===
    ENABLE_NEW_BOOKING_FLOW: bool = False

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid = {"development", "staging", "production"}
        if v not in valid:
            raise ValueError(f"ENVIRONMENT must be one of {valid}")
        return v

    @field_validator("DEBUG")
    @classmethod
    def debug_production(cls, v: bool, info) -> bool:
        if v and info.data.get("ENVIRONMENT") == "production":
            raise ValueError("DEBUG cannot be True in production")
        return v


# Global singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

## Required vs Optional

| Setting | Required | Default | Validation |
|---------|-----------|---------|------------|
| `DATABASE_URL` | No | Computed | Must be valid URL |
| `REDIS_URL` | No | Computed | Must be valid URL |
| `SECRET_KEY` | Yes | - | Min 32 chars |
| `DEBUG` | No | False | Cannot be True in prod |
| `ENVIRONMENT` | No | development | Must be valid env |

## Validation at Startup

```python
# src/main.py
from fastapi import FastAPI
from common.config import get_settings


def validate_settings() -> None:
    """Validate settings at startup."""
    settings = get_settings()

    # Validate required secrets in production
    if settings.ENVIRONMENT == "production":
        if not settings.SECRET_KEY:
            raise ValueError("SECRET_KEY is required in production")
        if not settings.JWT_SECRET:
            raise ValueError("JWT_SECRET is required in production")

        # Warn about default passwords
        if settings.DATABASE_PASSWORD == "password":
            raise ValueError("DATABASE_PASSWORD must be changed in production")


app = FastAPI()


@app.on_event("startup")
async def startup():
    validate_settings()
    configure_logging()
```

## Usage in Code

```python
# In any module
from common.config import get_settings


def some_function():
    settings = get_settings()

    # Use settings
    db_url = settings.database_url
    if settings.DEBUG:
        # Do something in debug mode
        pass
```

## Environment-Specific Config

### config.yaml

```yaml
# config.yaml
development:
  database:
    host: localhost
    port: 5432
  redis:
    host: localhost
  debug: true
  log_level: DEBUG

staging:
  database:
    host: staging-db.internal
    port: 5432
  redis:
    host: staging-redis.internal
  debug: false
  log_level: INFO

production:
  database:
    host: prod-db.internal
    port: 5432
  redis:
    host: prod-redis.internal
  debug: false
  log_level: WARNING
```

### Loading Config

```python
# src/common/config.py
import yaml
from pathlib import Path


class Settings(BaseSettings):
    # ... settings fields

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "Settings":
        """Load settings from YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            return cls()

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        env = config_data.get(cls().ENVIRONMENT, {})
        return cls(**env)
```

## Secrets Management

In production, load secrets from a secrets manager:

```python
# src/common/config.py
import boto3
from botocore.exceptions import ClientError


class Settings(BaseSettings):
    # ... fields

    @classmethod
    def from_aws_secrets_manager(cls, secret_name: str) -> "Settings":
        """Load secrets from AWS Secrets Manager."""
        # Create Secrets Manager client
        session = boto3.session.Session()
        client = session.client("secretsmanager")

        try:
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name
            )
            secret = json.loads(get_secret_value_response["SecretString"])
            return cls(**secret)
        except ClientError as e:
            raise ValueError(f"Failed to load secrets: {e}")
```

## Testing with Settings

```python
# tests/conftest.py
import pytest
from unittest.mock import patch

from common.config import Settings


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    return Settings(
        DATABASE_URL="sqlite+aiosqlite:///:memory:",
        REDIS_URL="redis://localhost:6379/0",
        SECRET_KEY="test-secret-key-that-is-long-enough",
        JWT_SECRET="test-jwt-secret-key",
        DEBUG=True,
        ENVIRONMENT="testing",
    )


@pytest.fixture
def override_settings(test_settings):
    """Override settings singleton in tests."""
    with patch("common.config._settings", test_settings):
        yield test_settings
```

## Anti-Patterns

1. **Hardcoding configuration** — Never hardcode URLs, secrets, or feature flags
2. **Missing validation** — Validate required settings at startup
3. **Storing secrets in code** — Use environment variables or secrets manager
4. **No defaults** — Always provide sensible defaults for development

## Related Documents

- [12-Factor App](https://12factor.net/config)
- [Pydantic Settings](https://docs.pydantic.dev/latest/usage/settings/)
- [Secrets Management](../09-security/secrets-management.md)
