import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from musecapsule.agents.idea_architect import ProposedMetaphorOrigin, generate_blueprint, parse_blueprint_response
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)

def test_proposed_origin_rejects_model_assigned_confirmation():
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ProposedMetaphorOrigin.model_validate(
            {
                "image_ids": [str(uuid4())],
                "hypothesis_ids": [],
                "meaning_basis": "Selecting one valuable fragment.",
                "mechanic_mapping": ("The user selects one idea to turn into an MVP."),
                "user_confirmed": True,
            }
        )


def test_parse_blueprint_rejects_unrelated_image():
    image_id = uuid4()
    intent = Intent(goal="Build an AI portfolio project")
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    linked_image = ImageFragment(
        id=image_id,
        label="Golden note",
        evidence=[source],
    )
    unrelated_image = ImageFragment(
        label="Golden note",
        evidence=[source],
    )

    idea = ProductIdea(
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[linked_image.id],
        hypothesis_ids=[],
    )
    raw_response = json.dumps(
        {
            "idea_summary": "A local workspace for inspecting AI experiments.",
            "metaphor_origin": {
                "meaning_basis": "One valuable result in a bounded space.",
                "mechanic_mapping": (
                    "Each workspace contains one experiment and its result."
                ),
                "image_ids": [str(unrelated_image.id)],
                "hypothesis_ids": [],
            },
            "problem": "Small AI experiments are difficult to organize.",
            "audience": "Developers building AI prototypes.",
            "core_scenario": "Run an experiment and inspect its saved result.",
            "features": ["Run and save one experiment"],
            "risks": ["Model responses may be invalid"],
            "acceptance_criteria": ["A saved experiment result can be reopened"],
        }
    )

    with pytest.raises(ValueError, match="Blueprint image is not linked to the idea."):
        parse_blueprint_response(
            raw_response,
            idea=idea,
            intent=intent,
            images=[linked_image, unrelated_image],
            hypotheses=[],
        )


def test_parse_blueprint_preserves_intent_and_origin():
    image_id = uuid4()
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development", "Local execution"],
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    linked_image = ImageFragment(
        id=image_id,
        label="Golden note",
        evidence=[source],
    )

    idea = ProductIdea(
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[linked_image.id],
        hypothesis_ids=[],
    )
    raw_response = json.dumps(
        {
            "idea_summary": "A local workspace for inspecting AI experiments.",
            "metaphor_origin": {
                "meaning_basis": "One valuable result in a bounded space.",
                "mechanic_mapping": (
                    "Each workspace contains one experiment and its result."
                ),
                "image_ids": [str(linked_image.id)],
                "hypothesis_ids": [],
            },
            "problem": "Small AI experiments are difficult to organize.",
            "audience": "Developers building AI prototypes.",
            "core_scenario": "Run an experiment and inspect its saved result.",
            "features": ["Run and save one experiment"],
            "risks": ["Model responses may be invalid"],
            "acceptance_criteria": ["A saved experiment result can be reopened"],
        }
    )

    parsed = parse_blueprint_response(
        raw_response,
        idea=idea,
        intent=intent,
        images=[linked_image],
        hypotheses=[],
    )
    assert parsed.acceptance_criteria[0] == "A saved experiment result can be reopened"
    assert parsed.metaphor_origin.image_ids == [linked_image.id]
    assert parsed.risks[0] == "Model responses may be invalid"
    assert parsed.idea_id == idea.id
    assert parsed.constraints == intent.constraints
    assert parsed.metaphor_origin.hypothesis_ids == []
    assert parsed.metaphor_origin.user_confirmed is False
    assert parsed.metaphor_origin.meaning_basis == (
        "One valuable result in a bounded space."
    )
    assert parsed.metaphor_origin.mechanic_mapping == (
        "Each workspace contains one experiment and its result."
    )


