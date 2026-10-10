FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Dependencies first, so a code-only change does not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY seed.py seed_if_empty.py seed_data.py ./
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 10000

# Migrations run here rather than in a Render preDeployCommand, which needs a
# paid instance type. `alembic upgrade head` is a no-op when the database is
# already current, so restarts are safe; with more than one instance this
# would need moving to a pre-deploy step so two containers cannot migrate at
# once.
# seed_if_empty.py inserts the sample jobs only when the table has none, so
# a fresh database does not serve an empty jobs page. It deletes nothing, and
# is a no-op on every boot after the first.
CMD ["sh", "-c", "alembic upgrade head && python seed_if_empty.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
