from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from musecapsule.api import create_app
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    Message,
    MetaphorOrigin,
    MVPBrief,
    ProductIdea,
)
from musecapsule.state import (
    SessionState,
    append_blueprint,
    append_message,
    append_product_ideas,
)
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


def test_api_rejects_idea_request_before_image_exploration(tmp_path):
    def process_ideas(session: SessionState) -> SessionState:
        pytest.fail("Generation must not run without images.")

    app = create_app(
        tmp_path / "sessions.db",
        process_ideas=process_ideas,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={
                "goal": "Build an AI portfolio project",
                "constraints": [],
            },
        ).json()

        response = client.post(f"/sessions/{created['id']}/ideas")

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Explore at least one image before requesting ideas."
        }
        assert client.get(f"/sessions/{created['id']}").json() == created


def test_api_generates_and_persists_ideas_without_adding_messages(tmp_path):
    database_path = tmp_path / "sessions.db"

    message = Message(
        role="user",
        text="A bunny jumps across the grass.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A bunny",
    )
    image = ImageFragment(
        label="Bunny",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        statement="The bunny could represent a deliberately limited agent.",
        image_ids=[image.id],
        evidence=[source],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an unusual AI-agent portfolio project",
            constraints=["Small MVP"],
        ),
        messages=[message],
        images=[image],
        hypotheses=[hypothesis],
        revision=3,
    )
    SessionStore(database_path).save(session)
    before = session.model_dump()

    ideas = [
        ProductIdea(
            title="Tiny Agent Trials",
            description="A bounded arena for observing an agent's actions.",
            goal_alignment="Demonstrates constrained tool use.",
            image_ids=[image.id],
            hypothesis_ids=[hypothesis.id],
        ),
        ProductIdea(
            title="One-Hop Investigator",
            description="An agent investigates one question in small steps.",
            goal_alignment="Demonstrates adaptive investigation.",
            image_ids=[image.id],
            hypothesis_ids=[hypothesis.id],
        ),
    ]
    received_sessions: list[SessionState] = []

    def process_ideas(current: SessionState) -> SessionState:
        received_sessions.append(current)
        return append_product_ideas(current, ideas)

    app = create_app(
        database_path,
        process_ideas=process_ideas,
    )

    with TestClient(app) as client:
        response = client.post(f"/sessions/{session.id}/ideas")

        assert response.status_code == 200
        updated = SessionState.model_validate(response.json())

        assert len(received_sessions) == 1
        assert received_sessions[0] == session
        assert updated.id == session.id
        assert updated.intent == session.intent
        assert updated.messages == session.messages
        assert updated.hypotheses == session.hypotheses
        assert updated.ideas == ideas
        assert updated.revision == session.revision + 1

    # The result must remain available without a generation handler.
    with TestClient(create_app(database_path)) as client:
        response = client.get(f"/sessions/{session.id}")

        assert response.status_code == 200
        assert response.json() == updated.model_dump(mode="json")

    assert session.model_dump() == before


def test_api_selects_existing_idea_and_preserves_selection(tmp_path):
    database_path = tmp_path / "sessions.db"

    message = Message(
        role="user",
        text="A bunny jumps across the grass.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A bunny",
    )
    image = ImageFragment(
        label="Bunny",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        statement="The bunny could represent a deliberately limited agent.",
        image_ids=[image.id],
        evidence=[source],
    )
    ideas = [
        ProductIdea(
            title="Tiny Agent Trials",
            description="A bounded arena for observing an agent's actions.",
            goal_alignment="Demonstrates constrained tool use.",
            image_ids=[image.id],
            hypothesis_ids=[hypothesis.id],
        )
    ]
    session = SessionState(
        intent=Intent(
            goal="Build an unusual AI-agent portfolio project",
            constraints=["Small MVP"],
        ),
        messages=[message],
        images=[image],
        hypotheses=[hypothesis],
        revision=3,
        ideas=ideas,
    )
    SessionStore(database_path).save(session)

    app = create_app(database_path)

    with TestClient(app) as client:
        response = client.post(
            f"/sessions/{session.id}/selection",
            json={"idea_id": str(ideas[0].id)},
        )

        assert response.status_code == 200
        selected = response.json()

        assert selected["selected_idea_id"] == str(ideas[0].id)
        assert selected["revision"] == session.revision + 1
        assert selected["messages"] == session.model_dump(mode="json")["messages"]

        restored = client.get(f"/sessions/{session.id}")
        assert restored.json() == selected

        repeated = client.post(
            f"/sessions/{session.id}/selection",
            json={"idea_id": str(ideas[0].id)},
        )
        assert repeated.status_code == 200
        assert repeated.json() == selected