def test_generate_blueprint_passes_intent_sources_and_clarifications():
    image_id = uuid4()
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development", "Local execution"],
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    linked_image = ImageFragment(
        id=image_id,
        label="Golden note",
        evidence=[source],
    )

    idea = ProductIdea(
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[linked_image.id],
        hypothesis_ids=[],
    )
    raw_response = json.dumps(
        {
            "idea_summary": "A local workspace for inspecting AI experiments.",
            "metaphor_origin": {
                "meaning_basis": "One valuable result in a bounded space.",
                "mechanic_mapping": (
                    "Each workspace contains one experiment and its result."
                ),
                "image_ids": [str(linked_image.id)],
                "hypothesis_ids": [],
            },
            "problem": "Small AI experiments are difficult to organize.",
            "audience": "Developers building AI prototypes.",
            "core_scenario": "Run an experiment and inspect its saved result.",
            "features": ["Run and save one experiment"],
            "risks": ["Model responses may be invalid"],
            "acceptance_criteria": ["A saved experiment result can be reopened"],
        }
    )

    clarification = Message(
        role="user",
        text="The capsule is opaque, not transparent.",
    )
    received_contexts: list[dict] = []

    def generate(context: str) -> str:
        payload = json.loads(context)
        received_contexts.append(payload)
        return raw_response

    brief = generate_blueprint(
        idea,
        intent,
        messages=[message, clarification],
        images=[linked_image],
        hypotheses=[],
        generate=generate,
    )

    assert len(received_contexts) == 1
    context = received_contexts[0]

    assert context["intent"] == intent.model_dump(mode="json")
    assert context["idea"]["id"] == str(idea.id)
    assert context["messages"] == [
        message.model_dump(mode="json"),
        clarification.model_dump(mode="json"),
    ]
    assert context["images"] == [linked_image.model_dump(mode="json")]
    assert context["hypotheses"] == []

    assert brief.idea_id == idea.id
    assert brief.constraints == intent.constraints
    assert brief.metaphor_origin.user_confirmed is False


