"""The first copilot message after the services have been idle.

Both free-plan services sleep. When the backend is awake and the MCP server
is not, the backend's call has to wait out a cold start that measured 31.4s
against the MCP SDK's 30s default -- so the first message failed and the
retry a moment later worked. These tests pin the timeout that fixes it, and
the unwrapping that made the cause visible in the first place: anyio re-raises
through a task group, so the error the user and the log saw was "unhandled
errors in a TaskGroup (1 sub-exception)" and nothing else.
"""

import json

from types import SimpleNamespace

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.routers import chat as chat_router
from app.routers.chat import unwrap
from app.settings import get_settings
from tests.fakes import FakeHttpClient, text_chunk
from tests.test_chat_streaming import ask, events, install_fakes

# What the cold start actually measured against the deployed service: 31.4s
# twice, and 41.5s once.
OBSERVED_COLD_START_SECONDS = 41.5

# Captured at import, before the autouse fixture shortens them for the suite.
PRODUCTION_BACKOFF = chat_router.MCP_RETRY_BACKOFF_SECONDS
# Likewise: the fixture stubs the wake out, and these two tests want the real one.
real_wake_mcp_server = chat_router.wake_mcp_server


def test_the_mcp_connection_outlives_a_cold_start() -> None:
    assert get_settings().mcp_timeout_seconds > OBSERVED_COLD_START_SECONDS