def test_api_rejects_blueprint_request_without_selection(tmp_path):
    def process_blueprint(session: SessionState) -> SessionState:
        pytest.fail("Generation must not run without a selected idea.")

    app = create_app(
        tmp_path / "sessions.db",
        process_blueprint=process_blueprint,
    )

    with TestClient(app) as client:
        created = client.post(
            "/sessions",
            json={
                "goal": "Build an AI portfolio project",
                "constraints": [],
            },
        ).json()

        response = client.post(f"/sessions/{created['id']}/briefs")

        assert response.status_code == 409
        assert response.json() == {
            "detail": "Select an idea before requesting a blueprint."
        }
        assert client.get(f"/sessions/{created['id']}").json() == created


def test_api_appends_blueprint_versions_for_selected_idea(tmp_path):
    database_path = tmp_path / "sessions.db"
    message = Message(
        role="user",
        text="A bunny jumps across the grass.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A bunny",
    )
    image = ImageFragment(
        label="Bunny",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        statement="The bunny could represent a limited agent.",
        image_ids=[image.id],
        evidence=[source],
    )
    idea = ProductIdea(
        title="Tiny Agent Trials",
        description="A bounded arena for observing an agent.",
        goal_alignment="Demonstrates constrained tool use.",
        image_ids=[image.id],
        hypothesis_ids=[hypothesis.id],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Small MVP"],
        ),
        messages=[message],
        images=[image],
        hypotheses=[hypothesis],
        ideas=[idea],
        selected_idea_id=idea.id,
        revision=4,
    )
    SessionStore(database_path).save(session)

    received_revisions: list[int] = []

    def process_blueprint(current: SessionState) -> SessionState:
        received_revisions.append(current.revision)
        version = len(current.briefs) + 1

        brief = MVPBrief(
            idea_id=idea.id,
            idea_summary=f"Tiny Agent Trials draft {version}",
            metaphor_origin=MetaphorOrigin(
                image_ids=[image.id],
                hypothesis_ids=[hypothesis.id],
                meaning_basis="A small actor with limited actions.",
                mechanic_mapping="The agent acts within a bounded arena.",
            ),
            problem="Agent behavior is difficult to inspect.",
            audience="Developers exploring AI agents.",
            core_scenario="Run a bounded trial and inspect its replay.",
            features=["Bounded trial runner", "Action replay"],
            constraints=list(current.intent.constraints),
            risks=["Model calls may fail"],
            acceptance_criteria=["Every executed action appears in the replay"],
        )
        return append_blueprint(current, brief)

    app = create_app(
        database_path,
        process_blueprint=process_blueprint,
    )

    with TestClient(app) as client:
        first_response = client.post(f"/sessions/{session.id}/briefs")
        assert first_response.status_code == 200
        first = first_response.json()

        second_response = client.post(f"/sessions/{session.id}/briefs")
        assert second_response.status_code == 200
        second = second_response.json()

        assert received_revisions == [4, 5]
        assert first["revision"] == 5
        assert second["revision"] == 6
        assert len(first["briefs"]) == 1
        assert len(second["briefs"]) == 2
        assert second["briefs"][0] == first["briefs"][0]
        assert second["briefs"][1]["idea_summary"] == ("Tiny Agent Trials draft 2")
        assert second["selected_idea_id"] == str(idea.id)
        assert second["messages"] == first["messages"]

        for brief in second["briefs"]:
            assert brief["idea_id"] == str(idea.id)
            assert brief["constraints"] == session.intent.constraints
            assert brief["metaphor_origin"]["image_ids"] == [str(image.id)]
            assert brief["metaphor_origin"]["hypothesis_ids"] == [str(hypothesis.id)]

    with TestClient(create_app(database_path)) as client:
        restored = client.get(f"/sessions/{session.id}")

        assert restored.status_code == 200
        assert restored.json() == second
