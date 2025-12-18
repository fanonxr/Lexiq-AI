"""Text chunking service for RAG ingestion."""

import re
from typing import Any, Dict, List, Optional

import tiktoken

from document_ingestion.config import get_settings
from document_ingestion.models.chunk import TextChunk
from document_ingestion.utils.errors import ChunkingError
from document_ingestion.utils.logging import get_logger

logger = get_logger("chunking_service")
settings = get_settings()


class ChunkingService:
    """
    Service for chunking text into token-sized segments with overlap.

    Supported methods:
    - sentence: sentence-aware packing into token-sized chunks
    - paragraph: paragraph-aware packing into token-sized chunks
    - fixed: raw token slicing (fastest, least structure-aware)
    """

    def __init__(self, encoding_name: str = "cl100k_base"):
        """
        Initialize the chunking service.

        Args:
            encoding_name: tiktoken encoding name to use for token counting/slicing
        """
        self._encoding = tiktoken.get_encoding(encoding_name)

    async def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        overlap: Optional[int] = None,
        method: Optional[str] = None,
        base_metadata: Optional[Dict[str, Any]] = None,
        chunk_id_prefix: Optional[str] = None,
    ) -> List[TextChunk]:
        """
        Chunk text according to the configured method.

        Args:
            text: Input text to chunk
            chunk_size: Maximum tokens per chunk (defaults to settings.chunking.chunk_size)
            overlap: Overlap between chunks in tokens (defaults to settings.chunking.chunk_overlap)
            method: Chunking method (defaults to settings.chunking.chunking_method)
            base_metadata: Metadata to attach to each chunk
            chunk_id_prefix: Optional prefix for chunk IDs (e.g., file_id)

        Returns:
            List of TextChunk instances

        Raises:
            ChunkingError: If chunking fails or input is invalid
        """
        if text is None:
            raise ChunkingError("Text is None")

        normalized = text.strip()
        if not normalized:
            raise ChunkingError("Text is empty")

        chunk_size = chunk_size or settings.chunking.chunk_size
        overlap = overlap if overlap is not None else settings.chunking.chunk_overlap
        method = (method or settings.chunking.chunking_method).lower()

        if chunk_size <= 0:
            raise ChunkingError("chunk_size must be > 0", details={"chunk_size": chunk_size})
        if overlap < 0:
            raise ChunkingError("overlap must be >= 0", details={"overlap": overlap})
        if overlap >= chunk_size:
            # avoid infinite loops / degenerate configuration
            raise ChunkingError(
                "overlap must be less than chunk_size",
                details={"overlap": overlap, "chunk_size": chunk_size},
            )

        base_metadata = base_metadata or {}
        base_metadata = {**base_metadata, "chunking_method": method}

        logger.info(
            "Chunking text",
            extra={"method": method, "chunk_size": chunk_size, "overlap": overlap},
        )

        if method == "fixed":
            return self._chunk_fixed(normalized, chunk_size, overlap, base_metadata, chunk_id_prefix)
        if method == "paragraph":
            segments = self._split_paragraphs(normalized)
            return self._pack_segments(segments, chunk_size, overlap, base_metadata, chunk_id_prefix)
        if method == "sentence":
            segments = self._split_sentences(normalized)
            return self._pack_segments(segments, chunk_size, overlap, base_metadata, chunk_id_prefix)

        raise ChunkingError(
            "Unsupported chunking method",
            details={"method": method, "valid": ["sentence", "paragraph", "fixed"]},
        )

    def _tokenize(self, text: str) -> List[int]:
        return self._encoding.encode(text)

    def _detokenize(self, tokens: List[int]) -> str:
        return self._encoding.decode(tokens)

    def _count_tokens(self, text: str) -> int:
        return len(self._tokenize(text))

    def _split_paragraphs(self, text: str) -> List[str]:
        # split on one or more blank lines
        parts = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
        return parts if parts else [text]

    def _split_sentences(self, text: str) -> List[str]:
        # naive sentence boundary split; keeps punctuation at end of each sentence
        # fall back to whole text if splitting yields nothing meaningful
        candidates = re.split(r"(?<=[.!?])\s+", text)
        parts = [c.strip() for c in candidates if c and c.strip()]
        return parts if parts else [text]

    def _chunk_fixed(
        self,
        text: str,
        chunk_size: int,
        overlap: int,
        base_metadata: Dict[str, Any],
        chunk_id_prefix: Optional[str],
    ) -> List[TextChunk]:
        tokens = self._tokenize(text)
        if not tokens:
            raise ChunkingError("Text tokenized to empty")

        step = chunk_size - overlap
        chunks: List[TextChunk] = []
        idx = 0
        start = 0
        while start < len(tokens):
            slice_tokens = tokens[start : start + chunk_size]
            chunk_text = self._detokenize(slice_tokens).strip()
            if chunk_text:
                chunk_id = f"{chunk_id_prefix}:{idx}" if chunk_id_prefix else None
                chunks.append(
                    TextChunk(
                        chunk_index=idx,
                        chunk_id=chunk_id,
                        text=chunk_text,
                        token_count=len(slice_tokens),
                        metadata={**base_metadata},
                    )
                )
                idx += 1
            start += step

        return chunks

    def _pack_segments(
        self,
        segments: List[str],
        chunk_size: int,
        overlap: int,
        base_metadata: Dict[str, Any],
        chunk_id_prefix: Optional[str],
    ) -> List[TextChunk]:
        # Precompute segment token counts for overlap selection / packing heuristics
        segs: List[str] = [s for s in (seg.strip() for seg in segments) if s]
        if not segs:
            raise ChunkingError("No segments to chunk")

        seg_token_lens: List[int] = [self._count_tokens(s) for s in segs]

        chunks: List[TextChunk] = []
        current: List[str] = []
        current_lens: List[int] = []
        current_tokens_approx = 0
        chunk_index = 0

        def finalize_chunk(parts: List[str]) -> Optional[TextChunk]:
            nonlocal chunk_index
            if not parts:
                return None
            chunk_text = "\n\n".join(parts).strip()
            if not chunk_text:
                return None
            token_count = self._count_tokens(chunk_text)
            if token_count == 0:
                return None
            if token_count > chunk_size:
                # trim from the front until it fits (should be rare with our packing)
                trimmed = parts[:]
                while len(trimmed) > 1 and self._count_tokens("\n\n".join(trimmed)) > chunk_size:
                    trimmed.pop(0)
                chunk_text = "\n\n".join(trimmed).strip()
                token_count = self._count_tokens(chunk_text)
            chunk_id = f"{chunk_id_prefix}:{chunk_index}" if chunk_id_prefix else None
            tc = TextChunk(
                chunk_index=chunk_index,
                chunk_id=chunk_id,
                text=chunk_text,
                token_count=token_count,
                metadata={**base_metadata},
            )
            chunk_index += 1
            return tc

        i = 0
        while i < len(segs):
            seg = segs[i]
            seg_len = seg_token_lens[i]

            # Handle single huge segment by token-splitting it
            if seg_len > chunk_size:
                # flush current chunk first
                finalized = finalize_chunk(current)
                if finalized:
                    chunks.append(finalized)
                current, current_lens, current_tokens_approx = [], [], 0

                # split this segment via fixed token slicing
                subchunks = self._chunk_fixed(
                    seg,
                    chunk_size=chunk_size,
                    overlap=overlap,
                    base_metadata=base_metadata,
                    chunk_id_prefix=chunk_id_prefix,
                )
                # re-index subchunks to maintain monotonic chunk_index in this doc
                for sc in subchunks:
                    sc.chunk_index = chunk_index
                    sc.chunk_id = f"{chunk_id_prefix}:{chunk_index}" if chunk_id_prefix else None
                    chunk_index += 1
                    chunks.append(sc)
                i += 1
                continue

            if not current:
                current = [seg]
                current_lens = [seg_len]
                current_tokens_approx = seg_len
                i += 1
                continue

            if current_tokens_approx + seg_len <= chunk_size:
                current.append(seg)
                current_lens.append(seg_len)
                current_tokens_approx += seg_len
                i += 1
                continue

            # finalize current chunk
            finalized = finalize_chunk(current)
            if finalized:
                chunks.append(finalized)

            # build overlap window from the end of current
            overlap_parts: List[str] = []
            overlap_lens: List[int] = []
            overlap_tokens = 0
            # Start from the end and collect until we hit overlap, but ensure space for next seg
            budget = max(0, chunk_size - seg_len)
            for part, part_len in zip(reversed(current), reversed(current_lens)):
                if overlap_tokens + part_len > overlap:
                    break
                if overlap_tokens + part_len > budget:
                    break
                overlap_parts.append(part)
                overlap_lens.append(part_len)
                overlap_tokens += part_len
            overlap_parts.reverse()
            overlap_lens.reverse()

            current = overlap_parts + [seg]
            current_lens = overlap_lens + [seg_len]
            current_tokens_approx = overlap_tokens + seg_len
            i += 1

        # finalize trailing chunk
        finalized = finalize_chunk(current)
        if finalized:
            chunks.append(finalized)

        # Enforce final size guarantees (defensive)
        for c in chunks:
            if c.token_count > chunk_size:
                raise ChunkingError(
                    "Chunk exceeds chunk_size after packing",
                    details={"chunk_index": c.chunk_index, "token_count": c.token_count, "chunk_size": chunk_size},
                )

        return chunks


