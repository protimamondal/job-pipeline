# Phase 3 working agreement

This repository is the product implementation workspace. Theory, revision,
planning, and private progress records live in Rahul's `ai-journey` repository.

Before Phase 3 work, read [`PHASE3.md`](PHASE3.md). When the user says
"start sub-phase N" or "implement sub-phase N" in this repository:

1. Open the matching section in `PHASE3.md` and state its goal and acceptance
   check.
2. Give Protima one manageable implementation task at a time, then review or
   debug what she writes.
3. Do not assume Protima has backend fundamentals. Explain whatever she asks
   clearly, including API boundaries, server lifecycle, persistence,
   transactions, authentication, middleware, concurrency, and operational
   concerns. Treat her as a senior engineer who is new to backend work, not as
   a beginner programmer.
4. Explain Python and FastAPI implementation mechanics carefully when they
   first appear, including syntax, idioms, typing/Pydantic, decorators,
   dependency injection, ASGI lifecycle, testing, packaging, and why the code
   is structured that way. These mechanics are also new to Rahul.
5. Do not implement the entire sub-phase silently unless the user explicitly
   asks the agent to write it.
6. Run the relevant tests and acceptance check before marking a sub-phase
   complete.

Protima owns and drives this product. Work directly on `main`; do not create
feature branches or pull requests unless the user explicitly reverses this
rule. Instructions in nested `AGENTS.md` files also apply within their
directories.
