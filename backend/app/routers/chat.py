import json
import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from langfuse.openai import AsyncOpenAI
from langfuse import get_client
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.api_schemas import ChatRequest
from app.db_models import User
from app.dependencies import get_current_user
from app.settings import get_settings

router = APIRouter(prefix="/chat",tags=["chat"])

def to_openai_messages(ui_messages: list[dict])-> list[dict]:
    messages = []
    for msg in ui_messages:
        text = "".join(
            part.get("text","")
            for part in msg.get("parts",[])
            if part.get("type") == "text"
        )
        if text:
            messages.append({"role":msg["role"],"content":text})
    return messages


def tool_error_text(result) -> str:
    """Pull the readable message out of a failed tool result."""
    parts = [getattr(block, "text", "") for block in result.content or []]
    text = " ".join(part for part in parts if part).strip()
    return text or "The tool failed without a message."


async def get_openai_tools(session: ClientSession) -> list[dict]:
    tools = await session.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in tools.tools
    ]


async def chat_stream(request: Request, ui_messages: list[dict]):
    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    messages = to_openai_messages(ui_messages)
    langfuse = get_client()

    def event(payload: dict) -> str:
        return f'data:{json.dumps(payload)}\n\n'

    try:
        with langfuse.start_as_current_observation(name="copilot-chat", as_type="agent"):
            async with streamable_http_client(settings.mcp_server_url) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    tools = await get_openai_tools(session)

                    for _ in range(5):
                        text_id = None
                        finish_reason = None
                        # keyed by the tool call's position in this turn, since a
                        # model can request more than one call at once
                        tool_calls: dict[int, dict] = {}

                        yield event({"type": "start-step"})

                        async with await client.chat.completions.create(
                            model=settings.draft_model,
                            messages=messages,
                            tools=tools,
                            stream=True,
                        ) as stream:
                            async for chunk in stream:
                                if await request.is_disconnected():
                                    return
                                choice = chunk.choices[0]
                                delta = choice.delta

                                if choice.finish_reason:
                                    finish_reason = choice.finish_reason

                                text = delta.content
                                if text:
                                    if text_id is None:
                                        text_id = str(uuid.uuid4())
                                        yield event({"type": "text-start", "id": text_id})
                                    yield event({"type": "text-delta", "id": text_id, "delta": text})

                                if delta.tool_calls:
                                    for tc in delta.tool_calls:
                                        if tc.id is not None:
                                            tool_calls[tc.index] = {
                                                "id": tc.id,
                                                "name": tc.function.name,
                                                "arguments": "",
                                            }
                                            yield event({
                                                "type": "tool-input-start",
                                                "toolCallId": tc.id,
                                                "toolName": tc.function.name,
                                            })
                                        entry = tool_calls[tc.index]
                                        if tc.function.arguments:
                                            entry["arguments"] += tc.function.arguments
                                            yield event({
                                                "type": "tool-input-delta",
                                                "toolCallId": entry["id"],
                                                "inputTextDelta": tc.function.arguments,
                                            })

                        if text_id is not None:
                            yield event({"type": "text-end", "id": text_id})
                        yield event({"type": "finish-step"})

                        if finish_reason != "tool_calls":
                            break  # a plain answer -- nothing left to do

                        # OpenAI wants tools run -- do it for real, then loop
                        # back for another step with the results in hand
                        assistant_tool_calls = []
                        tool_result_messages = []
                        for entry in tool_calls.values():
                            args = json.loads(entry["arguments"])
                            yield event({
                                "type": "tool-input-available",
                                "toolCallId": entry["id"],
                                "toolName": entry["name"],
                                "input": args,
                            })
                            assistant_tool_calls.append({
                                "id": entry["id"],
                                "type": "function",
                                "function": {"name": entry["name"], "arguments": entry["arguments"]},
                            })
                            try:
                                result = await session.call_tool(entry["name"], args)
                                if result.is_error:
                                    raise RuntimeError(tool_error_text(result))
                                output = {"structuredContent": result.structured_content}
                                yield event({
                                    "type": "tool-output-available",
                                    "toolCallId": entry["id"],
                                    "output": output,
                                })
                                tool_result_messages.append({
                                    "role": "tool",
                                    "tool_call_id": entry["id"],
                                    "content": json.dumps(output),
                                })
                            except Exception as exc:
                                yield event({
                                    "type": "tool-output-error",
                                    "toolCallId": entry["id"],
                                    "errorText": str(exc),
                                })
                                tool_result_messages.append({
                                    "role": "tool",
                                    "tool_call_id": entry["id"],
                                    "content": f"Error: {exc}",
                                })

                        messages.append({
                            "role": "assistant",
                            "tool_calls": assistant_tool_calls,
                            "content": None,
                        })
                        messages.extend(tool_result_messages)

    except Exception as exc:
        yield event({"type": "error", "errorText": str(exc)})

    langfuse.flush()
    yield "data: [DONE]\n\n"


@router.post("")
async def create_chat(
    payload: ChatRequest,
    request: Request,
    cur_user: User = Depends(get_current_user),
) -> StreamingResponse:
    return StreamingResponse(
        chat_stream(request, payload.messages),
        media_type="text/event-stream",
        headers={"x-vercel-ai-ui-message-stream": "v1"},
    )
