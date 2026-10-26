# Phase 4 — RAG End-to-End

Phase 4 adds retrieval-augmented generation to this product: a document Q&A
surface over real job descriptions, the user's resume, and their application
notes. It is built into `job-pipeline`, not as a separate app. Theory was
studied 2026-10-17 → 2026-10-22 (revision notes in the Drive folder
`phase4-revision`, files `01` to `08`); progress tracking lives in the study
repository.

## How sessions work

- "Start part N" or "implement part N" in this repo means follow the matching
  checklist below.
- RAG is new to Protima. Before each part, explain in plain words what is being
  built and why, linked to the revision note it uses. Then give one small task
  at a time. Do not move on until the current task runs.
- Protima types the code. The coding agent explains, reviews, tests, and
  debugs unless explicitly asked to write it.
- Explain only the new layer (RAG, pgvector, the SDK call being added), not the
  FastAPI/React code around it that she already knows.
- Each part ends with something runnable, a test, and a commit, with this file
  updated in the same commit.

## Approach

Build a simple RAG end to end first (parts 1–5), so the whole flow is visible
once. Then measure it (part 6). Then improve one thing at a time and measure
again after each (parts 7–10), so every improvement has a number behind it.

## Target architecture

```text
Browser / Next.js (`web/`)  — Q&A screen with clickable citations
          |
          v
FastAPI application (`backend/`)
  ingestion:  document -> chunks -> embeddings -> Postgres (pgvector)
  question:   rewrite -> hybrid search (vector + full-text, RRF)
              -> metadata filter -> rerank -> answer with citations
  |            |              |             |          |
Postgres     OpenAI         OpenAI        Cohere     Mem0
+ pgvector   embeddings     generation    Rerank     (memory, in Postgres)
                             |
                          Langfuse
```

Postgres stays the single database: chunks, vectors, and metadata live next to
the existing `jobs`, `users`, and `applications` tables.

## Decisions (2026-10-26)

- **Corpus.** The 7 seeded jobs and one hard-coded profile are too small for
  retrieval to be meaningful or for eval numbers to say anything. Add about 100
  real jobs imported from Arbeitnow (the API the MCP server already uses), a
  per-user resume entered as pasted text (PDF upload later, if at all), and the
  user's application notes.
- **Vector store.** pgvector in the existing Postgres, not a separate vector
  database. Same database, same backups, same connection; the scale here is
  small.
- **Embedding model.** OpenAI, because the product already uses OpenAI. The same
  model must embed both stored chunks and questions.
- **Reranker.** A hosted API (Cohere Rerank). A self-hosted cross-encoder needs
  PyTorch, which does not fit Render's free instance.
- **Privacy.** Every retrieval query filters by `user_id` from the first search
  onward. One user's resume or notes must never reach another user's answer.

## Parts

### 1 — Setup and documents

**Status:** Not started

**Build:** pgvector available locally and on Render; a `documents` table; about
100 Arbeitnow jobs imported; a way for a user to save their resume as text.

**Acceptance:** `CREATE EXTENSION vector` succeeds locally and in production;
the documents table holds jobs, a resume, and application notes for a test user.

### 2 — Chunking

**Status:** Not started

**Build:** a chunking function. Structural for resumes (one chunk per section),
with recursive splitting inside any section that is too long; recursive with
overlap for job descriptions. Revision note `01`.

**Acceptance:** unit tests on real text; the chunks are printed and read by eye
before they are embedded.

### 3 — Embeddings and storage

**Status:** Not started

**Build:** a `chunks` table with `text`, `embedding vector(...)`, and metadata
(`user_id`, `doc_type`, `job_id`, `document_id`) via an Alembic migration; an
ingestion step that embeds each chunk and saves it; an HNSW index. Notes `02`,
`03`.

**Acceptance:** every document has chunks with embeddings; `EXPLAIN` shows the
HNSW index in use.

### 4 — First search

**Status:** Not started

**Build:** an endpoint that embeds a question and returns the top 5 nearest
chunks, always filtered by the current user. Notes `02`, `04`.

**Acceptance:** realistic questions return sensible chunks; a second user never
sees the first user's chunks (tested).

### 5 — Answer with citations

**Status:** Not started

**Build:** a streaming Q&A endpoint that tags retrieved chunks as `[Chunk N]`
and instructs the model to cite them; a Q&A screen whose citations link to the
source document. Traced in Langfuse. Note `05`.

**Acceptance:** simple RAG works end to end in the browser, with citations that
point at real chunks.

### 6 — Retrieval evals (baseline)

**Status:** Not started

**Build:** a golden set of about 30–50 questions, each with its correct
chunk(s) marked by hand; a script that reports hit rate and MRR. Note `06`.

**Acceptance:** baseline numbers recorded in this file.

### 7 — Hybrid search and more filters

**Status:** Not started

**Build:** Postgres full-text search alongside vector search, merged with
reciprocal rank fusion; filters by document type and job. Note `04`.

**Acceptance:** eval numbers recorded next to the baseline.

### 8 — Query rewriting

**Status:** Not started

**Build:** an LLM step that rewrites the question before retrieval; start with
plain rephrasing, try HyDE alongside the original question if it helps. Note
`04`.

**Acceptance:** eval numbers recorded; keep the step only if it helps.

### 9 — Reranking

**Status:** Not started

**Build:** take the top 20, score each question-and-chunk pair with Cohere
Rerank, keep the top 5. Note `04`.

**Acceptance:** eval numbers recorded; added latency measured.

### 10 — Answer evals

**Status:** Not started

**Build:** faithfulness (claims split, each checked against the chunk it cites
by a judge LLM) and answer relevance. Note `07`.

**Acceptance:** faithfulness and relevance scores recorded over the golden set.

### 11 — Mem0 memory

**Status:** Not started

**Build:** Mem0 (open-source library, stored in the same Postgres) so the app
remembers each user's facts across sessions, such as preferred roles or
locations. Note `08`.

**Acceptance:** a fact stated in one session changes an answer in a later one.

### 12 — Deploy and README

**Status:** Not started

**Build:** pgvector, ingestion, and the Q&A surface live on Render and Vercel;
the README carries the eval table (baseline and after each improvement).

**Acceptance:** the public app answers document questions with citations; the
README shows the numbers.

## Guardrails

- Extend this product; do not create a disconnected demo.
- Measure before improving: no retrieval change is kept without eval numbers.
- Filter by user on every retrieval query, from part 4 onward.
- A part is complete only after its acceptance check passes.