def test_parse_blueprint_preserves_combined_origin():
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development", "Local execution"],
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image_note = ImageFragment(
        label="Golden note",
        evidence=[source],
    )
    capsule_source = EvidenceRef(
        message_id=message.id,
        quote="a transparent capsule",
    )
    image_capsule = ImageFragment(
        label="Transparent capsule",
        evidence=[capsule_source],
    )
    first_hypothesis = Hypothesis(
        statement=(
            "The note inside the capsule could represent "
            "a valuable result within a bounded workspace."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    second_hypothesis = Hypothesis(
        statement=(
            "The capsule's transparency could represent "
            "making an experiment's result inspectable."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    idea = ProductIdea(
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[image_note.id, image_capsule.id],
        hypothesis_ids=[first_hypothesis.id, second_hypothesis.id],
    )
    raw_response = json.dumps(
        {
            "idea_summary": "A local workspace for inspecting AI experiments.",
            "metaphor_origin": {
                "meaning_basis": "One valuable result in a bounded space.",
                "mechanic_mapping": (
                    "Each workspace contains one experiment and its result."
                ),
                "image_ids": [str(image_note.id), str(image_capsule.id)],
                "hypothesis_ids": [str(first_hypothesis.id), str(second_hypothesis.id)],
            },
            "problem": "Small AI experiments are difficult to organize.",
            "audience": "Developers building AI prototypes.",
            "core_scenario": "Run an experiment and inspect its saved result.",
            "features": ["Run and save one experiment"],
            "risks": ["Model responses may be invalid"],
            "acceptance_criteria": ["A saved experiment result can be reopened"],
        }
    )

    clarification = Message(
        role="user",
        text="The capsule is opaque, not transparent.",
    )
    received_contexts: list[dict] = []

    def generate(context: str) -> str:
        payload = json.loads(context)
        received_contexts.append(payload)
        return raw_response

    brief = generate_blueprint(
        idea,
        intent,
        messages=[message, clarification],
        images=[image_note, image_capsule],
        hypotheses=[first_hypothesis, second_hypothesis],
        generate=generate,
    )

    assert set(brief.metaphor_origin.image_ids) == {
        image_note.id,
        image_capsule.id,
    }
    assert set(brief.metaphor_origin.hypothesis_ids) == {
        first_hypothesis.id,
        second_hypothesis.id,
    }


def test_parse_blueprint_rejects_dropped_origin_image():
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development", "Local execution"],
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image_note = ImageFragment(
        label="Golden note",
        evidence=[source],
    )
    capsule_source = EvidenceRef(
        message_id=message.id,
        quote="a transparent capsule",
    )
    image_capsule = ImageFragment(
        label="Transparent capsule",
        evidence=[capsule_source],
    )
    first_hypothesis = Hypothesis(
        statement=(
            "The note inside the capsule could represent "
            "a valuable result within a bounded workspace."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    second_hypothesis = Hypothesis(
        statement=(
            "The capsule's transparency could represent "
            "making an experiment's result inspectable."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    idea = ProductIdea(
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[image_note.id, image_capsule.id],
        hypothesis_ids=[first_hypothesis.id, second_hypothesis.id],
    )
    raw_response = json.dumps(
        {
            "idea_summary": "A local workspace for inspecting AI experiments.",
            "metaphor_origin": {
                "meaning_basis": "One valuable result in a bounded space.",
                "mechanic_mapping": (
                    "Each workspace contains one experiment and its result."
                ),
                "image_ids": [str(image_note.id)],
                "hypothesis_ids": [str(first_hypothesis.id), str(second_hypothesis.id)],
            },
            "problem": "Small AI experiments are difficult to organize.",
            "audience": "Developers building AI prototypes.",
            "core_scenario": "Run an experiment and inspect its saved result.",
            "features": ["Run and save one experiment"],
            "risks": ["Model responses may be invalid"],
            "acceptance_criteria": ["A saved experiment result can be reopened"],
        }
    )

    received_contexts: list[dict] = []

    def generate(context: str) -> str:
        payload = json.loads(context)
        received_contexts.append(payload)
        return raw_response

    with pytest.raises(
        ValueError,
        match="Blueprint must preserve all images linked to the idea.",
    ):
        parse_blueprint_response(
            raw_response,
            idea=idea,
            intent=intent,
            images=[image_note, image_capsule],
            hypotheses=[first_hypothesis, second_hypothesis],
        )


def test_parse_blueprint_rejects_dropped_origin_hypothesis():
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development", "Local execution"],
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image_note = ImageFragment(
        label="Golden note",
        evidence=[source],
    )
    capsule_source = EvidenceRef(
        message_id=message.id,
        quote="a transparent capsule",
    )
    image_capsule = ImageFragment(
        label="Transparent capsule",
        evidence=[capsule_source],
    )
    first_hypothesis = Hypothesis(
        statement=(
            "The note inside the capsule could represent "
            "a valuable result within a bounded workspace."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    second_hypothesis = Hypothesis(
        statement=(
            "The capsule's transparency could represent "
            "making an experiment's result inspectable."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    idea = ProductIdea(
        title="Inspectable AI Sandbox",
        description="A local tool for inspecting small AI experiments.",
        goal_alignment="A bounded AI portfolio project for solo development.",
        image_ids=[image_note.id, image_capsule.id],
        hypothesis_ids=[first_hypothesis.id, second_hypothesis.id],
    )
    raw_response = json.dumps(
        {
            "idea_summary": "A local workspace for inspecting AI experiments.",
            "metaphor_origin": {
                "meaning_basis": "One valuable result in a bounded space.",
                "mechanic_mapping": (
                    "Each workspace contains one experiment and its result."
                ),
                "image_ids": [str(image_note.id), str(image_capsule.id)],
                "hypothesis_ids": [str(first_hypothesis.id)],
            },
            "problem": "Small AI experiments are difficult to organize.",
            "audience": "Developers building AI prototypes.",
            "core_scenario": "Run an experiment and inspect its saved result.",
            "features": ["Run and save one experiment"],
            "risks": ["Model responses may be invalid"],
            "acceptance_criteria": ["A saved experiment result can be reopened"],
        }
    )

    clarification = Message(
        role="user",
        text="The capsule is opaque, not transparent.",
    )
    received_contexts: list[dict] = []

    def generate(context: str) -> str:
        payload = json.loads(context)
        received_contexts.append(payload)
        return raw_response

    with pytest.raises(
        ValueError,
        match="Blueprint must preserve all hypotheses linked to the idea.",
    ):
        parse_blueprint_response(
            raw_response,
            idea=idea,
            intent=intent,
            images=[image_note, image_capsule],
            hypotheses=[first_hypothesis, second_hypothesis],
        )
