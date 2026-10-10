"""The per-user rate limit in front of the two endpoints that cost money.

`enforce_rate_limit` is a fixed-window limiter: it INCRs
`ratelimit:{user_id}:{window}` where `window` is the current minute, so a key
expiring is all the cleanup there is. These tests cover the policy (20/min,
per user, 429 with Retry-After), the window behaviour, and the deliberate
decision to fail open when Redis is unreachable.

Redis itself is `tests.fakes.FakeRedis`, installed for every test by the
autouse `fake_redis` fixture in `conftest.py`.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app import rate_limit
from app.rate_limit import RATE_LIMIT_PER_MINUTE, WINDOW_SECONDS
from tests.fakes import FakeRedis

# A moment pinned exactly on a window boundary. The window number is part of
# the key, so a test that sends twenty requests and then asserts the
# twenty-first is refused fails if the minute happens to tick over in the
# middle -- the counter starts again under a new key and the request is
# allowed. That is correct behaviour and a broken test: rare, timing
# dependent, and it duly appeared once the suite grew slower.
FROZEN_NOW = 1_700_000_040.0


@pytest.fixture(autouse=True)
def frozen_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hold the limiter's clock still, so no test straddles two windows."""
    monkeypatch.setattr(rate_limit, "time", SimpleNamespace(time=lambda: FROZEN_NOW))


def chat(client: TestClient, headers: dict):
    return client.post(
        "/chat",
        json={"messages": [{"role": "user", "parts": [{"type": "text", "text": "hi"}]}]},
        headers=headers,
    )


def draft(client: TestClient, headers: dict):
    return client.post(
        "/jobs/1/draft", json={"instruction": None}, headers=headers
    )


def current_key(user_id: int) -> str:
    return f"ratelimit:{user_id}:{int(FROZEN_NOW // WINDOW_SECONDS)}"


# --- the policy -----------------------------------------------------------

def test_requests_up_to_the_limit_are_allowed(
    client: TestClient, auth_headers: dict, stub_chat_ai: None
) -> None:
    for attempt in range(RATE_LIMIT_PER_MINUTE):
        response = chat(client, auth_headers)
        assert response.status_code == 200, f"request {attempt + 1} was rejected"


def test_the_request_after_the_limit_is_rejected_with_429(
    client: TestClient, auth_headers: dict, stub_chat_ai: None
) -> None:
    for _ in range(RATE_LIMIT_PER_MINUTE):
        chat(client, auth_headers)

    response = chat(client, auth_headers)
    assert response.status_code == 429
    assert response.json()["detail"] == (
        "Too many requests. Please wait a moment and try again."
    )
    # Tells a well-behaved client how long to wait instead of hammering.
    assert response.headers["Retry-After"] == str(WINDOW_SECONDS)


