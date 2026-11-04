from collections.abc import Sequence
from math import fsum, hypot, isfinite
from collections.abc import Callable
from uuid import UUID

from pydantic import BaseModel, Field

from musecapsule.knowledge import ReferenceChunk


def cosine_similarity(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    """Compare two finite, nonzero vectors of equal dimensions.

    Return a cosine score between -1 and 1.

    Raises:
        ValueError: If vectors are empty, have different dimensions,
            contain nonfinite values, or have invalid norms.
    """
    if not left or len(left) != len(right):
        raise ValueError("Vectors must have equal nonzero dimensions.")

    if any(not isfinite(value) for value in left):
        raise ValueError("Vectors must contain only finite values.")

    if any(not isfinite(value) for value in right):
        raise ValueError("Vectors must contain only finite values.")

    left_norm = hypot(*left)
    right_norm = hypot(*right)

    if (
        left_norm == 0
        or right_norm == 0
        or not isfinite(left_norm)
        or not isfinite(right_norm)
    ):
        raise ValueError("Vector norms must be finite and positive.")

    score = fsum(
        (a / left_norm) * (b / right_norm)
        for a, b in zip(left, right, strict=True)
    )

    # Floating-point rounding can slightly exceed the mathematical bounds.
    return max(-1.0, min(1.0, score))

class SemanticMatch(BaseModel):
    """An original source fragment with its cosine similarity score."""

    chunk: ReferenceChunk
    score: float = Field(ge=-1, le=1)


def retrieve_semantic_chunks(
    query: str,
    chunks: list[ReferenceChunk],
    *,
    session_id: UUID,
    embed: Callable[[list[str]], list[list[float]]],
    limit: int = 3,
    min_score: float = -1.0,
) -> list[SemanticMatch]:
    """Rank session-scoped fragments by embedding similarity.

    Preserve input order for equal scores. Embed only the current session's
    fragments and return up to limit results.

    Raises:
        ValueError: If the query, limit, or vectors are invalid.
        RuntimeError: If the embedding batch has an unexpected size.
    """
    if not query.strip():
        raise ValueError("Retrieval query must not be blank.")

    if limit <= 0:
        raise ValueError("Retrieval limit must be positive.")

    if not isfinite(min_score) or not -1.0 <= min_score <= 1.0:
        raise ValueError("Minimum score must be finite and between -1 and 1.")

    candidates = [
        chunk for chunk in chunks
        if chunk.session_id == session_id
    ]

    if not candidates:
        return []

    vectors = embed([query, *[chunk.text for chunk in candidates]])

    if len(vectors) != len(candidates) + 1:
        raise RuntimeError("Embedding count does not match retrieval inputs.")

    query_vector = vectors[0]

    results = [
        SemanticMatch(
            chunk=chunk,
            score=cosine_similarity(query_vector, vector),
        )
        for chunk, vector in zip(
            candidates,
            vectors[1:],
            strict=True,
        )
    ]

    results = [
        result for result in results
        if result.score >= min_score
    ]

    results.sort(key=lambda result: result.score, reverse=True)

    return results[:limit]
