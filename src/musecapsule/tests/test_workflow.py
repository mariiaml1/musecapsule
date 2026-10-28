import json
from uuid import uuid4

import pytest

from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)
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

    def generate_ideas(_: str) -> str:
        pytest.fail("Idea generation must not run during exploration.")

    def unexpected_architecture(_: str) -> str:
        pytest.fail("Blueprint generation must not run on this route.")

    graph = build_exploration_graph(
        generate_revisions=generate_revisions,
        generate_images=generate_images,
        generate_hypotheses=generate_hypotheses,
        generate_question=generate_question,
        generate_ideas=generate_ideas,
        generate_architecture=unexpected_architecture,
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

    def generate_ideas(_: str) -> str:
        pytest.fail("Idea generation must not run during exploration.")

    def unexpected_architecture(_: str) -> str:
        pytest.fail("Blueprint generation must not run on this route.")

    graph = build_exploration_graph(
        generate_images=generate_images,
        generate_hypotheses=generate_hypotheses,
        generate_revisions=generate_revisions,
        generate_question=generate_question,
        generate_ideas=generate_ideas,
        generate_architecture=unexpected_architecture,
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


def test_exploration_graph_generates_ideas_without_exploration():
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    image = ImageFragment(
        label="Golden note",
        evidence=[
            EvidenceRef(
                message_id=message.id,
                quote="A golden note",
            )
        ],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
        messages=[message],
        images=[image],
        revision=2,
    )
    before = session.model_dump()
    calls: list[str] = []

    def unexpected_generation(_: str) -> str:
        pytest.fail("Exploration must not run for an idea request.")

    def generate_ideas(context: str) -> str:
        calls.append("ideas")
        payload = json.loads(context)

        assert payload["intent"] == session.intent.model_dump(mode="json")
        assert payload["messages"][0]["id"] == str(message.id)
        assert payload["images"][0]["id"] == str(image.id)
        assert payload["hypotheses"] == []

        return json.dumps(
            {
                "ideas": [
                    {
                        "title": "Local Experiment Capsule",
                        "description": (
                            "A local tool that packages one AI experiment "
                            "and its result into a self-contained workspace."
                        ),
                        "goal_alignment": (
                            "A small AI portfolio project for solo development."
                        ),
                        "image_ids": [str(image.id)],
                        "hypothesis_ids": [],
                        "new_hypotheses": [
                            {
                                "statement": (
                                    "The golden note could represent one valuable result "
                                    "within a bounded workspace."
                                ),
                                "image_ids": [str(image.id)],
                                "evidence": [
                                    {
                                        "message_id": str(message.id),
                                        "quote": "A golden note",
                                    }
                                ],
                            }
                        ],
                    },
                    {
                        "title": "One Note Idea Picker",
                        "description": (
                            "A local assistant that helps a developer select "
                            "one idea from a collection of rough notes."
                        ),
                        "goal_alignment": (
                            "A bounded project demonstrating LLM integration."
                        ),
                        "image_ids": [str(image.id)],
                        "hypothesis_ids": [],
                        "new_hypotheses": [
                            {
                                "statement": (
                                    "The golden note could represent one promising idea "
                                    "selected from a collection."
                                ),
                                "image_ids": [str(image.id)],
                                "evidence": [
                                    {
                                        "message_id": str(message.id),
                                        "quote": "A golden note",
                                    }
                                ],
                            }
                        ],
                    },
                ]
            }
        )

    def unexpected_architecture(_: str) -> str:
        pytest.fail("Blueprint generation must not run on this route.")

    graph = build_exploration_graph(
        generate_images=unexpected_generation,
        generate_hypotheses=unexpected_generation,
        generate_revisions=unexpected_generation,
        generate_question=unexpected_generation,
        generate_ideas=generate_ideas,
        generate_architecture=unexpected_architecture,
    )

    result = graph.invoke(
        {
            "session": session,
            "command": "generate_ideas",
        }
    )
    updated = result["session"]

    assert calls == ["ideas"]
    assert len(updated.ideas) == 2
    assert updated.ideas[0].title == "Local Experiment Capsule"
    assert updated.ideas[1].title == "One Note Idea Picker"
    assert updated.ideas[0].id != updated.ideas[1].id

    assert len(updated.hypotheses) == 2
    assert updated.hypotheses[0].id != updated.hypotheses[1].id

    for idea, hypothesis in zip(
        updated.ideas,
        updated.hypotheses,
        strict=True,
    ):
        assert idea.image_ids == [image.id]
        assert idea.hypothesis_ids == [hypothesis.id]
        assert hypothesis.status == "proposed"
        assert hypothesis.evidence[0].message_id == message.id

    assert updated.id == session.id
    assert updated.intent == session.intent
    assert updated.messages == session.messages
    assert updated.images == session.images
    assert updated.hypothesis_history == session.hypothesis_history
    assert updated.revision == session.revision + 3

    assert session.model_dump() == before


def test_exploration_graph_selects_idea_without_generation():
    chosen_idea_id = uuid4()
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    image = ImageFragment(
        label="Golden note",
        evidence=[
            EvidenceRef(
                message_id=message.id,
                quote="A golden note",
            )
        ],
    )
    idea = ProductIdea(
        id=chosen_idea_id,
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[image.id],
        hypothesis_ids=[],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
        messages=[message],
        images=[image],
        ideas=[idea],
    )

    def unexpected_generation(_: str) -> str:
        pytest.fail("Selection must not invoke generation.")

    def unexpected_architecture(_: str) -> str:
        pytest.fail("Blueprint generation must not run on this route.")

    graph = build_exploration_graph(
        generate_images=unexpected_generation,
        generate_hypotheses=unexpected_generation,
        generate_revisions=unexpected_generation,
        generate_question=unexpected_generation,
        generate_ideas=unexpected_generation,
        generate_architecture=unexpected_architecture,
    )

    result = graph.invoke(
        {
            "session": session,
            "command": "select_idea",
            "idea_id": chosen_idea_id,
        }
    )
    updated = result["session"]

    assert updated.selected_idea_id == idea.id
    assert updated.revision == session.revision + 1
    assert updated.messages == session.messages
    assert updated.ideas == session.ideas
    assert session.selected_idea_id is None


def test_exploration_graph_builds_blueprint_for_selected_idea():
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    image = ImageFragment(
        label="Golden note",
        evidence=[
            EvidenceRef(
                message_id=message.id,
                quote="A golden note",
            )
        ],
    )
    idea = ProductIdea(
        title="Experiment Capsule",
        description="A local workspace for one AI experiment.",
        goal_alignment="A bounded portfolio project for solo development.",
        image_ids=[image.id],
        hypothesis_ids=[],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
        messages=[message],
        images=[image],
        ideas=[idea],
        selected_idea_id=idea.id,
    )
    before = session.model_dump()
    calls: list[str] = []

    def unexpected_generation(_: str) -> str:
        pytest.fail("Other AI roles must not run during blueprint generation.")

    def generate_architecture(context: str) -> str:
        calls.append("architect")
        payload = json.loads(context)

        assert payload["idea"]["id"] == str(idea.id)
        assert payload["intent"] == session.intent.model_dump(mode="json")
        assert payload["images"][0]["id"] == str(image.id)
        assert payload["messages"][0]["text"] == message.text

        return json.dumps(
            {
                "idea_summary": "A local workspace for one AI experiment.",
                "metaphor_origin": {
                    "image_ids": [str(image.id)],
                    "hypothesis_ids": [],
                    "meaning_basis": "One valuable result in a bounded space.",
                    "mechanic_mapping": (
                        "One workspace contains one experiment and its result."
                    ),
                },
                "problem": "Small AI experiments are difficult to revisit.",
                "audience": "Developers building AI prototypes.",
                "core_scenario": "Run, save, and reopen an experiment.",
                "features": ["Save and reopen an experiment result"],
                "risks": ["Model responses may be invalid"],
                "acceptance_criteria": [
                    "A saved result can be reopened without another LLM call"
                ],
            }
        )

    graph = build_exploration_graph(
        generate_images=unexpected_generation,
        generate_hypotheses=unexpected_generation,
        generate_revisions=unexpected_generation,
        generate_question=unexpected_generation,
        generate_ideas=unexpected_generation,
        generate_architecture=generate_architecture,
    )

    result = graph.invoke(
        {
            "session": session,
            "command": "build_blueprint",
        }
    )
    updated = result["session"]

    assert calls == ["architect"]
    assert len(updated.briefs) == 1

    brief = updated.briefs[0]
    assert brief.idea_id == idea.id
    assert brief.constraints == session.intent.constraints
    assert brief.metaphor_origin.image_ids == [image.id]
    assert brief.metaphor_origin.user_confirmed is False

    assert updated.selected_idea_id == idea.id
    assert updated.messages == session.messages
    assert updated.ideas == session.ideas
    assert updated.revision == session.revision + 1
    assert session.model_dump() == before


def test_workflow_preserves_combined_origin_from_idea_to_blueprint():
    message = Message(
        role="user",
        text="A golden note floats inside an opaque capsule.",
    )
    note_source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    capsule_source = EvidenceRef(
        message_id=message.id,
        quote="an opaque capsule",
    )
    note = ImageFragment(
        label="Golden note",
        evidence=[note_source],
    )
    capsule = ImageFragment(
        label="Opaque capsule",
        evidence=[capsule_source],
    )
    existing_hypothesis = Hypothesis(
        statement="The golden note could represent one valuable result.",
        image_ids=[note.id],
        evidence=[note_source],
    )
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
        messages=[message],
        images=[note, capsule],
        hypotheses=[existing_hypothesis],
    )
    before = session.model_dump()
    calls: list[str] = []

    def unexpected_generation(_: str) -> str:
        pytest.fail("Exploration must not run on these command routes.")

    def generate_ideas(context: str) -> str:
        calls.append("ideas")
        payload = json.loads(context)

        assert {item["id"] for item in payload["images"]} == {
            str(note.id),
            str(capsule.id),
        }
        assert payload["hypotheses"][0]["id"] == str(existing_hypothesis.id)

        return json.dumps(
            {
                "ideas": [
                    {
                        "title": "Sealed Result",
                        "description": (
                            "Process one note locally and reveal one useful "
                            "result only when the user requests it."
                        ),
                        "goal_alignment": "A bounded local AI portfolio project.",
                        "image_ids": [str(note.id), str(capsule.id)],
                        "hypothesis_ids": [str(existing_hypothesis.id)],
                        "new_hypotheses": [
                            {
                                "statement": (
                                    "The note within an opaque capsule could "
                                    "represent a valuable result withheld "
                                    "until a deliberate reveal."
                                ),
                                "image_ids": [str(note.id), str(capsule.id)],
                                "evidence": [
                                    note_source.model_dump(mode="json"),
                                    capsule_source.model_dump(mode="json"),
                                ],
                            }
                        ],
                    },
                    {
                        "title": "One Note Summary",
                        "description": "Turn one note into one concise summary.",
                        "goal_alignment": "A small local summarization project.",
                        "image_ids": [str(note.id)],
                        "hypothesis_ids": [str(existing_hypothesis.id)],
                        "new_hypotheses": [],
                    },
                ]
            }
        )

    def generate_architecture(context: str) -> str:
        calls.append("architect")
        payload = json.loads(context)

        image_ids = {str(note.id), str(capsule.id)}
        hypothesis_ids = set(payload["idea"]["hypothesis_ids"])

        assert payload["idea"]["title"] == "Sealed Result"
        assert set(payload["idea"]["image_ids"]) == image_ids
        assert len(hypothesis_ids) == 2
        assert str(existing_hypothesis.id) in hypothesis_ids

        assert {item["id"] for item in payload["images"]} == image_ids
        assert {item["id"] for item in payload["hypotheses"]} == hypothesis_ids

        new_meaning = next(
            item
            for item in payload["hypotheses"]
            if item["id"] != str(existing_hypothesis.id)
        )
        assert set(new_meaning["image_ids"]) == image_ids
        assert new_meaning["status"] == "proposed"

        return json.dumps(
            {
                "idea_summary": "Reveal one useful result from a local note.",
                "metaphor_origin": {
                    "image_ids": payload["idea"]["image_ids"],
                    "hypothesis_ids": payload["idea"]["hypothesis_ids"],
                    "meaning_basis": (
                        "A valuable result remains enclosed until requested."
                    ),
                    "mechanic_mapping": (
                        "Process the note locally, keep the result hidden, "
                        "and reveal it on the user's explicit action."
                    ),
                },
                "problem": "Users need a focused takeaway from one note.",
                "audience": "People organizing personal notes.",
                "core_scenario": (
                    "Import a note, generate a result, and choose to reveal it."
                ),
                "features": ["Local processing", "User-controlled reveal"],
                "risks": ["The generated takeaway may be inaccurate"],
                "acceptance_criteria": [
                    "The generated result stays hidden until reveal is selected"
                ],
            }
        )

    graph = build_exploration_graph(
        generate_images=unexpected_generation,
        generate_hypotheses=unexpected_generation,
        generate_revisions=unexpected_generation,
        generate_question=unexpected_generation,
        generate_ideas=generate_ideas,
        generate_architecture=generate_architecture,
    )

    generated = graph.invoke({"session": session, "command": "generate_ideas"})[
        "session"
    ]

    chosen = next(idea for idea in generated.ideas if idea.title == "Sealed Result")
    new_hypotheses = [
        item for item in generated.hypotheses if item.id != existing_hypothesis.id
    ]

    assert len(new_hypotheses) == 1
    new_hypothesis = new_hypotheses[0]

    expected_images = {note.id, capsule.id}
    expected_hypotheses = {existing_hypothesis.id, new_hypothesis.id}

    assert set(chosen.image_ids) == expected_images
    assert set(chosen.hypothesis_ids) == expected_hypotheses
    assert set(new_hypothesis.image_ids) == expected_images
    assert new_hypothesis.evidence == [note_source, capsule_source]

    selected = graph.invoke(
        {
            "session": generated,
            "command": "select_idea",
            "idea_id": chosen.id,
        }
    )["session"]

    completed = graph.invoke({"session": selected, "command": "build_blueprint"})[
        "session"
    ]

    assert calls == ["ideas", "architect"]
    assert len(completed.briefs) == 1

    brief = completed.briefs[0]
    assert brief.idea_id == chosen.id
    assert set(brief.metaphor_origin.image_ids) == expected_images
    assert set(brief.metaphor_origin.hypothesis_ids) == expected_hypotheses
    assert brief.metaphor_origin.user_confirmed is False
    assert brief.constraints == session.intent.constraints

    assert completed.selected_idea_id == chosen.id
    assert completed.messages == session.messages
    assert completed.revision == session.revision + 4
    assert session.model_dump() == before