def test_a_rejected_request_never_reaches_the_endpoint(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The whole point: a blocked request must not cost an OpenAI call.

    Note `stub_chat_ai` is deliberately not used here -- nothing is stubbed,
    so if the limiter let the request through, the route would try to reach
    the real OpenAI and the real MCP server.
    """
    from app.routers import chat as chat_router

    def explode(**kwargs):
        raise AssertionError("the endpoint ran for a rate-limited request")

    monkeypatch.setattr(chat_router, "AsyncOpenAI", explode)
    monkeypatch.setattr(chat_router, "streamable_http_client", explode)

    # Fill the window by hand so no real request is needed to fill it.
    from app import rate_limit

    rate_limit.redis_client.values[current_key(1)] = RATE_LIMIT_PER_MINUTE

    assert chat(client, auth_headers).status_code == 429


def test_both_paid_endpoints_are_limited(
    client: TestClient,
    auth_headers: dict,
    fake_redis: FakeRedis,
    stub_chat_ai: None,
    stub_draft_ai: None,
) -> None:
    fake_redis.values[current_key(1)] = RATE_LIMIT_PER_MINUTE

    assert chat(client, auth_headers).status_code == 429
    assert draft(client, auth_headers).status_code == 429


def test_the_two_endpoints_share_one_budget(
    client: TestClient,
    auth_headers: dict,
    fake_redis: FakeRedis,
    stub_chat_ai: None,
    stub_draft_ai: None,
) -> None:
    """One key per user, not one per route -- 20/min total, not 20 each."""
    fake_redis.values[current_key(1)] = RATE_LIMIT_PER_MINUTE - 1

    assert draft(client, auth_headers).status_code == 200
    assert chat(client, auth_headers).status_code == 429


# --- per user, not global -------------------------------------------------

def test_one_user_hitting_the_limit_does_not_block_another(
    client: TestClient, register_user, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    protima = register_user(email="protima@example.com")
    rahul = register_user(email="rahul@example.com")

    for _ in range(RATE_LIMIT_PER_MINUTE):
        chat(client, protima)

    assert chat(client, protima).status_code == 429
    assert chat(client, rahul).status_code == 200


def test_the_key_is_namespaced_by_user_and_window(
    client: TestClient, auth_headers: dict, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    chat(client, auth_headers)

    assert list(fake_redis.values) == [current_key(1)]


# --- the window -----------------------------------------------------------

def test_a_new_window_starts_a_new_counter(
    client: TestClient, auth_headers: dict, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    """The window number is part of the key, so the next minute is a new key.

    This also demonstrates the known limitation of a fixed window: a user who
    exhausts one window can immediately spend a whole second window, so up to
    2x the limit can land either side of a minute boundary.
    """
    previous_window = int(FROZEN_NOW // WINDOW_SECONDS) - 1
    fake_redis.values[f"ratelimit:1:{previous_window}"] = RATE_LIMIT_PER_MINUTE

    # The old window is full, but we are no longer in it.
    assert chat(client, auth_headers).status_code == 200
    assert fake_redis.values[current_key(1)] == 1


def test_a_fresh_key_is_given_an_expiry(
    client: TestClient, auth_headers: dict, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    """INCR creates a key with no TTL at all, so EXPIRE must follow it.

    Without this the keys would accumulate forever: one per user per minute,
    none of them ever removed.
    """
    chat(client, auth_headers)

    key = current_key(1)
    assert await_ttl(fake_redis, key) == WINDOW_SECONDS
    assert ("expire", key, WINDOW_SECONDS) in fake_redis.commands


def test_the_expiry_is_only_set_once_per_window(
    client: TestClient, auth_headers: dict, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    """EXPIRE runs only when INCR returned 1.

    Re-setting it on every request would slide the expiry forward and the
    window would never end for a continuously active user.
    """
    for _ in range(5):
        chat(client, auth_headers)

    expires = [c for c in fake_redis.commands if c[0] == "expire"]
    assert len(expires) == 1


def await_ttl(fake: FakeRedis, key: str) -> int:
    """TTL without needing an event loop -- FakeRedis stores it plainly."""
    return fake.ttls.get(key, -1 if key in fake.values else -2)


# --- Redis being unavailable ---------------------------------------------

@pytest.mark.parametrize(
    "failure",
    [
        RedisConnectionError("Error connecting to localhost:6380"),
        RedisTimeoutError("Timeout connecting to server"),
    ],
)
def test_the_request_is_allowed_when_redis_is_unreachable(
    client: TestClient,
    auth_headers: dict,
    fake_redis: FakeRedis,
    stub_chat_ai: None,
    failure: Exception,
) -> None:
    """A deliberate decision: fail open, not closed.

    Both limited endpoints are already behind authentication, so an
    unauthenticated flood is not the threat. Refusing every request because
    the cache is down would turn a degraded cache into a full outage, which
    is the opposite of what sub-phase 5 is for.
    """
    fake_redis.failure = failure

    assert chat(client, auth_headers).status_code == 200


def test_the_failure_is_logged_at_error_when_redis_is_unreachable(
    client: TestClient,
    auth_headers: dict,
    fake_redis: FakeRedis,
    stub_chat_ai: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Failing open silently would hide a broken limiter indefinitely."""
    fake_redis.failure = RedisConnectionError("Error connecting to localhost:6380")

    with caplog.at_level("ERROR", logger="job_pipeline"):
        chat(client, auth_headers)

    unavailable = [
        record
        for record in caplog.records
        if record.message == "rate_limit_unavailable"
    ]
    assert len(unavailable) == 1
    assert unavailable[0].levelname == "ERROR"
    assert unavailable[0].user_id == 1


def test_exceeding_the_limit_is_logged_at_warning(
    client: TestClient,
    auth_headers: dict,
    fake_redis: FakeRedis,
    stub_chat_ai: None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    fake_redis.values[current_key(1)] = RATE_LIMIT_PER_MINUTE

    with caplog.at_level("WARNING", logger="job_pipeline"):
        chat(client, auth_headers)

    exceeded = [
        record for record in caplog.records if record.message == "rate_limit_exceeded"
    ]
    assert len(exceeded) == 1
    assert exceeded[0].levelname == "WARNING"
    assert exceeded[0].limit == RATE_LIMIT_PER_MINUTE
    assert exceeded[0].count == RATE_LIMIT_PER_MINUTE + 1


def test_a_redis_that_accepts_incr_but_refuses_expire_still_allows_the_request(
    client: TestClient, auth_headers: dict, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    """A known limitation, pinned here so it is not mistaken for a bug.

    If EXPIRE fails on its own the counter survives with no TTL, so that one
    key leaks. The request is still allowed, which is the right trade: the
    alternative is rejecting real users over a stray Redis error.
    """
    fake_redis.expire_failure = RedisTimeoutError("Timeout connecting to server")

    assert chat(client, auth_headers).status_code == 200


# --- the limiter must not weaken auth ------------------------------------

def test_an_anonymous_request_is_still_rejected_as_401_not_429(
    client: TestClient, stub_chat_ai: None
) -> None:
    """Swapping the dependency must not have changed who gets in.

    `enforce_rate_limit` depends on `get_current_user`, so authentication
    still runs first and an anonymous caller never reaches the limiter.
    """
    assert chat(client, {}).status_code == 401
    assert draft(client, {}).status_code == 401


def test_a_rejected_anonymous_request_consumes_no_budget(
    client: TestClient, fake_redis: FakeRedis, stub_chat_ai: None
) -> None:
    chat(client, {})
    assert fake_redis.values == {}
