"""Settings that only bite in production.

The database URL normaliser exists because a hosting platform hands out a
connection string the app cannot use unchanged. Getting it wrong means the
service does not boot at all, which is the worst time to find out, so it is
tested here rather than on a deploy.
"""

import pytest

from app.settings import Settings

REQUIRED = {
    "jwt_secret": "test-secret",
    "openai_api_key": "test-key",
}


def settings_with(database_url: str) -> Settings:
    return Settings(database_url=database_url, **REQUIRED)


@pytest.mark.parametrize(
    "given",
    [
        "postgresql://user:pass@host:5432/db",
        # Heroku-style platforms still hand out the older scheme.
        "postgres://user:pass@host:5432/db",
    ],
)
def test_a_plain_postgres_url_is_pointed_at_the_async_driver(given: str) -> None:
    """SQLAlchemy picks its driver from the scheme.

    A bare `postgresql://` means psycopg, and `create_async_engine` rejects it
    at import time -- the service would never start.
    """
    assert settings_with(given).database_url == (
        "postgresql+asyncpg://user:pass@host:5432/db"
    )


def test_a_url_that_already_names_asyncpg_is_left_alone() -> None:
    url = "postgresql+asyncpg://user:pass@localhost:5433/job_pipeline"
    assert settings_with(url).database_url == url


def test_sslmode_is_dropped() -> None:
    """`sslmode` is a libpq option; asyncpg raises on it.

    Render's external connection string includes it, its internal one does
    not, so this only matters if someone wires up the external URL.
    """
    normalised = settings_with(
        "postgresql://user:pass@host:5432/db?sslmode=require"
    ).database_url
    assert normalised == "postgresql+asyncpg://user:pass@host:5432/db"


def test_other_query_parameters_survive() -> None:
    normalised = settings_with(
        "postgresql://user:pass@host:5432/db?sslmode=require&application_name=api"
    ).database_url
    assert normalised == (
        "postgresql+asyncpg://user:pass@host:5432/db?application_name=api"
    )


def test_a_password_with_punctuation_is_not_mangled() -> None:
    """Platform-generated passwords are random and contain URL-ish characters."""
    url = "postgresql://u:aB3%2Fx%3Dy@host:5432/db"
    assert settings_with(url).database_url == (
        "postgresql+asyncpg://u:aB3%2Fx%3Dy@host:5432/db"
    )


def test_the_environment_must_be_one_of_the_known_three() -> None:
    with pytest.raises(ValueError):
        Settings(
            database_url="postgresql+asyncpg://u:p@h:5432/d",
            environment="staging",
            **REQUIRED,
        )


def test_redis_defaults_to_the_local_container_port() -> None:
    """6380, not 6379: another project's Redis holds 6379 on this machine."""
    assert settings_with("postgresql+asyncpg://u:p@h:5432/d").redis_url == (
        "redis://localhost:6380"
    )
