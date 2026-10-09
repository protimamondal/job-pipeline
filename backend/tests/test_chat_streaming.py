"""What `/chat` actually streams back.

Sub-phases 3 and 4 only ever tested that these routes reject an anonymous
request. These tests exercise the real work: the AI SDK event protocol the
frontend's `useChat` depends on, the tool-calling loop, and what happens when
a tool fails. OpenAI and the MCP server are replaced by `tests/fakes.py`.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.routers import chat as chat_router
from tests.fakes import (
    FakeHttpClient,
    FakeLangfuse,
    FakeOpenAI,
    FakeSession,
    FakeToolResult,
    text_chunk,
    tool_call_chunk,
)


def install_fakes(monkeypatch, turns, tool_results=None):
    """Point the chat router at the fakes. Returns them for assertions."""
    openai = FakeOpenAI(turns)
    session = FakeSession(tool_results)
    langfuse = FakeLangfuse()

    monkeypatch.setattr(chat_router, "AsyncOpenAI", lambda **kw: openai)
    monkeypatch.setattr(chat_router, "streamable_http_client", FakeHttpClient)
    monkeypatch.setattr(chat_router, "ClientSession", lambda read, write: session)
    monkeypatch.setattr(chat_router, "get_client", lambda: langfuse)
    return openai, session, langfuse


def events(response) -> list[dict]:
    """Parse the SSE body into the decoded event payloads, dropping [DONE]."""
    parsed = []
    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue
        body = line[len("data:"):].strip()
        if body == "[DONE]":
            continue
        parsed.append(json.loads(body))
    return parsed


def ask(client: TestClient, headers: dict, text: str = "hi"):
    return client.post(
        "/chat",
        json={"messages": [{"role": "user", "parts": [{"type": "text", "text": text}]}]},
        headers=headers,
    )


# --- a plain answer, no tools ---------------------------------------------

def test_plain_answer_streams_the_text_protocol(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fakes(
        monkeypatch,
        turns=[[text_chunk("Hello "), text_chunk("world", finish_reason="stop")]],
    )

    response = ask(client, auth_headers)
    assert response.status_code == 200
    assert response.headers["x-vercel-ai-ui-message-stream"] == "v1"

    received = events(response)
    assert [e["type"] for e in received] == [
        "start-step",
        "text-start",
        "text-delta",
        "text-delta",
        "text-end",
        "finish-step",
    ]

    # The frontend stitches deltas together by id, so they must share one.
    deltas = [e for e in received if e["type"] == "text-delta"]
    assert "".join(e["delta"] for e in deltas) == "Hello world"
    assert len({e["id"] for e in deltas}) == 1

    assert response.text.endswith("data: [DONE]\n\n")


def test_the_stream_ends_with_done_even_when_the_model_sends_nothing(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fakes(monkeypatch, turns=[[]])

    response = ask(client, auth_headers)
    assert response.status_code == 200
    # No text parts at all, so no text-start/end -- but the step still closes.
    assert [e["type"] for e in events(response)] == ["start-step", "finish-step"]
    assert response.text.endswith("data: [DONE]\n\n")


def test_the_user_message_reaches_openai_as_plain_content(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    openai, _, _ = install_fakes(
        monkeypatch, turns=[[text_chunk("ok", finish_reason="stop")]]
    )

    ask(client, auth_headers, text="find me python jobs")

    assert openai.calls[0]["messages"] == [
        {"role": "user", "content": "find me python jobs"}
    ]
    assert openai.calls[0]["stream"] is True


def test_the_mcp_tool_is_offered_to_the_model(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    openai, session, _ = install_fakes(
        monkeypatch, turns=[[text_chunk("ok", finish_reason="stop")]]
    )

    ask(client, auth_headers)

    assert session.initialized
    offered = openai.calls[0]["tools"]
    assert offered[0]["type"] == "function"
    assert offered[0]["function"]["name"] == "search_job"
    assert "title" in offered[0]["function"]["parameters"]["properties"]


# --- the tool-calling loop ------------------------------------------------

def test_a_tool_call_runs_and_its_result_is_streamed(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    jobs = {"result": [{"company": "ACME", "title": "Python Developer"}]}
    openai, session, _ = install_fakes(
        monkeypatch,
        turns=[
            [
                tool_call_chunk("call_1", "search_job", '{"title":"python"'),
                tool_call_chunk(
                    None, None, ',"location":"berlin"}', finish_reason="tool_calls"
                ),
            ],
            [text_chunk("I found one job.", finish_reason="stop")],
        ],
        tool_results=[FakeToolResult(structured_content=jobs)],
    )

    response = ask(client, auth_headers)
    received = events(response)

    assert [e["type"] for e in received] == [
        "start-step",
        "tool-input-start",
        "tool-input-delta",
        "tool-input-delta",
        "finish-step",
        "tool-input-available",
        "tool-output-available",
        "start-step",
        "text-start",
        "text-delta",
        "text-end",
        "finish-step",
    ]

    # The tool really ran, with the streamed JSON fragments reassembled.
    assert session.tool_calls == [
        ("search_job", {"title": "python", "location": "berlin"})
    ]

    available = next(e for e in received if e["type"] == "tool-input-available")
    assert available["toolName"] == "search_job"
    assert available["input"] == {"title": "python", "location": "berlin"}

    # CoPilotPanel.tsx reads output.structuredContent.result -- that path must exist.
    output = next(e for e in received if e["type"] == "tool-output-available")
    assert output["output"]["structuredContent"] == jobs
    assert output["toolCallId"] == "call_1"

    # The second turn must carry the tool's result back to the model.
    second = openai.calls[1]["messages"]
    assert second[1]["role"] == "assistant"
    assert second[1]["tool_calls"][0]["function"]["name"] == "search_job"
    assert second[2]["role"] == "tool"
    assert second[2]["tool_call_id"] == "call_1"
    assert "ACME" in second[2]["content"]


def test_a_failed_tool_streams_an_error_not_a_null_success(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression test for a real bug.

    `ClientSession.call_tool` does not raise when a tool fails -- it returns a
    result with `is_error=True` and `structured_content=None`. Before this was
    handled, the router reported a failure to the browser as a successful
    `tool-output-available` carrying a null payload, which crashes
    `CoPilotPanel.tsx` at `.structuredContent.result`.
    """
    message = "Job search is temporarily unavailable. Please try again in a moment."
    openai, _, _ = install_fakes(
        monkeypatch,
        turns=[
            [
                tool_call_chunk(
                    "call_1",
                    "search_job",
                    '{"title":"python","location":"berlin"}',
                    finish_reason="tool_calls",
                ),
            ],
            [text_chunk("Sorry, search is down.", finish_reason="stop")],
        ],
        tool_results=[FakeToolResult(is_error=True, text=message)],
    )

    received = events(ask(client, auth_headers))
    types = [e["type"] for e in received]

    assert "tool-output-error" in types
    assert "tool-output-available" not in types

    error = next(e for e in received if e["type"] == "tool-output-error")
    assert error["errorText"] == message
    assert error["toolCallId"] == "call_1"

    # The model is told, so it can apologise instead of inventing jobs.
    assert openai.calls[1]["messages"][2]["content"] == f"Error: {message}"


