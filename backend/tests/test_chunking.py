"""Chunking: every chunk fits the token limit, and cuts fall at natural boundaries.

No database: chunking is a pure function, so these tests only need text.
"""

import tiktoken

from app.chunking import CHUNK_TOKENS, split_text
from seed_data import JOBS

enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


# The seeded job descriptions joined into one long, realistic document: about
# 700 tokens of real paragraphs, so it has to be cut more than once.
LONG_TEXT = "\n\n".join(job["description"] for job in JOBS)


def test_a_short_text_is_one_chunk() -> None:
    assert split_text("First paragraph.\n\nSecond paragraph.") == [
        "First paragraph.\n\nSecond paragraph."
    ]


def test_an_empty_text_has_no_chunks() -> None:
    assert split_text("") == []


def test_a_long_text_is_cut_into_chunks_within_the_limit() -> None:
    chunks = split_text(LONG_TEXT)

    assert len(chunks) > 1
    assert all(0 < count_tokens(chunk) <= CHUNK_TOKENS for chunk in chunks)


def test_cuts_fall_between_paragraphs_when_they_can() -> None:
    """Each paragraph here fits in a chunk, so no paragraph should be cut."""
    paragraphs = [job["description"].split("\n\n")[0] for job in JOBS]
    text = "\n\n".join(paragraphs * 3)

    for chunk in split_text(text):
        for piece in chunk.split("\n\n"):
            assert piece in paragraphs


def test_neighbouring_chunks_overlap() -> None:
    """The end of one chunk is repeated at the start of the next, so a
    sentence on the boundary appears whole in at least one of them."""
    sentences = " ".join(f"Sentence number {n} is here." for n in range(200))
    chunks = split_text(sentences)

    assert len(chunks) > 1
    for first, second in zip(chunks, chunks[1:]):
        last_words = first.split()[-3:]
        assert " ".join(last_words) in second


def test_a_word_longer_than_the_limit_is_still_cut() -> None:
    """A long URL has no spaces; the "" separator is what lets it be cut."""
    chunks = split_text("https://example.com/" + "a" * 5000)

    assert all(count_tokens(chunk) <= CHUNK_TOKENS for chunk in chunks)
