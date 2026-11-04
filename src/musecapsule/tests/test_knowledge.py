from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from musecapsule.knowledge import (
    ReferenceChunk,
    ReferenceDocument,
    chunk_document,
    retrieve_chunks,
    validate_chunk_source,
)


def test_reference_document_preserves_source_and_session():
    session_id = uuid4()
    original_text = "  Retries require explicit limits.\n\n"

    document = ReferenceDocument(
        session_id=session_id,
        title="Reliability notes",
        text=original_text,
    )

    assert isinstance(document.id, UUID)
    assert document.session_id == session_id
    assert document.text == original_text


@pytest.mark.parametrize("field", ["title", "text"])
@pytest.mark.parametrize("blank", ["", " ", "\t\n"])
def test_reference_document_rejects_blank_content(field, blank):
    values = {
        "session_id": uuid4(),
        "title": "Reliability notes",
        "text": "Retries require explicit limits.",
    }
    values[field] = blank

    with pytest.raises(ValidationError):
        ReferenceDocument(**values)


def test_reference_documents_receive_distinct_ids():
    values = {
        "session_id": uuid4(),
        "title": "Reliability notes",
        "text": "Retries require explicit limits.",
    }

    first = ReferenceDocument(**values)
    second = ReferenceDocument(**values)

    assert first.id != second.id


def test_chunk_document_preserves_sources_and_overlap():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Example",
        text="  abcdefghijklmnop  ",
    )
    before = document.model_dump()

    chunks = chunk_document(document, chunk_size=8, overlap=2)

    assert [(chunk.start, chunk.end) for chunk in chunks] == [
        (0, 8),
        (6, 14),
        (12, 20),
    ]
    assert len({chunk.id for chunk in chunks}) == 3

    for chunk in chunks:
        assert chunk.document_id == document.id
        assert chunk.session_id == document.session_id
        assert chunk.text == document.text[chunk.start : chunk.end]

    for previous, current in zip(chunks, chunks[1:]):
        assert previous.text[-2:] == current.text[:2]

    assert document.model_dump() == before


def test_chunk_document_returns_one_chunk_for_short_document():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Short note",
        text="Retries need limits.",
    )

    chunks = chunk_document(document)

    assert len(chunks) == 1
    assert chunks[0].start == 0
    assert chunks[0].end == len(document.text)
    assert chunks[0].text == document.text


@pytest.mark.parametrize(
    ("chunk_size", "overlap"),
    [(0, 0), (-1, 0), (8, -1), (8, 8), (8, 9)],
)
def test_chunk_document_rejects_invalid_settings(chunk_size, overlap):
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Example",
        text="Some reference content.",
    )

    with pytest.raises(ValueError):
        chunk_document(
            document,
            chunk_size=chunk_size,
            overlap=overlap,
        )


def test_retrieve_chunks_ranks_matches_and_preserves_sources():
    session_id = uuid4()
    documents = [
        ReferenceDocument(
            session_id=session_id,
            title="Partial match",
            text="Retries may repeat a request.",
        ),
        ReferenceDocument(
            session_id=session_id,
            title="Full match",
            text="Use bounded retries and explicit timeouts.",
        ),
        ReferenceDocument(
            session_id=session_id,
            title="Unrelated",
            text="SQLite stores session snapshots.",
        ),
    ]
    chunks = [chunk for document in documents for chunk in chunk_document(document)]
    before = [chunk.model_dump() for chunk in chunks]

    results = retrieve_chunks(
        "RETRIES retries timeouts",
        chunks,
        session_id=session_id,
        limit=2,
    )

    assert [result.chunk.document_id for result in results] == [
        documents[1].id,
        documents[0].id,
    ]
    assert [result.score for result in results] == [1.0, 0.5]
    assert results[0].chunk.text == documents[1].text
    assert [chunk.model_dump() for chunk in chunks] == before


def test_retrieve_chunks_excludes_other_sessions():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Another session",
        text="Use retries and timeouts.",
    )

    results = retrieve_chunks(
        "retries timeouts",
        chunk_document(document),
        session_id=uuid4(),
    )

    assert results == []


def test_retrieve_chunks_returns_empty_when_nothing_matches():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Storage",
        text="SQLite stores session snapshots.",
    )

    results = retrieve_chunks(
        "timeouts",
        chunk_document(document),
        session_id=document.session_id,
    )

    assert results == []


@pytest.mark.parametrize(
    ("query", "limit"),
    [("", 3), (" \n", 3), ("retries", 0), ("retries", -1)],
)
def test_retrieve_chunks_rejects_invalid_requests(query, limit):
    with pytest.raises(ValueError):
        retrieve_chunks(
            query,
            [],
            session_id=uuid4(),
            limit=limit,
        )


def test_validate_chunk_source_accepts_exact_source_without_changes():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability",
        text="Use bounded retries.",
    )
    chunk = ReferenceChunk(
        document_id=document.id,
        session_id=document.session_id,
        start=4,
        end=11,
        text="bounded",
    )
    before_document = document.model_dump()
    before_chunk = chunk.model_dump()

    validate_chunk_source(chunk, document)

    assert document.model_dump() == before_document
    assert chunk.model_dump() == before_chunk


@pytest.mark.parametrize(
    ("changes", "expected_error"),
    [
        (
            {"document_id": uuid4()},
            "Chunk references a different document.",
        ),
        (
            {"session_id": uuid4()},
            "Chunk and document belong to different sessions.",
        ),
        (
            {"start": 100, "end": 107},
            "Chunk offsets are outside the document.",
        ),
        (
            {"text": "fiction"},
            "Chunk text does not match its source.",
        ),
    ],
)
def test_validate_chunk_source_rejects_invalid_provenance(changes, expected_error):
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability",
        text="Use bounded retries.",
    )
    chunk = ReferenceChunk(
        document_id=document.id,
        session_id=document.session_id,
        start=4,
        end=11,
        text="bounded",
    )
    invalid = ReferenceChunk.model_validate(
        {
            **chunk.model_dump(),
            **changes,
        }
    )

    with pytest.raises(ValueError) as error:
        validate_chunk_source(invalid, document)

    assert str(error.value) == expected_error
