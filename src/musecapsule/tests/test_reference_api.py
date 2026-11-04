from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from musecapsule.api import create_app
from musecapsule.embeddings import EmbeddingInputTooLongError
from musecapsule.knowledge import ReferenceChunk
from musecapsule.knowledge_service import ingest_reference_document
from musecapsule.knowledge_storage import KnowledgeStore
from musecapsule.retrieval import SemanticMatch


def test_reference_api_persists_document_and_index_without_changing_session(
    tmp_path,
):
    database_path = tmp_path / "sessions.db"
    knowledge = KnowledgeStore(database_path)

    def process_reference(session_id, title, text):
        return ingest_reference_document(
            session_id=session_id,
            title=title,
            text=text,
            store=knowledge,
            model_name="test-model",
            embed=lambda texts: [[1.0, 0.0] for _ in texts],
        )

    app = create_app(
        database_path,
        process_reference=process_reference,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={"goal": "Build an AI portfolio project"},
        )
        assert created.status_code == 201
        session = created.json()
        source_text = "  Use bounded retries.\n"

        response = client.post(
            f"/sessions/{session['id']}/references",
            json={
                "title": "Reliability notes",
                "text": source_text,
            },
        )

        assert response.status_code == 201
        document = response.json()
        assert document["session_id"] == session["id"]
        assert document["text"] == source_text

        restored_session = client.get(f"/sessions/{session['id']}")
        assert restored_session.json() == session

    reopened = KnowledgeStore(database_path)
    restored = reopened.load_document(
        UUID(document["id"]),
        session_id=UUID(session["id"]),
    )
    assert restored is not None
    assert restored.text == source_text

    indexed = reopened.load_index(
        session_id=UUID(session["id"]),
        model_name="test-model",
    )
    assert len(indexed) == 1
    assert indexed[0].chunk.document_id == restored.id


def test_reference_api_rejects_missing_session_before_processing(tmp_path):
    handler = Mock()
    app = create_app(
        tmp_path / "sessions.db",
        process_reference=handler,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/sessions/{uuid4()}/references",
            json={"title": "Notes", "text": "Use bounded retries."},
        )

    assert response.status_code == 404
    handler.assert_not_called()


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (EmbeddingInputTooLongError("Private detail"), 422),
        (RuntimeError("Private detail"), 502),
    ],
)
def test_reference_api_sanitizes_processing_errors(
    tmp_path, error, expected_status
):
    handler = Mock(side_effect=error)
    app = create_app(
        tmp_path / "sessions.db",
        process_reference=handler,
    )

    with TestClient(app) as client:
        session = client.post(
            "/sessions",
            json={"goal": "Build an AI portfolio project"},
        ).json()

        response = client.post(
            f"/sessions/{session['id']}/references",
            json={"title": "Notes", "text": "Reference content."},
        )

    assert response.status_code == expected_status
    assert "Private detail" not in response.text
    handler.assert_called_once()


def test_reference_search_returns_sources_without_changing_session(tmp_path):
    handler = Mock()
    app = create_app(
        tmp_path / "sessions.db",
        search_references=handler,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={"goal": "Build an AI portfolio project"},
        )
        assert created.status_code == 201
        session = created.json()
        session_id = UUID(session["id"])

        match = SemanticMatch(
            chunk=ReferenceChunk(
                document_id=uuid4(),
                session_id=session_id,
                start=0,
                end=20,
                text="Use bounded retries.",
            ),
            score=0.8,
        )
        handler.return_value = [match]

        response = client.post(
            f"/sessions/{session_id}/references/search",
            json={
                "query": "Repeat a failed request",
                "limit": 2,
                "min_score": 0.40,
            },
        )

        assert response.status_code == 200
        assert response.json() == [match.model_dump(mode="json")]
        handler.assert_called_once_with(
            session_id,
            "Repeat a failed request",
            2,
            0.40,
        )

        handler.return_value = []

        empty = client.post(
            f"/sessions/{session_id}/references/search",
            json={"query": "Bake bread"},
        )

        assert empty.status_code == 200
        assert empty.json() == []
        assert client.get(f"/sessions/{session_id}").json() == session


def test_reference_search_rejects_missing_session(tmp_path):
    handler = Mock()
    app = create_app(
        tmp_path / "sessions.db",
        search_references=handler,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/sessions/{uuid4()}/references/search",
            json={"query": "Retries"},
        )

    assert response.status_code == 404
    handler.assert_not_called()


@pytest.mark.parametrize(
    "body",
    [
        {"query": " "},
        {"query": "Retries", "limit": 0},
        {"query": "Retries", "min_score": 1.1},
    ],
)
def test_reference_search_rejects_invalid_request(tmp_path, body):
    handler = Mock()
    app = create_app(
        tmp_path / "sessions.db",
        search_references=handler,
    )

    with TestClient(app) as client:
        session = client.post(
            "/sessions",
            json={"goal": "Build an AI portfolio project"},
        ).json()

        response = client.post(
            f"/sessions/{session['id']}/references/search",
            json=body,
        )

    assert response.status_code == 422
    handler.assert_not_called()
