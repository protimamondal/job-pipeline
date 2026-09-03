from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Job Pipeline API"
    environment: Literal["local", "test", "production"] = "local"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="JOB_PIPELINE_",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
