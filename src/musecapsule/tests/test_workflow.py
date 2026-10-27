import json

import pytest

from musecapsule.models import EvidenceRef, Hypothesis, ImageFragment, Intent, Message
from musecapsule.state import SessionState
from musecapsule.workflow import build_exploration_graph


def test_initial_exploration_graph_preserves_sources_and_orders_steps():
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    calls: list[str] = []

    def generate_images(text: str) -> str:
        calls.append("images")
        assert text == message.text

        return json.dumps(
            {
                "images": [
                    {
                        "label": "Golden note",
                        "quote": "A golden note",
                    }
                ]
            }
        )

    def generate_hypotheses(context: str) -> str:
        calls.append("hypotheses")
        payload = json.loads(context)

        assert payload["intent"]["goal"] == session.intent.goal
        assert payload["messages"][0]["id"] == str(message.id)

        image_id = payload["images"][0]["id"]

        return json.dumps(
            {
                "hypotheses": [
                    {
                        "statement": (
                            "The note could represent one focused capability."
                        ),
                        "image_ids": [image_id],
                        "evidence": [
                            {
                                "message_id": str(message.id),
                                "quote": "A golden note",
                            }
                        ],
                    }
                ]
            }
        )

    def generate_question(context: str) -> str:
        calls.append("question")
        payload = json.loads(context)

        assert len(payload["hypotheses"]) == 1
        assert payload["hypotheses"][0]["status"] == "proposed"

        return json.dumps({"question": "What happens to the note next?"})

    def generate_revisions(_: str) -> str:
        pytest.fail("Revision must not run without existing hypotheses.")

    graph = build_exploration_graph(
        generate_revisions=generate_revisions,
        generate_images=generate_images,
        generate_hypotheses=generate_hypotheses,
        generate_question=generate_question,
    )

    result = graph.invoke(
        {
            "session": session,
            "incoming_message": message,
        }
    )
    updated = result["session"]

    assert calls == ["images", "hypotheses", "question"]

    assert updated.id == session.id
    assert updated.intent == session.intent
    assert updated.messages[0] == message
    assert len(updated.messages) == 2
    assert updated.messages[-1].role == "assistant"
    assert updated.messages[-1].text == "What happens to the note next?"

    assert len(updated.images) == 1
    assert len(updated.hypotheses) == 1
    assert updated.hypotheses[0].image_ids == [updated.images[0].id]
    assert updated.hypotheses[0].evidence[0].message_id == message.id
    assert updated.revision == 4

    assert session.messages == []
    assert session.images == []
    assert session.hypotheses == []
    assert session.revision == 0


def test_exploration_graph_revises_existing_hypothesis():
    original_message = Message(
        role="user",
        text="A note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=original_message.id,
        quote="a transparent capsule",
    )
    image = ImageFragment(
        label="Transparent capsule",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        statement="The transparency could represent inspectable processing.",
        image_ids=[image.id],
        evidence=[source],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Local execution"],
        ),
        messages=[original_message],
        images=[image],
        hypotheses=[hypothesis],
        revision=3,
    )
    clarification = Message(
        role="user",
        text="The capsule is opaque, not transparent.",
    )
    before = session.model_dump()
    calls: list[str] = []

    def generate_images(text: str) -> str:
        calls.append("images")
        assert text == clarification.text
        return '{"images": []}'

    def generate_hypotheses(_: str) -> str:
        pytest.fail("New hypotheses must not be generated on this route.")

    def generate_revisions(context: str) -> str:
        calls.append("revisions")
        payload = json.loads(context)

        assert payload["clarification"]["id"] == str(clarification.id)
        assert payload["hypotheses"][0]["id"] == str(hypothesis.id)

        return json.dumps(
            {
                "revisions": [
                    {
                        "hypothesis_id": str(hypothesis.id),
                        "new_status": "unsupported",
                        "reason": "The clarification contradicts transparency.",
                        "evidence": [
                            {
                                "message_id": str(clarification.id),
                                "quote": "The capsule is opaque",
                            }
                        ],
                    }
                ]
            }
        )

    def generate_question(context: str) -> str:
        calls.append("question")
        payload = json.loads(context)

        assert payload["hypotheses"][0]["status"] == "unsupported"

        return json.dumps({"question": "What happens around the opaque capsule?"})

    graph = build_exploration_graph(
        generate_images=generate_images,
        generate_hypotheses=generate_hypotheses,
        generate_revisions=generate_revisions,
        generate_question=generate_question,
    )
    result = graph.invoke(
        {
            "session": session,
            "incoming_message": clarification,
        }
    )
    updated = result["session"]

    assert calls == ["images", "revisions", "question"]
    assert updated.id == session.id
    assert updated.intent == session.intent
    assert updated.images == session.images
    assert updated.messages[:-1] == [original_message, clarification]
    assert updated.messages[-1].role == "assistant"
    assert updated.messages[-1].text == ("What happens around the opaque capsule?")

    assert len(updated.hypotheses) == 1
    assert updated.hypotheses[0].id == hypothesis.id
    assert updated.hypotheses[0].status == "unsupported"

    assert len(updated.hypothesis_history) == 1
    entry = updated.hypothesis_history[0]
    assert entry.previous == hypothesis
    assert entry.new_status == "unsupported"
    assert entry.evidence[0].message_id == clarification.id
    assert entry.session_revision == 5

    assert updated.revision == 6
    assert session.model_dump() == before
