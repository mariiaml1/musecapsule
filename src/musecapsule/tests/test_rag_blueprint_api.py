import json
import sqlite3
from contextlib import closing
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from musecapsule import server
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)
from musecapsule.state import SessionState
from musecapsule.storage import SessionStore


def make_selected_session() -> SessionState:
    """Create a selected idea with grounded metaphor references."""
    message = Message(role="user", text="A capsule holds a small machine.")
    evidence = EvidenceRef(message_id=message.id, quote="A capsule")
    image = ImageFragment(label="Capsule", evidence=[evidence])
    hypothesis = Hypothesis(
        statement="The capsule could suggest a bounded execution space.",
        image_ids=[image.id],
        evidence=[evidence],
    )
    idea = ProductIdea(
        title="Bounded Agent Runner",
        description="Run an agent with a bounded retry budget.",
        goal_alignment="Demonstrates agent reliability.",
        image_ids=[image.id],
        hypothesis_ids=[hypothesis.id],
    )

    return SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Small MVP"],
        ),
        messages=[message],
        images=[image],
        hypotheses=[hypothesis],
        ideas=[idea],
        selected_idea_id=idea.id,
    )


@pytest.mark.parametrize("streaming", [False, True])
def test_rag_blueprint_api_preserves_citations_and_saves_once(
    tmp_path, monkeypatch, streaming
):
    database_path = tmp_path / "sessions.db"
    session = make_selected_session()
    SessionStore(database_path).save(session)

    monkeypatch.setenv("MUSECAPSULE_DEVKIT_DIR", str(tmp_path))
    monkeypatch.setenv("MUSECAPSULE_DATABASE", str(database_path))
    monkeypatch.setenv("MUSECAPSULE_RAG_ENABLED", "1")

    embed = Mock(
        side_effect=lambda texts: [[1.0] * 384 for _ in texts],
    )
    create_embedder = Mock(return_value=embed)
    monkeypatch.setattr(server, "create_local_embedder", create_embedder)

    received_contexts = []

    def generate(*, text, **kwargs):
        context = json.loads(text)
        received_contexts.append(context)

        assert len(context["reference_chunks"]) == 1
        source = context["reference_chunks"][0]

        return json.dumps({
            "idea_summary": "A bounded agent execution tool.",
            "metaphor_origin": {
                "image_ids": context["idea"]["image_ids"],
                "hypothesis_ids": context["idea"]["hypothesis_ids"],
                "meaning_basis": "A bounded execution space.",
                "mechanic_mapping": "Each run has an explicit attempt budget.",
            },
            "problem": "Retries can continue without clear limits.",
            "audience": "Developers testing agents.",
            "core_scenario": "Run an agent and inspect its attempts.",
            "features": ["Run one bounded scenario"],
            "risks": ["Model behavior may vary"],
            "acceptance_criteria": ["Execution stops at its attempt limit"],
            "references": [{
                "document_id": source["document_id"],
                "chunk_id": source["chunk_id"],
                "quote": "bounded retries",
            }],
        })

    monkeypatch.setattr(server, "request_generation", generate)

    # Keep the real graph, API, ingestion service, and SQLite storage.
    app = server.create_local_app()

    with TestClient(app) as client:
        uploaded = client.post(
            f"/sessions/{session.id}/references",
            json={
                "title": "Reliability notes",
                "text": "Use bounded retries and explicit timeouts.",
            },
        )
        assert uploaded.status_code == 201
        document = uploaded.json()

        endpoint = f"/sessions/{session.id}/briefs"

        if streaming:
            with client.stream("POST", f"{endpoint}/stream") as response:
                assert response.status_code == 200
                body = response.read().decode("utf-8")

            assert body.count("event: session_completed\n") == 1
            assert "event: run_failed\n" not in body
        else:
            response = client.post(endpoint)
            assert response.status_code == 200

        restored = client.get(f"/sessions/{session.id}")
        assert restored.status_code == 200
        saved = restored.json()

    assert len(received_contexts) == 1
    assert saved["revision"] == session.revision + 1
    assert len(saved["briefs"]) == 1

    brief = saved["briefs"][0]
    supplied = received_contexts[0]["reference_chunks"][0]

    assert brief["references"] == [{
        "document_id": document["id"],
        "chunk_id": supplied["chunk_id"],
        "quote": "bounded retries",
    }]
    assert brief["metaphor_origin"]["image_ids"] == [
        str(value) for value in session.ideas[0].image_ids
    ]
    assert brief["metaphor_origin"]["hypothesis_ids"] == [
        str(value) for value in session.ideas[0].hypothesis_ids
    ]
    assert brief["metaphor_origin"]["user_confirmed"] is False
    assert brief["constraints"] == session.intent.constraints

    create_embedder.assert_called_once_with()
    assert embed.call_count == 2  # Document indexing, then query embedding.
    assert session.briefs == []

    with closing(sqlite3.connect(database_path)) as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM session_snapshots
            WHERE session_id = ?
            """,
            (str(session.id),),
        ).fetchone()[0]

    assert count == 2  # Initial snapshot plus one completed blueprint.
