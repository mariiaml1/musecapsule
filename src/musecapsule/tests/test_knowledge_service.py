from unittest.mock import Mock
from uuid import uuid4

import pytest

from musecapsule.knowledge_service import ingest_reference_document
from musecapsule.knowledge_storage import KnowledgeStore


def test_ingestion_embeds_before_saving_and_preserves_source(
    tmp_path, monkeypatch
):
    database_path = tmp_path / "knowledge.db"
    store = KnowledgeStore(database_path)
    session_id = uuid4()
    original_text = "  Use bounded retries.\n"
    operations = []

    original_save = store.save_document_with_index

    def record_save(document, indexed, *, model_name):
        operations.append("save")
        original_save(document, indexed, model_name=model_name)

    monkeypatch.setattr(
        store,
        "save_document_with_index",
        record_save,
    )

    def embed(texts):
        operations.append("embed")
        assert texts == [original_text]
        return [[1.0, 0.0]]

    document = ingest_reference_document(
        session_id=session_id,
        title="Reliability notes",
        text=original_text,
        store=store,
        model_name="test-model",
        embed=embed,
    )

    assert operations == ["embed", "save"]

    reopened = KnowledgeStore(database_path)

    assert reopened.load_document(
        document.id,
        session_id=session_id,
    ) == document

    indexed = reopened.load_index(
        session_id=session_id,
        model_name="test-model",
    )

    assert len(indexed) == 1
    assert indexed[0].chunk.document_id == document.id
    assert indexed[0].chunk.text == original_text
    assert indexed[0].vector == [1.0, 0.0]


def test_ingestion_does_not_save_when_embedding_fails(
    tmp_path, monkeypatch
):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    save = Mock(wraps=store.save_document_with_index)
    monkeypatch.setattr(store, "save_document_with_index", save)

    def failing_embed(texts):
        raise RuntimeError("Embedding failed.")

    with pytest.raises(RuntimeError, match="Embedding failed"):
        ingest_reference_document(
            session_id=uuid4(),
            title="Reliability notes",
            text="Use bounded retries.",
            store=store,
            model_name="test-model",
            embed=failing_embed,
        )

    save.assert_not_called()
