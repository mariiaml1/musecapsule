from uuid import uuid4

import pytest

from musecapsule.knowledge import ReferenceDocument, chunk_document
from musecapsule.retrieval import cosine_similarity, retrieve_semantic_chunks


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ([1.0, 0.0], [5.0, 0.0], 1.0),
        ([1.0, 0.0], [0.0, 1.0], 0.0),
        ([1.0, 0.0], [-1.0, 0.0], -1.0),
        ([1.0, 0.0], [1.0, 1.0], 2 ** -0.5),
    ],
)
def test_cosine_similarity_compares_vector_directions(
    left, right, expected
):
    assert cosine_similarity(left, right) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("left", "right"),
    [
        ([], []),
        ([1.0], [1.0, 0.0]),
        ([0.0, 0.0], [1.0, 0.0]),
        ([1.0, 0.0], [0.0, 0.0]),
        ([float("nan")], [1.0]),
        ([1.0], [float("inf")]),
    ],
)
def test_cosine_similarity_rejects_invalid_vectors(left, right):
    with pytest.raises(ValueError):
        cosine_similarity(left, right)

def test_semantic_retrieval_ranks_sources_and_excludes_other_sessions():
    session_id = uuid4()

    storage = ReferenceDocument(
        session_id=session_id,
        title="Storage",
        text="SQLite stores snapshots.",
    )
    reliability = ReferenceDocument(
        session_id=session_id,
        title="Reliability",
        text="Use bounded retries.",
    )
    foreign = ReferenceDocument(
        session_id=uuid4(),
        title="Another session",
        text="Private reference content.",
    )

    chunks = [
        chunk
        for document in [storage, reliability, foreign]
        for chunk in chunk_document(document)
    ]
    before = [chunk.model_dump() for chunk in chunks]
    received = []

    def embed(texts):
        received.append(texts)
        # Query, storage, reliability.
        return [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]

    results = retrieve_semantic_chunks(
        "Repeat an unsuccessful call.",
        chunks,
        session_id=session_id,
        embed=embed,
        limit=1,
    )

    assert received == [[
        "Repeat an unsuccessful call.",
        storage.text,
        reliability.text,
    ]]
    assert len(results) == 1
    assert results[0].chunk.document_id == reliability.id
    assert results[0].score == pytest.approx(1.0)
    assert [chunk.model_dump() for chunk in chunks] == before


def test_semantic_retrieval_skips_embedding_without_candidates():
    def unexpected_embedding(texts):
        pytest.fail("Embedding must not run without candidate chunks.")

    results = retrieve_semantic_chunks(
        "Retries",
        [],
        session_id=uuid4(),
        embed=unexpected_embedding,
    )

    assert results == []

@pytest.mark.parametrize(
    ("min_score", "expected_count"),
    [
        (0.0, 1),
        (0.6, 1),
        (0.7, 0),
    ],
)
def test_semantic_retrieval_applies_score_threshold(
    min_score, expected_count
):
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability",
        text="Use bounded retries.",
    )
    chunks = chunk_document(document)

    def embed(texts):
        # Cosine similarity is 0.6.
        return [[1.0, 0.0], [0.6, 0.8]]

    results = retrieve_semantic_chunks(
        "Repeat an unsuccessful call.",
        chunks,
        session_id=document.session_id,
        embed=embed,
        min_score=min_score,
    )

    assert len(results) == expected_count

    if results:
        assert results[0].chunk.id == chunks[0].id
        assert results[0].score == pytest.approx(0.6)


@pytest.mark.parametrize(
    "min_score",
    [-1.1, 1.1, float("nan"), float("inf")],
)
def test_semantic_retrieval_rejects_invalid_threshold(min_score):
    def unexpected_embedding(texts):
        pytest.fail("Invalid settings must be rejected before embedding.")

    with pytest.raises(ValueError, match="Minimum score"):
        retrieve_semantic_chunks(
            "Retries",
            [],
            session_id=uuid4(),
            embed=unexpected_embedding,
            min_score=min_score,
        )
