"""What `/jobs/{job_id}/draft` actually streams back.

Sub-phase 3 built this route and left its tests at "401 without a token",
noting that testing the real behaviour needed `AsyncOpenAI` mocked. That is
what `tests/fakes.py` provides, so these are the tests that gap was about:
the AI SDK text protocol, the prompt the model is actually handed, and what
the browser receives when OpenAI fails mid-stream.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.routers import drafts as drafts_router
from tests.fakes import FakeLangfuse, FakeOpenAI, text_chunk


def install_fakes(monkeypatch, turns):
    """Point the drafts router at the fakes. Returns them for assertions."""
    openai = FakeOpenAI(turns)
    langfuse = FakeLangfuse()
    monkeypatch.setattr(drafts_router, "AsyncOpenAI", lambda **kw: openai)
    monkeypatch.setattr(drafts_router, "get_client", lambda: langfuse)
    return openai, langfuse


def events(response) -> list[dict]:
    parsed = []
    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue
        body = line[len("data:"):].strip()
        if body == "[DONE]":
            continue
        parsed.append(json.loads(body))
    return parsed


def request_draft(client: TestClient, headers: dict, job_id: int = 1, instruction=None):
    return client.post(
        f"/jobs/{job_id}/draft",
        json={"instruction": instruction},
        headers=headers,
    )


# --- the happy path -------------------------------------------------------

def test_a_draft_streams_back_as_text_parts(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fakes(
        monkeypatch,
        turns=[
            [
                text_chunk("Dear hiring manager, "),
                text_chunk("I am applying for the role."),
            ]
        ],
    )

    response = request_draft(client, auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    received = events(response)
    assert [e["type"] for e in received] == [
        "text-start",
        "text-delta",
        "text-delta",
        "text-end",
    ]

    deltas = [e for e in received if e["type"] == "text-delta"]
    assert "".join(e["delta"] for e in deltas) == (
        "Dear hiring manager, I am applying for the role."
    )

    # Every part of one draft must share an id for the frontend to assemble it.
    assert len({e["id"] for e in received}) == 1
    assert response.text.endswith("data: [DONE]\n\n")


def test_empty_chunks_are_not_streamed_as_deltas(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """OpenAI sends chunks with no content (role-only, or the final one)."""
    install_fakes(
        monkeypatch,
        turns=[[text_chunk(None), text_chunk("Real text."), text_chunk("")]],
    )

    received = events(request_draft(client, auth_headers))
    assert [e["type"] for e in received] == ["text-start", "text-delta", "text-end"]


# --- the prompt -----------------------------------------------------------

def test_the_prompt_carries_the_job_and_the_profile(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    openai, _ = install_fakes(monkeypatch, turns=[[text_chunk("draft")]])

    request_draft(client, auth_headers, job_id=1)

    sent = openai.calls[0]["messages"][0]["content"]
    # Job 1 is the first row in seed_data.JOBS.
    assert "Senior Frontend Engineer" in sent
    assert "customer-facing dashboard" in sent
    # And the citation markers the frontend renders.
    assert "[[job]]" in sent
    assert "[[profile]]" in sent
    assert openai.calls[0]["stream"] is True


def test_an_extra_instruction_is_appended_to_the_prompt(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    openai, _ = install_fakes(monkeypatch, turns=[[text_chunk("draft")]])

    request_draft(client, auth_headers, instruction="Keep it under 100 words.")

    sent = openai.calls[0]["messages"][0]["content"]
    assert "Extra user instruction: Keep it under 100 words." in sent


def test_no_instruction_leaves_the_prompt_clean(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    openai, _ = install_fakes(monkeypatch, turns=[[text_chunk("draft")]])

    request_draft(client, auth_headers, instruction=None)

    assert "Extra user instruction" not in openai.calls[0]["messages"][0]["content"]


def test_each_job_gets_its_own_prompt(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    openai, _ = install_fakes(
        monkeypatch, turns=[[text_chunk("one")], [text_chunk("two")]]
    )

    request_draft(client, auth_headers, job_id=1)
    request_draft(client, auth_headers, job_id=2)

    first = openai.calls[0]["messages"][0]["content"]
    second = openai.calls[1]["messages"][0]["content"]
    assert "Senior Frontend Engineer" in first
    assert "Staff Engineer, Web Platform" in second


# --- failures -------------------------------------------------------------

def test_a_job_that_does_not_exist_is_404(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Checked before the stream opens, so a real status code is still possible."""
    openai, _ = install_fakes(monkeypatch, turns=[[text_chunk("unused")]])

    response = request_draft(client, auth_headers, job_id=9999)

    assert response.status_code == 404
    # No money spent on a job that is not there.
    assert openai.calls == []


def test_openai_failing_mid_stream_sends_an_error_event_not_a_500(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """By the time the model fails, 200 and the headers are already sent.

    The only way left to tell the browser is an `error` event, followed by
    `[DONE]` so the client stops waiting.
    """
    install_fakes(monkeypatch, turns=[])  # asking for a turn raises

    response = request_draft(client, auth_headers)
    assert response.status_code == 200

    received = events(response)
    assert received[-1]["type"] == "error"
    assert "scripted" in received[-1]["errorText"]
    assert response.text.endswith("data: [DONE]\n\n")


def test_the_trace_is_flushed_once_per_draft(
    client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`flush()` is synchronous.

    Sub-phase 4 found this awaited by mistake, which raised `TypeError` and
    killed the stream right before `[DONE]` -- so the test asserts both that
    it ran and that the stream finished.
    """
    _, langfuse = install_fakes(monkeypatch, turns=[[text_chunk("draft")]])

    response = request_draft(client, auth_headers)

    assert langfuse.flushed == 1
    assert response.text.endswith("data: [DONE]\n\n")
