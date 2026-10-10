from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Job Pipeline API"
    environment: Literal["local", "test", "production"] = "local"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    openai_api_key: str
    draft_model: str = "gpt-4.1-mini"
    mcp_server_url: str = "http://127.0.0.1:8001/mcp"
    # The MCP SDK's own default is 30s, and a sleeping free-plan service takes
    # a little over 31s to wake, so the first request after an idle period
    # failed about a second early. Long enough to cover a cold start, and
    # still short enough that a genuinely dead service does not hang the user.
    mcp_timeout_seconds: float = 90.0
    redis_url: str = "redis://localhost:6380"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JOB_PIPELINE_",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def normalise_database_url(cls, value: str) -> str:
        """Accept a plain Postgres URL and point it at the async driver.

        Hosting platforms hand out `postgresql://...` (Heroku-style ones still
        hand out `postgres://...`), but SQLAlchemy picks its driver from that
        scheme, and a bare `postgresql://` means psycopg. `create_async_engine`
        then refuses it at import time, so the service would never start.

        Normalising here rather than in the deploy config means the platform's
        own connection string can be wired straight through, with nothing to
        keep in sync by hand.

        `sslmode` is dropped because it is a libpq option that asyncpg does not
        accept; asyncpg negotiates TLS on its own. Render's internal connection
        string does not include it, but its external one does.
        """
        for prefix, replacement in (
            ("postgres://", "postgresql+asyncpg://"),
            ("postgresql://", "postgresql+asyncpg://"),
        ):
            if value.startswith(prefix):
                value = replacement + value[len(prefix):]
                break

        parts = urlsplit(value)
        if "sslmode=" in parts.query:
            kept = [
                pair
                for pair in parts.query.split("&")
                if pair and not pair.startswith("sslmode=")
            ]
            value = urlunsplit(parts._replace(query="&".join(kept)))

        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
