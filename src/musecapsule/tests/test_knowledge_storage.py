from uuid import uuid4

import pytest

from musecapsule.knowledge import ReferenceDocument, chunk_document
from musecapsule.knowledge_storage import KnowledgeStore
from musecapsule.retrieval import index_chunks, search_index


def test_knowledge_store_restores_document_after_reopening(tmp_path):
    database_path = tmp_path / "knowledge.db"
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability notes",
        text="  Use bounded retries.\n\n",
    )

    KnowledgeStore(database_path).save_document(document)

    restored = KnowledgeStore(database_path).load_document(
        document.id,
        session_id=document.session_id,
    )

    assert restored == document
    assert restored.text == document.text


def test_knowledge_store_excludes_other_sessions(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Private reference",
        text="Session-specific content.",
    )
    store.save_document(document)

    assert store.load_document(
        document.id,
        session_id=uuid4(),
    ) is None


def test_knowledge_store_rejects_overwrite_and_preserves_source(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability notes",
        text="Use bounded retries.",
    )
    store.save_document(document)

    replacement = document.model_copy(
        update={"text": "Replacement content."},
    )

    with pytest.raises(ValueError, match="already exists"):
        store.save_document(replacement)

    assert store.load_document(
        document.id,
        session_id=document.session_id,
    ) == document


@pytest.fixture
def reference_index(tmp_path):
    database_path = tmp_path / "knowledge.db"
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
    ]
    store = KnowledgeStore(database_path)

    for document in documents:
        store.save_document(document)

    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(document)
    ]
    indexed = index_chunks(
        chunks,
        session_id=session_id,
        model_name="test-model",
        embed=lambda texts: [[1.0, 0.0], [0.0, 1.0]],
    )

    return database_path, session_id, indexed


def test_knowledge_store_restores_index_after_reopening(reference_index):
    database_path, session_id, indexed = reference_index

    KnowledgeStore(database_path).save_index(
        indexed,
        session_id=session_id,
        model_name="test-model",
    )

    restored = KnowledgeStore(database_path).load_index(
        session_id=session_id,
        model_name="test-model",
    )

    assert restored == indexed


def test_knowledge_store_rolls_back_invalid_index_batch(reference_index):
    database_path, session_id, indexed = reference_index
    store = KnowledgeStore(database_path)

    invalid_chunk = indexed[1].chunk.model_copy(
        update={"text": indexed[1].chunk.text.upper()},
    )
    invalid_item = indexed[1].model_copy(
        update={"chunk": invalid_chunk},
    )

    with pytest.raises(ValueError, match="does not match its source"):
        store.save_index(
            [indexed[0], invalid_item],
            session_id=session_id,
            model_name="test-model",
        )

    assert store.load_index(
        session_id=session_id,
        model_name="test-model",
    ) == []


def test_knowledge_store_scopes_index_by_session_and_model(reference_index):
    database_path, session_id, indexed = reference_index
    store = KnowledgeStore(database_path)
    store.save_index(
        indexed,
        session_id=session_id,
        model_name="test-model",
    )

    assert store.load_index(
        session_id=uuid4(),
        model_name="test-model",
    ) == []

    assert store.load_index(
        session_id=session_id,
        model_name="another-model",
    ) == []


def test_restored_index_search_embeds_only_query(reference_index):
    database_path, session_id, indexed = reference_index

    KnowledgeStore(database_path).save_index(
        indexed,
        session_id=session_id,
        model_name="test-model",
    )

    # Reopen storage to simulate a new application instance.
    reopened = KnowledgeStore(database_path)
    restored = reopened.load_index(
        session_id=session_id,
        model_name="test-model",
    )
    before = [item.model_dump() for item in restored]
    calls = []

    def embed_query(texts):
        calls.append(list(texts))
        return [[1.0, 0.0]]

    results = search_index(
        "Repeat an unsuccessful call.",
        restored,
        session_id=session_id,
        model_name="test-model",
        embed=embed_query,
        limit=1,
        min_score=0.30,
    )

    assert calls == [["Repeat an unsuccessful call."]]
    assert len(results) == 1
    assert results[0].score == pytest.approx(1.0)

    source = results[0].chunk
    assert source.id == indexed[0].chunk.id
    assert source.document_id == indexed[0].chunk.document_id

    document = reopened.load_document(
        source.document_id,
        session_id=session_id,
    )
    assert document is not None
    assert source.text == document.text[source.start:source.end]

    assert [item.model_dump() for item in restored] == before
    assert reopened.load_index(
        session_id=session_id,
        model_name="test-model",
    ) == restored


@pytest.fixture
def document_package():
    document = ReferenceDocument(
        session_id=uuid4(),
        title="Reliability",
        text="Use bounded retries.",
    )
    indexed = index_chunks(
        chunk_document(document),
        session_id=document.session_id,
        model_name="test-model",
        embed=lambda texts: [[1.0, 0.0]],
    )
    return document, indexed


def test_save_document_with_index_persists_both(tmp_path, document_package):
    document, indexed = document_package
    database_path = tmp_path / "knowledge.db"

    KnowledgeStore(database_path).save_document_with_index(
        document,
        indexed,
        model_name="test-model",
    )

    reopened = KnowledgeStore(database_path)

    assert reopened.load_document(
        document.id,
        session_id=document.session_id,
    ) == document

    assert reopened.load_index(
        session_id=document.session_id,
        model_name="test-model",
    ) == indexed


def test_save_document_with_index_rolls_back_document(
    tmp_path, document_package
):
    document, indexed = document_package
    store = KnowledgeStore(tmp_path / "knowledge.db")

    invalid_chunk = indexed[0].chunk.model_copy(
        update={"text": indexed[0].chunk.text.upper()},
    )
    invalid_item = indexed[0].model_copy(
        update={"chunk": invalid_chunk},
    )

    with pytest.raises(ValueError, match="does not match its source"):
        store.save_document_with_index(
            document,
            [invalid_item],
            model_name="test-model",
        )

    assert store.load_document(
        document.id,
        session_id=document.session_id,
    ) is None

    assert store.load_index(
        session_id=document.session_id,
        model_name="test-model",
    ) == []

    # A valid retry can use the same IDs after the rollback.
    store.save_document_with_index(
        document,
        indexed,
        model_name="test-model",
    )

    assert store.load_document(
        document.id,
        session_id=document.session_id,
    ) == document