def test_a_tool_error_with_no_message_still_reports_something(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fakes(
        monkeypatch,
        turns=[
            [
                tool_call_chunk(
                    "call_1",
                    "search_job",
                    '{"title":"python","location":"berlin"}',
                    finish_reason="tool_calls",
                ),
            ],
            [text_chunk("Sorry.", finish_reason="stop")],
        ],
        tool_results=[FakeToolResult(is_error=True)],
    )

    received = events(ask(client, auth_headers))
    error = next(e for e in received if e["type"] == "tool-output-error")
    assert error["errorText"] == "The tool failed without a message."


def test_two_tool_calls_in_one_turn_are_kept_apart(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model can request several calls at once, dribbling both in parallel.

    This is why the router keys in-flight calls by `index` and not by id.
    """
    openai, session, _ = install_fakes(
        monkeypatch,
        turns=[
            [
                tool_call_chunk("call_1", "search_job", '{"title":"python",', index=0),
                tool_call_chunk("call_2", "search_job", '{"title":"react",', index=1),
                tool_call_chunk(None, None, '"location":"berlin"}', index=0),
                tool_call_chunk(
                    None,
                    None,
                    '"location":"remote"}',
                    index=1,
                    finish_reason="tool_calls",
                ),
            ],
            [text_chunk("Found some.", finish_reason="stop")],
        ],
        tool_results=[
            FakeToolResult(structured_content={"result": ["berlin job"]}),
            FakeToolResult(structured_content={"result": ["remote job"]}),
        ],
    )

    received = events(ask(client, auth_headers))

    assert session.tool_calls == [
        ("search_job", {"title": "python", "location": "berlin"}),
        ("search_job", {"title": "react", "location": "remote"}),
    ]

    outputs = [e for e in received if e["type"] == "tool-output-available"]
    assert [e["toolCallId"] for e in outputs] == ["call_1", "call_2"]


def test_the_tool_loop_is_capped_at_five_rounds(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A model that asks for a tool forever must not loop forever."""
    openai, session, _ = install_fakes(
        monkeypatch,
        turns=[
            [
                tool_call_chunk(
                    "call_x",
                    "search_job",
                    '{"title":"python","location":"berlin"}',
                    finish_reason="tool_calls",
                ),
            ]
            for _ in range(5)
        ],
        tool_results=[
            FakeToolResult(structured_content={"result": []}) for _ in range(5)
        ],
    )

    response = ask(client, auth_headers)

    assert len(openai.calls) == 5
    assert len(session.tool_calls) == 5
    # It stops cleanly rather than erroring out.
    assert response.text.endswith("data: [DONE]\n\n")


# --- failures outside the tool loop ---------------------------------------

def test_an_mcp_server_that_is_down_streams_one_error_event(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If the MCP server is unreachable the request must not 500 mid-stream.

    The status line is already sent by then, so the only way to tell the
    browser is an `error` event followed by `[DONE]`.
    """
    install_fakes(monkeypatch, turns=[[text_chunk("unused", finish_reason="stop")]])

    def refuse(url):
        raise ConnectionError("All connection attempts failed")

    monkeypatch.setattr(chat_router, "streamable_http_client", refuse)

    response = ask(client, auth_headers)
    assert response.status_code == 200

    received = events(response)
    assert [e["type"] for e in received] == ["error"]
    assert "connection attempts failed" in received[0]["errorText"]
    assert response.text.endswith("data: [DONE]\n\n")


def test_langfuse_wraps_the_whole_turn_in_one_observation(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sub-phase 4 made several OpenAI calls nest under a single trace."""
    _, _, langfuse = install_fakes(
        monkeypatch,
        turns=[
            [
                tool_call_chunk(
                    "call_1",
                    "search_job",
                    '{"title":"python","location":"berlin"}',
                    finish_reason="tool_calls",
                ),
            ],
            [text_chunk("done", finish_reason="stop")],
        ],
        tool_results=[FakeToolResult(structured_content={"result": []})],
    )

    ask(client, auth_headers)

    # Two OpenAI calls, one observation around both.
    assert langfuse.observations == ["copilot-chat"]
    assert langfuse.flushed == 1
