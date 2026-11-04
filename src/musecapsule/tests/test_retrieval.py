from uuid import uuid4

import pytest

from musecapsule.knowledge import ReferenceDocument, chunk_document
from musecapsule.retrieval import (
    EmbeddedChunk,
    cosine_similarity,
    index_chunks,
    retrieve_semantic_chunks,
    search_index,
)


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [
        ([1.0, 0.0], [5.0, 0.0], 1.0),
        ([1.0, 0.0], [0.0, 1.0], 0.0),
        ([1.0, 0.0], [-1.0, 0.0], -1.0),
        ([1.0, 0.0], [1.0, 1.0], 2**-0.5),
    ],
)
def test_cosine_similarity_compares_vector_directions(left, right, expected):
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

    assert received == [
        [
            "Repeat an unsuccessful call.",
            storage.text,
            reliability.text,
        ]
    ]
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
def test_semantic_retrieval_applies_score_threshold(min_score, expected_count):
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


def test_index_chunks_embeds_only_session_sources_in_one_batch():
    session_id = uuid4()
    documents = [
        ReferenceDocument(
            session_id=session_id,
            title="Reliability",
            text="Use bounded retries.",
        ),
        ReferenceDocument(
            session_id=session_id,
            title="Storage",
            text="Save session snapshots.",
        ),
        ReferenceDocument(
            session_id=uuid4(),
            title="Another session",
            text="Unrelated private content.",
        ),
    ]
    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    before = [chunk.model_dump() for chunk in chunks]
    calls = []

    def embed(texts):
        calls.append(list(texts))
        return [[1.0, 0.0], [0.0, 1.0]]

    indexed = index_chunks(
        chunks,
        session_id=session_id,
        model_name="test-model",
        embed=embed,
    )

    assert calls == [[documents[0].text, documents[1].text]]
    assert [item.chunk.id for item in indexed] == [
        chunks[0].id,
        chunks[1].id,
    ]
    assert [item.vector for item in indexed] == [
        [1.0, 0.0],
        [0.0, 1.0],
    ]
    assert all(item.model_name == "test-model" for item in indexed)
    assert [chunk.model_dump() for chunk in chunks] == before


@pytest.mark.parametrize(
    "vectors",
    [
        [],
        [[]],
        [[0.0, 0.0]],
        [[float("nan"), 1.0]],
    ],
)
def test_index_chunks_rejects_invalid_vectors(vectors):
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability",
        text="Use bounded retries.",
    )

    with pytest.raises(RuntimeError):
        index_chunks(
            chunk_document(document),
            session_id=document.session_id,
            model_name="test-model",
            embed=lambda texts: vectors,
        )


def test_index_chunks_skips_embedding_without_candidates():
    def unexpected_embedding(texts):
        pytest.fail("Embedding must not run without candidate chunks.")

    assert (
        index_chunks(
            [],
            session_id=uuid4(),
            model_name="test-model",
            embed=unexpected_embedding,
        )
        == []
    )


def test_search_index_embeds_only_queries_and_preserves_sources():
    session_id = uuid4()
    documents = [
        ReferenceDocument(
            session_id=session_id,
            title="Storage",
            text="SQLite stores snapshots.",
        ),
        ReferenceDocument(
            session_id=session_id,
            title="Reliability",
            text="Use bounded retries.",
        ),
        ReferenceDocument(
            session_id=uuid4(),
            title="Another session",
            text="Private content.",
        ),
    ]

    indexed = [
        EmbeddedChunk(
            chunk=chunk_document(document)[0],
            model_name=model_name,
            vector=vector,
        )
        for document, model_name, vector in [
            (documents[0], "test-model", [0.0, 1.0]),
            (documents[1], "test-model", [1.0, 0.0]),
            (documents[2], "another-model", [1.0, 0.0]),
        ]
    ]
    before = [item.model_dump() for item in indexed]
    calls = []

    def embed(texts):
        calls.append(list(texts))
        return [[1.0, 0.0]]

    for query in ["Repeat a failed call.", "Try the request again."]:
        results = search_index(
            query,
            indexed,
            session_id=session_id,
            model_name="test-model",
            embed=embed,
            limit=1,
            min_score=0.30,
        )

        assert len(results) == 1
        assert results[0].chunk.document_id == documents[1].id
        assert results[0].score == pytest.approx(1.0)

    assert calls == [
        ["Repeat a failed call."],
        ["Try the request again."],
    ]
    assert [item.model_dump() for item in indexed] == before


def test_search_index_rejects_model_mismatch_before_embedding():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability",
        text="Use bounded retries.",
    )
    indexed = [
        EmbeddedChunk(
            chunk=chunk_document(document)[0],
            model_name="original-model",
            vector=[1.0, 0.0],
        )
    ]

    def unexpected_embedding(texts):
        pytest.fail("Model mismatch must be rejected before embedding.")

    with pytest.raises(ValueError, match="different embedding model"):
        search_index(
            "Retries",
            indexed,
            session_id=document.session_id,
            model_name="different-model",
            embed=unexpected_embedding,
        )
