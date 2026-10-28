from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from musecapsule.api import create_app


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
    assert any(
        error["loc"] == ["body", "goal"]
        for error in response.json()["detail"]
    )
