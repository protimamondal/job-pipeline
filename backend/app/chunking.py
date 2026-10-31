from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_TOKENS = 300
OVERLAP_TOKENS = 50

SEPERATORS = ["\n\n", "\n", ". ", " ", ""]

_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
    encoding_name="cl100k_base",
    chunk_size=CHUNK_TOKENS,
    chunk_overlap=OVERLAP_TOKENS,
    separators=SEPERATORS,
)


def split_text(text: str) -> list[str]:
    """Split text into chunks of at most max_chars, cutting at the largest
    boundary that works."""
    return _splitter.split_text(text)
