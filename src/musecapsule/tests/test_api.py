from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from musecapsule.api import create_app
from musecapsule.models import Message
from musecapsule.state import SessionState, append_message
from musecapsule.storage import SessionStore


def test_api_creates_session_and_restores_it_after_reopening(tmp_path):
    database_path = tmp_path / "sessions.db"
    intent = {
        "goal": "Build an unusual AI-agent portfolio project",
        "constraints": ["Solo development", "Small MVP"],
    }

    with TestClient(create_app(database_path)) as client:
        response = client.post("/sessions", json=intent)

        assert response.status_code == 201
        created = response.json()

        assert UUID(created["id"])
        assert created["intent"] == intent
        assert created["revision"] == 0
        assert created["messages"] == []
        assert created["ideas"] == []
        assert created["briefs"] == []
        assert created["selected_idea_id"] is None

    # Recreate the application to verify persistence beyond its lifetime.
    with TestClient(create_app(database_path)) as client:
        response = client.get(f"/sessions/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created


def test_api_returns_404_for_unknown_session(tmp_path):
    with TestClient(create_app(tmp_path / "sessions.db")) as client:
        response = client.get(f"/sessions/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Session not found."}


def test_api_rejects_blank_goal(tmp_path):
    with TestClient(create_app(tmp_path / "sessions.db")) as client:
        response = client.post(
            "/sessions",
            json={
                "goal": "   ",
                "constraints": [],
            },
        )

    assert response.status_code == 422
    assert any(error["loc"] == ["body", "goal"] for error in response.json()["detail"])


def test_api_processes_message_and_persists_updated_session(tmp_path):
    received: list[Message] = []

    def process_message(
        session: SessionState,
        message: Message,
    ) -> SessionState:
        received.append(message)
        updated = append_message(session, message)

        return append_message(
            updated,
            Message(
                role="assistant",
                text="What happens around the bunny?",
            ),
        )

    app = create_app(
        tmp_path / "sessions.db",
        process_message=process_message,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={
                "goal": "Build an unusual AI-agent portfolio project",
                "constraints": ["Small MVP"],
            },
        ).json()

        narrative = "  A little bunny jumps on the grass.\n"
        response = client.post(
            f"/sessions/{created['id']}/messages",
            json={"text": narrative},
        )

        assert response.status_code == 200
        updated = response.json()

        assert len(received) == 1
        assert received[0].role == "user"
        assert received[0].text == narrative

        assert updated["id"] == created["id"]
        assert updated["intent"] == created["intent"]
        assert updated["revision"] == 2
        assert updated["messages"][0]["id"] == str(received[0].id)
        assert updated["messages"][0]["text"] == narrative
        assert updated["messages"][1]["role"] == "assistant"
        assert updated["messages"][1]["text"] == ("What happens around the bunny?")

        restored = client.get(f"/sessions/{created['id']}")

        assert restored.status_code == 200
        assert restored.json() == updated


def test_api_preserves_session_when_message_processing_fails(tmp_path):
    def process_message(
        session: SessionState,
        message: Message,
    ) -> SessionState:
        # Create an intermediate result, then simulate a later failure.
        append_message(session, message)
        raise RuntimeError("Private provider details")

    app = create_app(
        tmp_path / "sessions.db",
        process_message=process_message,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={
                "goal": "Build an AI portfolio project",
                "constraints": [],
            },
        ).json()

        response = client.post(
            f"/sessions/{created['id']}/messages",
            json={"text": "A little bunny jumps on the grass."},
        )

        assert response.status_code == 502
        assert response.json() == {"detail": "Generation could not be completed."}
        assert "Private provider details" not in response.text

        restored = client.get(f"/sessions/{created['id']}")

        assert restored.status_code == 200
        assert restored.json() == created


def test_api_returns_conflict_without_overwriting_newer_session(tmp_path):
    database_path = tmp_path / "sessions.db"
    competing_updates: list[SessionState] = []

    def process_message(
        session: SessionState,
        message: Message,
    ) -> SessionState:
        # Simulate another request committing while this request is processing.
        competing = append_message(
            session,
            Message(
                role="user",
                text="Another message was saved first.",
            ),
        )
        SessionStore(database_path).save(
            competing,
            expected_revision=session.revision,
        )
        competing_updates.append(competing)

        # This result is based on the now-outdated starting session.
        updated = append_message(session, message)
        return append_message(
            updated,
            Message(
                role="assistant",
                text="What happens around the bunny?",
            ),
        )

    app = create_app(
        database_path,
        process_message=process_message,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={
                "goal": "Build an AI portfolio project",
                "constraints": [],
            },
        ).json()

        response = client.post(
            f"/sessions/{created['id']}/messages",
            json={"text": "A bunny jumps across the grass."},
        )

        assert response.status_code == 409
        assert response.json() == {
            "detail": (
                "Session changed during processing. " "Reload it before retrying."
            )
        }

        restored = client.get(f"/sessions/{created['id']}")

        assert restored.status_code == 200
        assert restored.json() == (competing_updates[0].model_dump(mode="json"))
