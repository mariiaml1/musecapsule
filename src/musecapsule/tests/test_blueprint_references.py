import json
from uuid import uuid4

import pytest

from musecapsule.agents.idea_architect import generate_blueprint, parse_blueprint_response
from musecapsule.knowledge import ReferenceChunk
from musecapsule.models import (
    EvidenceRef,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)
from musecapsule.state import SessionState
from musecapsule.workflow import build_exploration_graph


@pytest.fixture
def blueprint_reference_case():
    image = ImageFragment(
        label="Capsule",
        evidence=[
            EvidenceRef(
                message_id=uuid4(),
                quote="A capsule",
            )
        ],
    )
    idea = ProductIdea(
        title="Bounded Agent Arena",
        description="Run a small agent within an explicit attempt budget.",
        goal_alignment="Demonstrates agent reliability.",
        image_ids=[image.id],
        hypothesis_ids=[],
    )
    text = "Use bounded retries and explicit timeouts."
    chunk = ReferenceChunk(
        document_id=uuid4(),
        session_id=uuid4(),
        start=0,
        end=len(text),
        text=text,
    )
    payload = {
        "idea_summary": "A bounded agent testing arena.",
        "metaphor_origin": {
            "image_ids": [str(image.id)],
            "hypothesis_ids": [],
            "meaning_basis": "A bounded space.",
            "mechanic_mapping": "Each run has an explicit attempt budget.",
        },
        "problem": "Agent retries can continue without clear limits.",
        "audience": "Developers testing agents.",
        "core_scenario": "Run a scenario and inspect its attempts.",
        "features": ["Run one bounded scenario"],
        "risks": ["Model behavior may vary"],
        "acceptance_criteria": ["A run stops at its attempt limit"],
        "references": [
            {
                "document_id": str(chunk.document_id),
                "chunk_id": str(chunk.id),
                "quote": "bounded retries",
            }
        ],
    }
    arguments = {
        "idea": idea,
        "intent": Intent(goal="Build an AI portfolio project"),
        "images": [image],
        "hypotheses": [],
    }

    return arguments, chunk, payload


def test_blueprint_preserves_valid_reference(blueprint_reference_case):
    arguments, chunk, payload = blueprint_reference_case

    brief = parse_blueprint_response(
        json.dumps(payload),
        **arguments,
        reference_chunks=[chunk],
    )

    assert len(brief.references) == 1
    assert brief.references[0].document_id == chunk.document_id
    assert brief.references[0].chunk_id == chunk.id
    assert brief.references[0].quote == "bounded retries"


@pytest.mark.parametrize(
    ("field", "value", "expected_error"),
    [
        (
            "chunk_id",
            str(uuid4()),
            "Blueprint references a chunk outside the supplied context.",
        ),
        (
            "document_id",
            str(uuid4()),
            "Blueprint citation references a different document.",
        ),
        (
            "quote",
            "Retry forever",
            "Blueprint reference quote was not found in the chunk.",
        ),
    ],
)
def test_blueprint_rejects_invalid_reference(
    blueprint_reference_case, field, value, expected_error
):
    arguments, chunk, payload = blueprint_reference_case
    payload["references"][0][field] = value

    with pytest.raises(ValueError) as error:
        parse_blueprint_response(
            json.dumps(payload),
            **arguments,
            reference_chunks=[chunk],
        )

    assert str(error.value) == expected_error


def test_blueprint_rejects_reference_without_supplied_context(
    blueprint_reference_case,
):
    arguments, _, payload = blueprint_reference_case

    with pytest.raises(ValueError, match="outside the supplied context"):
        parse_blueprint_response(
            json.dumps(payload),
            **arguments,
        )


def test_generate_blueprint_passes_reference_context_and_preserves_citation(
    blueprint_reference_case,
):
    arguments, chunk, payload = blueprint_reference_case
    received = []

    def generate(context):
        received.append(json.loads(context))
        return json.dumps(payload)

    brief = generate_blueprint(
        **arguments,
        messages=[],
        reference_chunks=[chunk],
        generate=generate,
    )

    assert len(received) == 1
    assert received[0]["reference_chunks"] == [
        {
            "chunk_id": str(chunk.id),
            "document_id": str(chunk.document_id),
            "text": chunk.text,
        }
    ]
    assert received[0]["idea"]["id"] == str(arguments["idea"].id)
    assert received[0]["intent"] == arguments["intent"].model_dump(
        mode="json",
    )
    assert brief.references[0].chunk_id == chunk.id
    assert brief.references[0].quote == "bounded retries"
    assert brief.metaphor_origin.image_ids == arguments["idea"].image_ids
    assert brief.metaphor_origin.user_confirmed is False


def test_generate_blueprint_remains_compatible_without_references(
    blueprint_reference_case,
):
    arguments, _, payload = blueprint_reference_case
    payload["references"] = []

    def generate(context):
        assert json.loads(context)["reference_chunks"] == []
        return json.dumps(payload)

    brief = generate_blueprint(
        **arguments,
        messages=[],
        generate=generate,
    )

    assert brief.references == []


@pytest.mark.parametrize("foreign_session", [False, True])
def test_blueprint_workflow_retrieves_only_current_session_sources(
    blueprint_reference_case,
    foreign_session,
):
    arguments, chunk, payload = blueprint_reference_case
    image = arguments["images"][0]
    idea = arguments["idea"]

    session = SessionState(
        id=chunk.session_id,
        intent=arguments["intent"],
        messages=[
            Message(
                id=image.evidence[0].message_id,
                role="user",
                text="A capsule",
            )
        ],
        images=arguments["images"],
        hypotheses=arguments["hypotheses"],
        ideas=[idea],
        selected_idea_id=idea.id,
    )
    before = session.model_dump()
    calls = []

    returned_chunk = chunk
    if foreign_session:
        returned_chunk = chunk.model_copy(
            update={"session_id": uuid4()},
        )

    def retrieve(session_id, selected_idea):
        calls.append("retrieve")
        assert session_id == session.id
        assert selected_idea.id == idea.id
        return [returned_chunk]

    def generate(context):
        calls.append("generate")
        supplied = json.loads(context)["reference_chunks"]
        assert supplied[0]["chunk_id"] == str(chunk.id)
        return json.dumps(payload)

    def unexpected_generation(context):
        pytest.fail("Unrelated generation must not run.")

    graph = build_exploration_graph(
        generate_images=unexpected_generation,
        generate_hypotheses=unexpected_generation,
        generate_revisions=unexpected_generation,
        generate_question=unexpected_generation,
        generate_ideas=unexpected_generation,
        generate_architecture=generate,
        retrieve_references=retrieve,
    )

    if foreign_session:
        with pytest.raises(ValueError, match="different session"):
            graph.invoke({
                "session": session,
                "command": "build_blueprint",
            })

        assert calls == ["retrieve"]
    else:
        result = graph.invoke({
            "session": session,
            "command": "build_blueprint",
        })
        updated = result["session"]

        assert calls == ["retrieve", "generate"]
        assert updated.revision == session.revision + 1
        assert updated.briefs[-1].references[0].chunk_id == chunk.id
        assert updated.briefs[-1].idea_id == idea.id

    assert session.model_dump() == before
