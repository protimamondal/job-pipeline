# Phase 3 — Sub-phase 3: draft streaming SSE contract

This records the wire contract used for moving cover-letter generation from
the Next.js route (`web/app/api/draft/route.ts`) to FastAPI. It exists
separately from `PHASE3.md` because it's a design decision worth keeping
around for reference, not a checklist item.

**Revision note:** the first version of this document specified a custom,
hand-invented contract (`{"type": "delta"/"error"/"done", ...}`). That was
implemented and verified working, but was later replaced with what's
documented below — the AI SDK's own real Data Stream / UI Message Stream
Protocol — after confirming two things: the AI SDK's own docs
(`node_modules/ai/docs/04-ai-sdk-ui/50-stream-protocol.mdx`) explicitly
document this protocol as intended for custom backends "implemented in a
different language such as Python," with an official FastAPI example; and
`web/app/api/chat/route.ts` (copilot) already speaks this exact protocol
today, so implementing it correctly here is directly reusable when copilot
moves to FastAPI in sub-phase 4, whereas the custom contract was a dead end
that only ever served this one endpoint.

## The contract

Standard SSE framing (`data: <json>\n\n`, blank-line delimited), matching
the AI SDK's `uiMessageChunkSchema`. A response streaming from a custom
backend must set the header:

```
x-vercel-ai-ui-message-stream: v1
```

Text content uses a start/delta/end pattern, all three sharing one `id` per
message:

| `type` | When | Payload |
|---|---|---|
| `text-start` | Once, before any text | `{"type": "text-start", "id": "..."}` |
| `text-delta` | A chunk of generated text arrives | `{"type": "text-delta", "id": "...", "delta": "..."}` |
| `text-end` | Once, generation finished successfully | `{"type": "text-end", "id": "..."}` |
| `error` | Generation failed partway (OpenAI error, connection drop) | `{"type": "error", "errorText": "..."}` |

The stream always ends with the literal termination marker, after either the
`text-end` or the `error` event:

```
data: [DONE]
```

Example trace for a short response that completes normally:

```
data: {"type": "text-start", "id": "a3f9..."}

data: {"type": "text-delta", "id": "a3f9...", "delta": "Dear"}

data: {"type": "text-delta", "id": "a3f9...", "delta": " hiring"}

data: {"type": "text-end", "id": "a3f9..."}

data: [DONE]

```

Field names are not negotiable — they're fixed by the AI SDK's own schema
(`web/node_modules/ai/src/ui-message-stream/ui-message-chunks.ts`), which
`useCompletion`/`useChat` validate incoming chunks against. `delta` (not
`text`), `errorText` (not `message`), and the literal `type` strings above
are all required exactly as spelled, or the chunk fails validation and the
whole stream throws client-side.

## Cancellation

Not a wire event — the server can't announce anything to a client that's
already gone. Handled by two things together: `await request.is_disconnected()`
checked inside the loop pulling chunks from OpenAI, breaking out the moment
it's true; and wrapping the OpenAI call in `async with ... as stream:` so the
connection to OpenAI is deterministically closed on exit — normal
completion, an early `break`, or an exception — rather than left for garbage
collection to eventually clean up. This is stricter than the original
Next.js route, which aborted the browser connection on Stop but never passed
an `abortSignal` into `streamText`, so the upstream OpenAI call was never
actually cancelled there.

## Consequence for the frontend

Because this matches `useCompletion`'s own expected shape exactly, no manual
stream-reading code is needed at all. The only frontend change was removing
the `streamProtocol: "text"` override in `DraftPanel.tsx`, letting the hook
fall back to its default `'data'` mode — its built-in parser
(`web/node_modules/ai/src/ui/call-completion-api.ts`) handles the SSE
framing, the buffering across network chunks, and updating `completion`/
`error` state, all on its own.

## Status

Implemented and verified end-to-end: real login through the Next.js auth
routes, a real request through the Next.js proxy to FastAPI, a real OpenAI
call, and all 231 frames of a real response validated successfully against
the AI SDK's actual `uiMessageChunkSchema` (0 invalid), with the
reconstructed text confirmed to read as a coherent cover letter. Sub-phase 3
step 6 (Langfuse tracing) is the remaining open item.
