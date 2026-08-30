# AI Job Pipeline

A small job-pipeline product with two embedded AI features:

- a copilot that discovers an MCP job-search tool at runtime and renders tool
  progress and results as UI;
- a cover-letter assistant that streams markdown, supports copy/regenerate/edit,
  preserves partial output on failure, and links claims to visible sources.

This is the Phase 2 frontend of a structured AI engineering programme. Phase 3
replaces its stub data and direct provider calls with a real FastAPI service.

## Architecture

```text
Browser
  |
  +-- job list/detail pages (Next.js stub data)
  |
  +-- /api/draft -- Vercel AI SDK --> OpenAI
  |
  +-- /api/chat  -- Vercel AI SDK --> MCP client
                                      |
                                      +--> Python MCP 2.0 server on Render
```

Both API routes run on the Next.js server. Provider keys and the MCP URL are
therefore server-side variables and never enter browser JavaScript.

## Run locally

Requirements: Node.js 22+, npm, Python 3.13+, uv, and an OpenAI API key.

Start the MCP server:

```bash
cd ../mcp-server
uv sync --frozen
uv run python server.py
```

Start the frontend in another terminal:

```bash
cd ../web
nvm use
printf 'OPENAI_API_KEY=replace-me\n' > .env.local
npm ci
npm run dev
```

`MCP_SERVER_URL` defaults to `http://127.0.0.1:8001/mcp` locally.

## Production deployment

1. In Render, create a Blueprint from this repository. The `render.yaml` at the
   repository root builds `mcp-server/`.
2. Import this repository into Vercel and set the project Root Directory to
   `web`.
3. Add these Vercel environment variables for Production:
   - `OPENAI_API_KEY`
   - `MCP_SERVER_URL=https://<render-service>.onrender.com/mcp`
4. Deploy, then verify both the cover-letter stream and a copilot job search.

The public MCP endpoint is unauthenticated. That is acceptable only because
the current tool returns fixed fake data; Phase 3 must put authentication in
front of any real tool or user data.

## The six Phase 2 UI decisions

1. **Streaming markdown:** Streamdown renders incomplete markdown; a small
   helper hides the one empty marker it cannot repair cleanly.
2. **Copy, regenerate, edit:** controls are disabled during streaming so two
   writers cannot race over the same draft.
3. **Message branching:** the data-model consequence is understood—regenerating
   from old state creates a tree—but the full version-navigation UI is deferred.
4. **Partial failure:** failures before a response, in-stream failures, and MCP
   tool failures have separate UI states. Partial useful text stays visible.
5. **Optimistic tool UI:** MCP tool parts render preparing, searching, result,
   cancellation, and error states instead of collapsing everything into prose.
6. **Citation UX:** model markers become clickable chips that highlight the
   job description or candidate-profile source outside the letter.

## Known deferred polish

- Copy and Edit currently preserve converted citation-link syntax.
- A citation marker can flash raw while only part of it has streamed.
- An unknown citation marker is not yet dropped.
- Citations identify the whole job/profile source rather than individual lines.

The citation-invention rate is not meaningful yet: the prompt permits only two
fixed source identifiers. Per-retrieved-chunk citation validation belongs to
the Phase 4 RAG work.
