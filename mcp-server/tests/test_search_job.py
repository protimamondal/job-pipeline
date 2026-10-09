"""What `search_job` does with the cache and with a failing Arbeitnow.

Sub-phase 5 verified all of this by hand with throwaway scripts. These are
the same checks, kept.

Neither Redis nor Arbeitnow is real here. `FakeRedis` records the commands it
receives so a test can assert on the TTL, and `fake_http` replaces
`httpx.AsyncClient` so a test can make the job board fail on demand without
waiting for a real timeout.

The coroutines are driven with `asyncio.run` from sync tests, so no async
pytest plugin is needed.
"""

import asyncio
import json
from types import SimpleNamespace

import httpx
import pytest
import redis.exceptions

import server

CACHE_KEY = "jobs:python developer:berlin"


# --- doubles ---------------------------------------------------------------

class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.ttls: dict[str, int] = {}
        self.read_failure: Exception | None = None
        self.write_failure: Exception | None = None

    async def get(self, key: str) -> str | None:
        if self.read_failure is not None:
            raise self.read_failure
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        if self.write_failure is not None:
            raise self.write_failure
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True


class FakeResponse:
    def __init__(self, payload, status: int = 200) -> None:
        self._payload = payload
        self.status_code = status

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code}", request=None, response=None
            )

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class FakeAsyncClient:
    """Replaces `httpx.AsyncClient`, recording the params it was given."""

    calls: list[dict] = []

    def __init__(self, response=None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def get(self, url: str, params=None, timeout=None):
        type(self).calls.append({"url": url, "params": params, "timeout": timeout})
        if self._error is not None:
            raise self._error
        return self._response


def install(monkeypatch, *, response=None, error: Exception | None = None) -> FakeRedis:
    """Give `server` a fresh fake Redis and a scripted Arbeitnow."""
    fake_redis = FakeRedis()
    monkeypatch.setattr(server, "redis_client", fake_redis)

    FakeAsyncClient.calls = []
    monkeypatch.setattr(
        server.httpx,
        "AsyncClient",
        lambda *a, **kw: FakeAsyncClient(response=response, error=error),
    )
    return fake_redis


def board(*jobs) -> FakeResponse:
    """An Arbeitnow response carrying these jobs."""
    return FakeResponse({"data": list(jobs)})


def job(title="Python Developer", company="ACME", location="Berlin") -> dict:
    return {"title": title, "company_name": company, "location": location}


def search(title="python developer", location="berlin"):
    return asyncio.run(server.search_job(title, location))


# --- a cache miss ---------------------------------------------------------

def test_a_miss_calls_arbeitnow_and_caches_the_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = install(monkeypatch, response=board(job()))

    results = search()

    assert results == [
        {
            "company": "ACME",
            "title": "Python Developer",
            "location": "Berlin",
            "salary": None,
        }
    ]
    assert len(FakeAsyncClient.calls) == 1
    assert FakeAsyncClient.calls[0]["params"] == {"search": "python developer"}
    assert json.loads(fake_redis.values[CACHE_KEY]) == results


def test_the_cached_entry_expires_after_ten_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """600s is a staleness decision: job boards change slowly."""
    fake_redis = install(monkeypatch, response=board(job()))

    search()

    assert fake_redis.ttls[CACHE_KEY] == 600
    assert server.CACHE_TTL_SECONDS == 600


def test_the_cache_key_is_case_insensitive(monkeypatch: pytest.MonkeyPatch) -> None:
    """Otherwise "Python Developer" and "python developer" are separate keys."""
    fake_redis = install(monkeypatch, response=board(job()))

    search(title="Python Developer", location="Berlin")

    assert list(fake_redis.values) == [CACHE_KEY]


# --- a cache hit ----------------------------------------------------------

def test_a_hit_returns_the_cached_value_without_calling_arbeitnow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cached = [
        {
            "company": "Cached Co",
            "title": "Python Developer",
            "location": "Berlin",
            "salary": None,
        }
    ]
    fake_redis = install(monkeypatch, response=board(job()))
    fake_redis.values[CACHE_KEY] = json.dumps(cached)

    results = search()

    assert results == cached
    assert FakeAsyncClient.calls == []


def test_an_empty_cached_result_is_still_a_hit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A cached empty list means "we looked and there were none".

    The check is `cached is not None`, not a truthiness test, so an empty
    list must not be mistaken for a miss and re-fetched.
    """
    fake_redis = install(monkeypatch, response=board(job()))
    fake_redis.values[CACHE_KEY] = json.dumps([])

    assert search() == []
    assert FakeAsyncClient.calls == []


# --- filtering ------------------------------------------------------------

def test_jobs_outside_the_location_are_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install(
        monkeypatch,
        response=board(
            job(location="Berlin"),
            job(location="Munich"),
            job(location="Berlin, Germany"),
        ),
    )

    results = search()

    assert [r["location"] for r in results] == ["Berlin", "Berlin, Germany"]


def test_at_most_five_jobs_come_back(monkeypatch: pytest.MonkeyPatch) -> None:
    install(monkeypatch, response=board(*[job() for _ in range(12)]))

    assert len(search()) == 5


def test_no_matches_returns_an_empty_list_and_caches_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = install(monkeypatch, response=board(job(location="Munich")))

    assert search() == []
    # Worth caching: it stops a popular dead search hitting Arbeitnow repeatedly.
    assert fake_redis.values[CACHE_KEY] == "[]"


# --- Redis being unavailable ---------------------------------------------

def test_a_failed_cache_read_still_returns_live_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Losing Redis must only make things slower, never wrong."""
    fake_redis = install(monkeypatch, response=board(job()))
    fake_redis.read_failure = redis.exceptions.ConnectionError("connection refused")

    results = search()

    assert len(results) == 1
    assert len(FakeAsyncClient.calls) == 1


def test_a_failed_cache_write_still_returns_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = install(monkeypatch, response=board(job()))
    fake_redis.write_failure = redis.exceptions.TimeoutError("timeout")

    assert len(search()) == 1


def test_redis_being_down_entirely_is_survivable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_redis = install(monkeypatch, response=board(job()))
    down = redis.exceptions.ConnectionError("connection refused")
    fake_redis.read_failure = down
    fake_redis.write_failure = down

    assert len(search()) == 1


def test_the_connect_timeout_is_half_a_second() -> None:
    """Measured in sub-phase 5: 4.1s by default, 0.509s with this set.

    Without it every call waits on the OS connect timeout while Redis is
    down, which is what made a degraded cache feel like an outage.
    """
    kwargs = server.redis_client.connection_pool.connection_kwargs
    assert kwargs["socket_connect_timeout"] == 0.5


# --- Arbeitnow failing ----------------------------------------------------

@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("All connection attempts failed"),
        httpx.ReadTimeout("timed out"),
    ],
)
def test_a_dead_job_board_becomes_a_readable_message(
    monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """`httpx.HTTPError` is the parent of connect, timeout and status errors."""
    install(monkeypatch, error=error)

    with pytest.raises(RuntimeError) as raised:
        search()

    assert str(raised.value) == (
        "Job search is temporarily unavailable. Please try again in a moment."
    )
    # The cause is kept so the logs can say why, without leaking it to the user.
    assert raised.value.__cause__ is error


def test_a_rate_limited_job_board_becomes_the_same_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arbeitnow answering 429 is the case a queue would have retried.

    With no worker, the user is simply told it failed. Recorded as a known
    limitation in PHASE3.md sub-phase 5.
    """
    install(monkeypatch, response=FakeResponse(None, status=429))

    with pytest.raises(RuntimeError) as raised:
        search()

    assert "temporarily unavailable" in str(raised.value)
    assert isinstance(raised.value.__cause__, httpx.HTTPStatusError)


@pytest.mark.parametrize(
    "payload",
    [
        {"jobs": []},  # the "data" key is gone -> KeyError
        ValueError("Expecting value: line 1 column 1"),  # not JSON at all
    ],
)
def test_an_unexpected_response_shape_becomes_its_own_message(
    monkeypatch: pytest.MonkeyPatch, payload
) -> None:
    """A changed API is a bug to notice, not a blip -- so a distinct message."""
    install(monkeypatch, response=FakeResponse(payload))

    with pytest.raises(RuntimeError) as raised:
        search()

    assert str(raised.value) == (
        "Job search returned an unexpected response. Please try again in a moment."
    )


def test_a_missing_field_in_a_job_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The filtering happens after the except blocks.

    A job with no `location` raises `KeyError` outside the handled region, so
    it propagates as itself. Pinned so the behaviour is deliberate: a changed
    schema should be loud, not turned into an empty result list.
    """
    install(monkeypatch, response=board({"title": "x", "company_name": "y"}))

    with pytest.raises(KeyError):
        search()


def test_a_failure_is_never_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cached failure would poison the key for the full ten minutes."""
    fake_redis = install(monkeypatch, error=httpx.ConnectError("refused"))

    with pytest.raises(RuntimeError):
        search()

    assert fake_redis.values == {}


def test_a_timeout_is_set_on_the_job_board_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without it a hanging Arbeitnow would hang the MCP tool indefinitely."""
    install(monkeypatch, response=board(job()))

    search()

    assert FakeAsyncClient.calls[0]["timeout"] == 10
