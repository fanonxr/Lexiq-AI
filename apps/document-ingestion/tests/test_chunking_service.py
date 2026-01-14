import pytest

from document_ingestion.services.chunking_service import ChunkingService


@pytest.mark.asyncio
async def test_fixed_chunking_respects_chunk_size():
    svc = ChunkingService()
    text = "hello " * 200
    chunks = await svc.chunk_text(text=text, chunk_size=20, overlap=5, method="fixed")
    assert len(chunks) > 1
    assert all(0 < c.token_count <= 20 for c in chunks)


@pytest.mark.asyncio
async def test_sentence_chunking_produces_multiple_chunks_and_respects_size():
    svc = ChunkingService()
    text = " ".join([f"Sentence {i}." for i in range(100)])
    chunks = await svc.chunk_text(text=text, chunk_size=40, overlap=10, method="sentence")
    assert len(chunks) > 1
    assert all(0 < c.token_count <= 40 for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


@pytest.mark.asyncio
async def test_paragraph_chunking_splits_on_blank_lines():
    svc = ChunkingService()
    text = """Para one has some text.

Para two has some more text.

Para three has even more text."""
    chunks = await svc.chunk_text(text=text, chunk_size=30, overlap=5, method="paragraph")
    assert len(chunks) >= 1
    assert all(0 < c.token_count <= 30 for c in chunks)


