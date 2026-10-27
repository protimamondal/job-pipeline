"""Import about 100 real jobs from Arbeitnow, the corpus for Phase 4 RAG.

Seven seeded jobs are too few for retrieval to be tested: every search finds
nearly everything. This adds real job descriptions from the same free API the
MCP server searches.

Only English jobs are kept. Arbeitnow is a German board and about half its
listings are in German; the questions and evals here are in English, and the
chunks have to be readable by eye. Descriptions arrive as HTML, sometimes
escaped (`&lt;p&gt;`), and are stored as plain text so tags never reach the
chunks or the embeddings. Block ends become line breaks, because headings and
list items help chunking later.

Like `seed_if_empty.py`, this deletes nothing, and a second run adds nothing:
the 100 is a total, not a per-run count. Imported jobs are the ones with a
URL (the seeded samples have none). A job is skipped when its URL, or its
company and title, are already in the table: the API lists some jobs twice
under different URLs, and two copies of one job would give two "correct"
chunks for one question in the retrieval evals.
"""

import asyncio
import html
import re

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, engine
from app.db_models import Job

ARBEITNOW_URL = "https://www.arbeitnow.com/api/job-board-api"
TARGET = 100

# Every description ends with a link-back line. It says nothing about the job
# and would match the same searches in every chunk it lands in.
FOOTER = re.compile(r"\s*Find (more English Speaking )?Jobs in [\w ]+ on Arbeitnow\s*$")


def html_to_text(raw: str) -> str:
    """Turn an HTML description into plain text, one block per line."""
    # Unescape first: some descriptions carry their tags as `&lt;p&gt;`.
    text = html.unescape(raw)
    text = re.sub(r"</(p|li|h\d|div)>|<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = FOOTER.sub("", text)
    text = "\n".join(line.strip() for line in text.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def is_english(text: str) -> bool:
    """A rough check, good enough to drop German listings."""
    padded = f" {text.lower()} "
    return " the " in padded and " and " in padded


def _key(company: str, title: str) -> tuple[str, str]:
    return company.strip().lower(), title.strip().lower()


def select_jobs(
    raw_jobs: list[dict],
    existing_urls: set[str],
    existing_keys: set[tuple[str, str]],
    limit: int,
) -> list[Job]:
    """Pick up to `limit` new English jobs from the API response."""
    selected: list[Job] = []
    for raw in raw_jobs:
        if len(selected) >= limit:
            break
        key = _key(raw["company_name"], raw["title"])
        if raw["url"] in existing_urls or key in existing_keys:
            continue
        description = html_to_text(raw["description"])
        if not is_english(description):
            continue
        selected.append(
            Job(
                company=raw["company_name"],
                title=raw["title"],
                location=raw["location"],
                salary_usd=None,
                url=raw["url"],
                description=description,
            )
        )
        existing_urls.add(raw["url"])
        existing_keys.add(key)
    return selected


async def fetch_jobs() -> list[dict]:
    """The first page of the API: about 300 of the newest listings."""
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(ARBEITNOW_URL)
        response.raise_for_status()
        return response.json()["data"]


async def import_jobs(session: AsyncSession, raw_jobs: list[dict]) -> int:
    """Top the imported jobs up to TARGET. Returns the number inserted."""
    rows = (await session.execute(select(Job.url, Job.company, Job.title))).all()
    existing_urls = {row.url for row in rows if row.url}
    existing_keys = {_key(row.company, row.title) for row in rows}
    missing = TARGET - len(existing_urls)
    if missing <= 0:
        return 0

    jobs = select_jobs(raw_jobs, existing_urls, existing_keys, missing)
    session.add_all(jobs)
    await session.commit()
    return len(jobs)


async def main() -> None:
    raw_jobs = await fetch_jobs()
    async with SessionLocal() as session:
        inserted = await import_jobs(session, raw_jobs)
    await engine.dispose()
    print(f"Fetched {len(raw_jobs)} jobs, inserted {inserted}.")


if __name__ == "__main__":
    asyncio.run(main())
