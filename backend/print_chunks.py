"""Print how the documents are chunked, to check the cuts by eye before
paying to embed them."""

import asyncio

import tiktoken
from sqlalchemy import select

from app.chunking import split_text
from app.db import SessionLocal, engine
from app.db_models import Document

enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


async def main() -> None:
    async with SessionLocal() as session:
        documents = (
            await session.scalars(select(Document).order_by(Document.id))
        ).all()
    await engine.dispose()

    # Summary: every document, how many chunks, and the biggest chunk.
    total = 0
    for doc in documents:
        chunks = split_text(doc.content)
        total += len(chunks)
        biggest = max(count_tokens(chunk) for chunk in chunks)
        print(
            f"{doc.id:4} {doc.doc_type:17} {len(chunks):2} chunks, "
            f"biggest {biggest} tokens  {doc.title[:50]}"
        )
    print(f"\n{len(documents)} documents -> {total} chunks\n")

    # Full text: the first job, resume and note, chunk by chunk.
    for doc_type in ["job", "resume", "application_note"]:
        doc = next((d for d in documents if d.doc_type == doc_type), None)
        if doc is None:
            continue
        print(f"===== {doc.doc_type}: {doc.title} =====")
        for number, chunk in enumerate(split_text(doc.content), start=1):
            print(f"--- chunk {number} ({count_tokens(chunk)} tokens) ---")
            print(chunk)
        print()


if __name__ == "__main__":
    asyncio.run(main())
