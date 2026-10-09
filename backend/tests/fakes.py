"""Stand-ins for the paid, non-deterministic services the AI routes call.

`/chat` and `/jobs/{job_id}/draft` talk to OpenAI and to the MCP server. Both
are real network calls, one of them costs money per request, and neither
returns the same thing twice, so the tests replace them with these.

The shapes here mirror only what the routers actually touch: the routers read
`chunk.choices[0].delta.content`, so that is what a chunk has.
"""

from types import SimpleNamespace
from typing import Any


# --- OpenAI streaming ------------------------------------------------------

def text_chunk(text: str, finish_reason: str | None = None) -> SimpleNamespace:
    """One streamed chunk carrying a piece of the assistant's answer."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                delta=SimpleNamespace(content=text, tool_calls=None),
            )
        ]
    )


def tool_call_chunk(
    call_id: str | None,
    name: str | None,
    arguments: str,
    index: int = 0,
    finish_reason: str | None = None,
) -> SimpleNamespace:
    """One streamed chunk carrying part of a tool call.

    OpenAI sends the id and name once and then dribbles the JSON arguments
    across later chunks with `id=None`, which is why the routers key tool
    calls by `index` rather than by id.
    """
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                finish_reason=finish_reason,
                delta=SimpleNamespace(
                    content=None,
                    tool_calls=[
                        SimpleNamespace(
                            id=call_id,
                            index=index,
                            function=SimpleNamespace(name=name, arguments=arguments),
                        )
                    ],
                ),
            )
        ]
    )


class FakeStream:
    """What `await client.chat.completions.create(...)` returns.

    The routers use it as `async with await create(...) as stream:` and then
    `async for chunk in stream`, so it is both an async context manager and
    an async iterator.
    """

    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks

    async def __aenter__(self) -> "FakeStream":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def __aiter__(self):
        for chunk in self._chunks:
            yield chunk


class FakeOpenAI:
    """Replaces `AsyncOpenAI`, returning scripted turns.

    `turns` is one list of chunks per expected call, so a tool-calling test
    scripts two: the turn that asks for the tool, then the turn that answers
    with the tool's result in hand. `calls` records the kwargs each time, so a
    test can assert on the messages the router built.
    """

    def __init__(self, turns: list[list[Any]]) -> None:
        self._turns = list(turns)
        self.calls: list[dict] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **kwargs: Any) -> FakeStream:
        self.calls.append(kwargs)
        if not self._turns:
            raise AssertionError("the router asked for more turns than were scripted")
        return FakeStream(self._turns.pop(0))


# --- MCP -------------------------------------------------------------------

class FakeToolResult:
    def __init__(
        self,
        structured_content: Any = None,
        is_error: bool = False,
        text: str | None = None,
    ) -> None:
        self.structured_content = structured_content
        self.is_error = is_error
        self.content = [SimpleNamespace(text=text)] if text is not None else []


class FakeSession:
    """Replaces `mcp.ClientSession`.

    `tool_results` is one result per `call_tool`. Note a failing MCP tool does
    NOT raise: it comes back as a result with `is_error=True`, which is the
    bug this suite guards against.
    """

    def __init__(self, tool_results: list[FakeToolResult] | None = None) -> None:
        self._tool_results = list(tool_results or [])
        self.tool_calls: list[tuple[str, dict]] = []
        self.initialized = False

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    async def initialize(self) -> None:
        self.initialized = True

    async def list_tools(self) -> SimpleNamespace:
        return SimpleNamespace(
            tools=[
                SimpleNamespace(
                    name="search_job",
                    description="search for job openings by title and location",
                    input_schema={
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "location": {"type": "string"},
                        },
                        "required": ["title", "location"],
                    },
                )
            ]
        )

    async def call_tool(self, name: str, args: dict) -> FakeToolResult:
        self.tool_calls.append((name, args))
        if not self._tool_results:
            raise AssertionError("the router called more tools than were scripted")
        return self._tool_results.pop(0)


class FakeHttpClient:
    """Replaces `streamable_http_client`, which yields a stream pair."""

    def __init__(self, url: str) -> None:
        self.url = url

    async def __aenter__(self) -> tuple[object, object]:
        return (object(), object())

    async def __aexit__(self, *exc_info: object) -> bool:
        return False


# --- Langfuse --------------------------------------------------------------

class FakeLangfuse:
    """Replaces the Langfuse client so tests make no network calls.

    `start_as_current_observation` is a plain context manager in the real
    client too, not an async one.
    """

    def __init__(self) -> None:
        self.observations: list[str] = []
        self.flushed = 0

    def start_as_current_observation(self, name: str = "", as_type: str = "", **kw):
        self.observations.append(name)
        return self

    def __enter__(self) -> "FakeLangfuse":
        return self

    def __exit__(self, *exc_info: object) -> bool:
        return False

    def flush(self) -> None:
        self.flushed += 1

    def update_current_trace(self, **kwargs: Any) -> None:
        pass


# --- Redis -----------------------------------------------------------------

class FakeRedis:
    """An in-memory stand-in for the commands the rate limiter uses.

    Two reasons the tests do not talk to the real Redis container:

    1. `app.cache.redis_client` is created once at import time, and
       `TestClient` runs every request on a fresh event loop, so a pooled
       connection from an earlier request belongs to a loop that is already
       closed. Under uvicorn there is one loop for the process lifetime, so
       this is a testing artefact, not a production bug.
    2. A suite that needs a running container cannot run in CI unchanged.

    The semantics below are the ones the limiter depends on: INCR creates a
    missing key at 0 and returns the value *after* incrementing, and a key
    created by INCR has no expiry until EXPIRE is called (TTL -1).
    """

    def __init__(self) -> None:
        self.values: dict[str, int] = {}
        self.ttls: dict[str, int] = {}
        self.commands: list[tuple] = []
        # Set to a redis exception instance to make every command raise it.
        self.failure: Exception | None = None
        # Set to make only EXPIRE fail, leaving INCR working.
        self.expire_failure: Exception | None = None

    def _check(self) -> None:
        if self.failure is not None:
            raise self.failure

    async def incr(self, key: str) -> int:
        self._check()
        self.commands.append(("incr", key))
        self.values[key] = self.values.get(key, 0) + 1
        return self.values[key]

    async def expire(self, key: str, seconds: int) -> bool:
        if self.expire_failure is not None:
            raise self.expire_failure
        self._check()
        self.commands.append(("expire", key, seconds))
        if key not in self.values:
            return False
        self.ttls[key] = seconds
        return True

    async def ttl(self, key: str) -> int:
        self._check()
        if key not in self.values:
            return -2  # no such key
        return self.ttls.get(key, -1)  # -1 means "exists, never expires"

    async def get(self, key: str):
        self._check()
        value = self.values.get(key)
        return None if value is None else str(value)

    async def set(self, key: str, value, ex: int | None = None) -> bool:
        self._check()
        self.commands.append(("set", key, ex))
        self.values[key] = value
        if ex is not None:
            self.ttls[key] = ex
        return True

    async def exists(self, key: str) -> int:
        self._check()
        return 1 if key in self.values else 0

    async def delete(self, key: str) -> int:
        self._check()
        self.ttls.pop(key, None)
        return 1 if self.values.pop(key, None) is not None else 0

    async def ping(self) -> bool:
        self._check()
        return True
