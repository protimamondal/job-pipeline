"""Cut every document into chunks, embed them with OpenAI, and save them.

Like build_documents.py, this deletes all chunks and writes them again, so it
can be run at any time. Run build_documents.py first, then, from `backend/`:

    uv run python -m app.embed_chunks
"""

import asyncio

from openai import AsyncOpenAI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chunking import split_text
from app.db import SessionLocal, engine
from app.db_models import Chunk, Document
from app.settings import get_settings

EMBEDDING_MODEL = "text-embedding-3-small"
BATCH_SIZE = 100


async def embed(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Return one embedding (1536 numbers) per text, in the same order."""
    response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


async def embed_documents(session: AsyncSession, client: AsyncOpenAI) -> int:
    """Replace every chunk. Returns how many chunks were saved."""
    documents = (await session.scalars(select(Document).order_by(Document.id))).all()

    chunks: list[Chunk] = []
    for doc in documents:
        for index, text in enumerate(split_text(doc.content)):
            chunks.append(
                Chunk(
                    document_id=doc.id,
                    user_id=doc.user_id,
                    job_id=doc.job_id,
                    doc_type=doc.doc_type,
                    chunk_index=index,
                    content=f"{doc.title}\n\n{text}",
                )
            )

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start : start + BATCH_SIZE]
        vectors = await embed(client, [chunk.content for chunk in batch])
        for chunk, vector in zip(batch, vectors):
            chunk.embedding = vector

    # Only now, with every embedding safely back: a failed OpenAI call above
    # leaves the old chunks in place.
    await session.execute(delete(Chunk))
    session.add_all(chunks)
    await session.commit()
    return len(chunks)


async def main() -> None:
    client = AsyncOpenAI(api_key=get_settings().openai_api_key)
    async with SessionLocal() as session:
        count = await embed_documents(session, client)
    await engine.dispose()
    print(f"Chunks saved: {count}")


if __name__ == "__main__":
    asyncio.run(main())
