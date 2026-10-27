import json

from musecapsule.models import Intent, Message
from musecapsule.state import SessionState
from musecapsule.workflow import build_initial_exploration_graph


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

        return json.dumps(
            {"question": "What happens to the note next?"}
        )

    graph = build_initial_exploration_graph(
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
