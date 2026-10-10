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

import httpx2
import pytest
from fastapi.testclient import TestClient

from app.routers import chat as chat_router
from app.routers.chat import unwrap
from app.settings import get_settings
from tests.fakes import FakeLangfuse, FakeOpenAI, FakeSession, text_chunk
from tests.test_chat_streaming import ask, events, install_fakes

# What the cold start actually measured, twice, against the deployed service.
OBSERVED_COLD_START_SECONDS = 31.4


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
    assert received[0]["errorText"] == "connect timed out"
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