def test_the_router_hands_the_connection_a_client_with_that_timeout(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The SDK's 30s default applies unless a client is passed in."""
    seen: dict[str, httpx2.Timeout] = {}

    class RecordingClient:
        def __init__(self, url: str, *, http_client: httpx2.AsyncClient) -> None:
            seen["timeout"] = http_client.timeout

        async def __aenter__(self) -> tuple[object, object]:
            return (object(), object())

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

    install_fakes(monkeypatch, turns=[[text_chunk("hi", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", RecordingClient)

    assert ask(client, auth_headers).status_code == 200

    timeout = seen["timeout"]
    assert timeout.connect > OBSERVED_COLD_START_SECONDS
    assert timeout.connect == get_settings().mcp_timeout_seconds
    # The read timeout governs how long a stream may stay open, which is a
    # different thing; leave the SDK's value alone.
    assert timeout.read == 300.0


def test_the_client_is_closed_even_though_the_sdk_did_not_open_it(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Passing a client in makes its lifecycle ours, and a leak here is a
    connection leak on every chat request."""
    captured: dict[str, httpx2.AsyncClient] = {}

    class Capturing:
        def __init__(self, url: str, *, http_client: httpx2.AsyncClient) -> None:
            captured["client"] = http_client

        async def __aenter__(self) -> tuple[object, object]:
            return (object(), object())

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

    install_fakes(monkeypatch, turns=[[text_chunk("hi", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", Capturing)

    ask(client, auth_headers)

    assert captured["client"].is_closed


# --- the error the user and the log are shown -----------------------------


def test_unwrap_digs_out_the_innermost_cause() -> None:
    """Two levels deep is what the live failure actually looked like."""
    real = httpx2.ConnectTimeout("timed out")
    nested = ExceptionGroup("inner", [real])
    wrapped = ExceptionGroup("unhandled errors in a TaskGroup", [nested])

    assert unwrap(wrapped) is real


def test_unwrap_follows_a_cause_chain() -> None:
    root = ValueError("the real problem")
    try:
        try:
            raise root
        except ValueError as exc:
            raise RuntimeError("wrapper") from exc
    except RuntimeError as exc:
        assert unwrap(exc) is root


def test_unwrap_leaves_a_group_of_several_alone() -> None:
    """With more than one sub-exception there is no single cause to report."""
    group = ExceptionGroup("two", [ValueError("a"), KeyError("b")])

    assert unwrap(group) is group


def test_a_timeout_reaches_the_browser_as_itself(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not as "unhandled errors in a TaskGroup", which is what it used to say."""
    def time_out(url, *, http_client=None):
        raise ExceptionGroup(
            "unhandled errors in a TaskGroup (1 sub-exception)",
            [ExceptionGroup("inner", [httpx2.ConnectTimeout("connect timed out")])],
        )

    install_fakes(monkeypatch, turns=[[text_chunk("unused", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", time_out)

    response = ask(client, auth_headers)
    received = events(response)

    assert [e["type"] for e in received] == ["error"]
    assert received[0]["errorText"].startswith("connect timed out")
    assert "TaskGroup" not in received[0]["errorText"]
    assert response.text.endswith("data: [DONE]\n\n")


def test_the_failure_is_logged_with_the_real_exception(
    client: TestClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A production failure that logs only the wrapper cannot be diagnosed."""
    def time_out(url, *, http_client=None):
        raise ExceptionGroup(
            "unhandled errors in a TaskGroup (1 sub-exception)",
            [httpx2.ConnectTimeout("connect timed out")],
        )

    install_fakes(monkeypatch, turns=[[text_chunk("unused", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", time_out)

    with caplog.at_level("ERROR", logger="job_pipeline"):
        ask(client, auth_headers)

    failures = [r for r in caplog.records if r.message == "chat_stream_failed"]
    assert len(failures) == 1
    assert failures[0].error_type == "ConnectTimeout"
    assert failures[0].exc_info is not None


# --- retrying the connection ----------------------------------------------
#
# A cold start is not only slow. Waking the deployed MCP service, the call
# came straight back in 2.8s with a non-2xx status while it booted, and the
# same request worked once the service was up. So the timeout alone was not
# enough: the connection has to be attempted again.


def test_the_retries_keep_going_for_longer_than_a_boot_takes() -> None:
    """The point the first attempt at this fix got wrong.

    Three tries over eleven seconds all failed against a service that needed
    41.5s to wake. What matters is not the number of attempts but how long
    the last one happens, so that is what is asserted.
    """
    waited = 0.0
    for attempt in range(1, chat_router.MCP_CONNECT_ATTEMPTS):
        waited += PRODUCTION_BACKOFF[min(attempt, len(PRODUCTION_BACKOFF)) - 1]

    assert waited > OBSERVED_COLD_START_SECONDS
    assert waited <= chat_router.MCP_CONNECT_DEADLINE_SECONDS


def test_an_attempt_lands_shortly_after_the_boot_finishes() -> None:
    """A retry schedule that only tried again at 89s would technically pass
    the test above while making the user wait twice as long as needed."""
    waited = 0.0
    for attempt in range(1, chat_router.MCP_CONNECT_ATTEMPTS):
        waited += PRODUCTION_BACKOFF[min(attempt, len(PRODUCTION_BACKOFF)) - 1]
        if waited > OBSERVED_COLD_START_SECONDS:
            assert waited < OBSERVED_COLD_START_SECONDS * 1.5
            return

    raise AssertionError("no attempt falls just after the boot")


def test_a_connection_that_fails_once_is_retried_and_succeeds(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """What the live failure looked like: refused while booting, fine after."""
    attempts = {"n": 0}

    def flaky(url, *, http_client=None):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ExceptionGroup(
                "unhandled errors in a TaskGroup (1 sub-exception)",
                [RuntimeError("Server returned an error response")],
            )
        return FakeHttpClient(url, http_client=http_client)

    install_fakes(monkeypatch, turns=[[text_chunk("hello", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", flaky)

    received = events(ask(client, auth_headers))

    assert attempts["n"] == 2
    assert [e["type"] for e in received] == [
        "start-step", "text-start", "text-delta", "text-end", "finish-step",
    ]
    assert received[2]["delta"] == "hello"


def test_it_gives_up_after_the_last_attempt(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts = {"n": 0}

    def always_fail(url, *, http_client=None):
        attempts["n"] += 1
        raise RuntimeError("Server returned an error response")

    install_fakes(monkeypatch, turns=[[text_chunk("unused", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", always_fail)

    received = events(ask(client, auth_headers))

    assert attempts["n"] == chat_router.MCP_CONNECT_ATTEMPTS
    assert [e["type"] for e in received] == ["error"]
    assert received[0]["errorText"].startswith("Server returned an error response")


def test_a_healthy_server_is_connected_to_exactly_once(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The retry must not cost anything when nothing is wrong."""
    attempts = {"n": 0}

    def once(url, *, http_client=None):
        attempts["n"] += 1
        return FakeHttpClient(url, http_client=http_client)

    install_fakes(monkeypatch, turns=[[text_chunk("hi", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", once)

    ask(client, auth_headers)

    assert attempts["n"] == 1


def test_a_failure_after_streaming_has_begun_is_not_retried(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retrying mid-answer would repeat text the user has already read."""
    attempts = {"n": 0}

    class FailsAfterFirstEvent:
        def __init__(self, url: str, *, http_client: object = None) -> None:
            attempts["n"] += 1

        async def __aenter__(self) -> tuple[object, object]:
            return (object(), object())

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

    install_fakes(monkeypatch, turns=[[text_chunk("partial", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", FailsAfterFirstEvent)

    original = chat_router.get_openai_tools

    async def tools_then_die(session):
        tools = await original(session)
        # Blow up after the first event has reached the browser.
        chat_router.get_openai_tools = boom
        return tools

    async def boom(session):
        raise RuntimeError("died mid-stream")

    monkeypatch.setattr(chat_router, "get_openai_tools", tools_then_die)

    ask(client, auth_headers)
    monkeypatch.setattr(chat_router, "get_openai_tools", original)

    assert attempts["n"] == 1


def test_the_deadline_stops_a_server_that_is_down_rather_than_asleep(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without this, a dead server holds the request open for the whole
    backoff sequence before admitting defeat."""
    attempts = {"n": 0}

    def always_fail(url, *, http_client=None):
        attempts["n"] += 1
        raise RuntimeError("Server returned an error response")

    install_fakes(monkeypatch, turns=[[text_chunk("unused", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", always_fail)
    monkeypatch.setattr(chat_router, "MCP_RETRY_BACKOFF_SECONDS", (0.05,))
    monkeypatch.setattr(chat_router, "MCP_CONNECT_DEADLINE_SECONDS", 0.12)

    received = events(ask(client, auth_headers))

    # Two sleeps fit inside the deadline, the third would not.
    assert attempts["n"] == 3
    assert attempts["n"] < chat_router.MCP_CONNECT_ATTEMPTS
    assert [e["type"] for e in received] == ["error"]


# --- waking the service ----------------------------------------------------
#
# The retries alone were still not enough: against a sleeping service every
# attempt was refused, even ones landing well after the 41.5s wake. Yet a
# plain httpx2 GET from the same library was *held* for 31.8s and answered
# 200. So the connection is not what wakes the service -- an ordinary request
# is -- and that is now done deliberately.


def test_a_failed_connection_triggers_a_wake(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    wakes = {"n": 0}
    attempts = {"n": 0}

    async def count_wake(settings) -> str:
        wakes["n"] += 1
        return "HTTP 404 after 31.8s"

    def flaky(url, *, http_client=None):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("Server returned an error response")
        return FakeHttpClient(url, http_client=http_client)

    install_fakes(monkeypatch, turns=[[text_chunk("hi", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", flaky)
    monkeypatch.setattr(chat_router, "wake_mcp_server", count_wake)

    received = events(ask(client, auth_headers))

    assert wakes["n"] == 1
    assert [e["type"] for e in received][-1] == "finish-step"


def test_a_healthy_server_is_never_woken(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The wake costs a whole extra request, so it must stay on the sad path."""
    wakes = {"n": 0}

    async def count_wake(settings) -> str:
        wakes["n"] += 1
        return "unexpected"

    install_fakes(monkeypatch, turns=[[text_chunk("hi", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "wake_mcp_server", count_wake)

    ask(client, auth_headers)

    assert wakes["n"] == 0


def test_the_wake_outcome_reaches_the_browser_when_all_else_fails(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Render's logs cannot be read from a laptop, so a failure has to carry
    its own diagnosis."""
    async def wake(settings) -> str:
        return "HTTP 503 after 0.4s"

    def always_fail(url, *, http_client=None):
        raise RuntimeError("Server returned an error response")

    install_fakes(monkeypatch, turns=[[text_chunk("unused", finish_reason="stop")]])
    monkeypatch.setattr(chat_router, "streamable_http_client", always_fail)
    monkeypatch.setattr(chat_router, "wake_mcp_server", wake)

    received = events(ask(client, auth_headers))

    assert [e["type"] for e in received] == ["error"]
    assert "Server returned an error response" in received[0]["errorText"]
    assert "HTTP 503 after 0.4s" in received[0]["errorText"]


def test_the_wake_asks_for_the_service_root_not_the_mcp_path(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any status proves something is listening, and the root avoids opening
    an MCP session that nothing will ever use."""
    import asyncio

    import httpx2 as real_httpx2

    asked: dict[str, str] = {}

    class RecordingClient:
        def __init__(self, **kwargs) -> None:
            asked["timeout"] = kwargs.get("timeout")

        async def __aenter__(self) -> "RecordingClient":
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

        async def get(self, url: str):
            asked["url"] = url
            return SimpleNamespace(status_code=404)

    monkeypatch.setattr(chat_router.httpx2, "AsyncClient", RecordingClient)

    outcome = asyncio.run(real_wake_mcp_server(get_settings()))

    assert asked["url"] == "http://127.0.0.1:8001/"
    assert "HTTP 404" in outcome
    assert isinstance(asked["timeout"], real_httpx2.Timeout)


def test_a_wake_that_itself_fails_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """It runs on the failure path; throwing there would mask the real error."""
    import asyncio

    class Exploding:
        def __init__(self, **kwargs) -> None:
            pass

        async def __aenter__(self) -> "Exploding":
            return self

        async def __aexit__(self, *exc_info: object) -> bool:
            return False

        async def get(self, url: str):
            raise OSError("no route to host")

    monkeypatch.setattr(chat_router.httpx2, "AsyncClient", Exploding)

    outcome = asyncio.run(real_wake_mcp_server(get_settings()))

    assert "OSError" in outcome
    assert "no route to host" in outcome
