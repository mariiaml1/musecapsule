from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Self

from pydantic import model_validator
import re


class ReferenceDocument(BaseModel):
    """A reference document scoped to one exploration session.

    Preserve the original text for chunking and source verification.
    Reference content is separate from narrative evidence and user intent.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)

    @field_validator("title", "text")
    @classmethod
    def reject_blank_content(cls, value: str) -> str:
        """Reject blank values without altering source content."""
        if not value.strip():
            raise ValueError("Reference content must not be blank.")
        return value


class ReferenceChunk(BaseModel):
    """An exact document fragment with source character offsets.

    The start offset is inclusive; the end offset is exclusive.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    session_id: UUID
    start: int = Field(ge=0)
    end: int = Field(ge=1)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_offsets(self) -> Self:
        """Require offsets to match the fragment's character length."""
        if self.end <= self.start:
            raise ValueError("Chunk end must be greater than start.")

        if self.end - self.start != len(self.text):
            raise ValueError("Chunk offsets must match text length.")

        return self


def chunk_document(
    document: ReferenceDocument,
    *,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[ReferenceChunk]:
    """Split a document into overlapping character windows.

    Preserve source text and stop when a window reaches the document end.

    Raises:
        ValueError: If chunk size or overlap is invalid.
    """
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Overlap must be nonnegative and smaller than chunk size."
        )

    chunks: list[ReferenceChunk] = []
    start = 0

    while start < len(document.text):
        end = min(start + chunk_size, len(document.text))

        chunks.append(
            ReferenceChunk(
                document_id=document.id,
                session_id=document.session_id,
                start=start,
                end=end,
                text=document.text[start:end],
            )
        )

        if end == len(document.text):
            break

        start = end - overlap

    return chunks

class RetrievedChunk(BaseModel):
    """A source fragment ranked by the retrieval strategy.

    The score is a relevance measure, not a probability of correctness.
    """

    chunk: ReferenceChunk
    score: float = Field(gt=0, le=1)


def retrieve_chunks(
    query: str,
    chunks: list[ReferenceChunk],
    *,
    session_id: UUID,
    limit: int = 3,
) -> list[RetrievedChunk]:
    """Rank session-scoped fragments by unique query-word coverage.

    Ignore fragments without matching words. Preserve input order for ties.
    Return original source fragments without modifying them.

    Raises:
        ValueError: If the query is blank or the limit is not positive.
    """
    if not query.strip():
        raise ValueError("Retrieval query must not be blank.")

    if limit <= 0:
        raise ValueError("Retrieval limit must be positive.")

    def words(text: str) -> set[str]:
        return set(re.findall(r"[^\W_]+", text.casefold()))

    query_words = words(query)

    if not query_words:
        return []

    results: list[RetrievedChunk] = []

    for chunk in chunks:
        if chunk.session_id != session_id:
            continue

        matched_words = query_words & words(chunk.text)

        if not matched_words:
            continue

        results.append(
            RetrievedChunk(
                chunk=chunk,
                score=len(matched_words) / len(query_words),
            )
        )

    results.sort(key=lambda result: result.score, reverse=True)

    return results[:limit]


def validate_chunk_source(
    chunk: ReferenceChunk,
    document: ReferenceDocument,
) -> None:
    """Verify a fragment against its original document.

    Check document identity, session ownership, offsets, and exact text.

    Raises:
        ValueError: If the fragment does not match its declared source.
    """
    if chunk.document_id != document.id:
        raise ValueError("Chunk references a different document.")

    if chunk.session_id != document.session_id:
        raise ValueError("Chunk and document belong to different sessions.")

    if not 0 <= chunk.start < chunk.end <= len(document.text):
        raise ValueError("Chunk offsets are outside the document.")

    if chunk.text != document.text[chunk.start : chunk.end]:
        raise ValueError("Chunk text does not match its source.")
