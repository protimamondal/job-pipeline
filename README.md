# AI Job Pipeline

A job-application product with two AI features built into it: a **copilot** that
searches jobs through a Model Context Protocol tool and renders the tool's
progress as UI, and a **cover-letter assistant** that streams markdown and links
each claim back to a visible source.

Both AI surfaces are built with the Vercel AI SDK. The MCP server is written by
hand in Python — not a wrapper around a library example.

| | |
|---|---|
| **Live app** | _add the Vercel URL after deploying_ |
| **MCP endpoint** | _add the Render URL after deploying_ |
| **Stack** | Next.js 16, React 19, TypeScript, Vercel AI SDK 7, Tailwind 4, Python 3.13, MCP 2.0 |

> The job listings and the MCP search results are fixed sample data. The AI
> calls, the streaming, the tool protocol and the failure handling are all real.

## What is actually interesting here

Most AI demos stream text into a box. The work in this repo is the part that
comes after that — what the interface does when the model is slow, wrong, or
cut off halfway.

**Streaming markdown that is never broken.** Markdown arrives one token at a
time, so at any moment the buffer may hold a half-open `**` or an unclosed list.
Rendering that naively makes the page flicker. Streamdown repairs incomplete
markdown, and a small helper hides the one marker case it cannot repair.

**Three different failures, three different screens.** A failure before any
response, a failure in the middle of a stream, and a failure inside an MCP tool
call are not the same event and should not look the same. When a stream dies
halfway, the text that already arrived stays on screen — throwing away partial
work the user was already reading is the wrong default.

**Tool calls as UI, not prose.** An MCP tool call moves through preparing,
searching, result, cancelled and error states. Each renders as its own UI state,
so the user can see what the assistant is doing rather than reading about it
afterwards.

**Citations that point at something.** The model emits source markers, which
become clickable chips that highlight the originating job description or
profile section next to the letter — so a claim can be checked without trusting
it.

**Controls that cannot race.** Copy, regenerate and edit are disabled while a
response streams, so two writers can never fight over the same draft.

## Architecture

```text
Browser
  |
  +-- job list / detail pages (Next.js, sample data)
  |
  +-- /api/draft --- Vercel AI SDK ---> OpenAI
  |
  +-- /api/chat  --- Vercel AI SDK ---> MCP client
                                         |
                                         +--> Python MCP 2.0 server (Render)
```

Both API routes run on the Next.js **server**. The provider key and the MCP URL
are server-side environment variables and never reach browser JavaScript.

```text
web/          Next.js frontend and both API routes
mcp-server/   Python MCP 2.0 server exposing the job-search tool
```

## Run it locally

Requires Node.js 22+, Python 3.13+, [uv](https://docs.astral.sh/uv/), and an
OpenAI API key.

Terminal 1 — the MCP server:

```bash
cd mcp-server
uv sync --frozen
uv run python server.py     # http://127.0.0.1:8001/mcp
```

Terminal 2 — the frontend:

```bash
cd web
nvm use
printf 'OPENAI_API_KEY=sk-your-key\n' > .env.local
npm ci
npm run dev                 # http://localhost:3000
```

`MCP_SERVER_URL` defaults to the local server, so nothing else is needed.

## Deploy

**MCP server → Render.** Create a Blueprint from this repository. The
`render.yaml` at the repository root builds `mcp-server/` as a Docker service.

**Frontend → Vercel.** Import this repository and set the project **Root
Directory** to `web`. Add two Production environment variables:

| Variable | Value |
|---|---|
| `OPENAI_API_KEY` | your OpenAI key |
| `MCP_SERVER_URL` | `https://<render-service>.onrender.com/mcp` |

Then check both surfaces on the live URL: a cover letter that streams, and a
copilot job search that shows the tool running.

## Known limitations

Kept deliberately, and listed rather than hidden:

- The MCP endpoint is unauthenticated. That is only acceptable because the tool
  returns fixed sample data. Anything touching real user data needs auth in
  front of it first.
- Copy and Edit still carry the converted citation link syntax.
- A citation marker can flash raw while only part of it has streamed.
- An unrecognised citation marker is not dropped yet.
- Citations resolve to a whole job or profile source, not to individual lines.
- Message branching is understood as a data-model consequence — regenerating
  from earlier state creates a tree — but the version-navigation UI is not built.

Citation accuracy is not a meaningful measurement yet: the prompt permits only
two fixed source identifiers. Validating a citation per retrieved chunk is a
retrieval problem, and belongs with the RAG work rather than here.

## Background

Built by **[Protima Mondal](https://github.com/protimamondal)** as the Phase 2
project of a structured AI engineering programme. The learning log, roadmap and
notes behind it are in
[ai-engineering-journey](https://github.com/protimamondal/ai-engineering-journey).
