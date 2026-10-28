from uuid import uuid4

import pytest
from pydantic import ValidationError

from musecapsule.evidence import validate_evidence
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    MVPBrief,
    Message,
)


def test_intent_rejects_non_string_constrain():
    with pytest.raises(ValidationError):
        Intent(
            goal="Build an AI-agent portfolio project",
            constraints=[123],
        )


@pytest.mark.parametrize("goal", ["", " ", "\t\n"])
def test_intent_rejects_blank_goal(goal: str):
    with pytest.raises(ValidationError):
        Intent(goal=goal)


def test_message_preserves_original_text():
    original = "  A glowing capsule.\n"

    message = Message(role="user", text=original)

    assert message.text == original


def test_message_rejects_empty_text():
    with pytest.raises(ValidationError):
        Message(role="user", text="")


@pytest.mark.parametrize("text", [" ", "\t", "\n", " \t\n "])
def test_message_rejects_whitespace_only_text(text: str):
    with pytest.raises(ValidationError):
        Message(role="user", text=text)


def test_evidence_accepts_exact_user_quote():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    validate_evidence(evidence, message)


def test_evidence_rejects_wrong_user_quote():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A silver key",
    )

    with pytest.raises(ValueError):
        validate_evidence(evidence, message)


def test_evidence_rejects_blank_quote():
    with pytest.raises(ValidationError):
        EvidenceRef(message_id=uuid4(), quote="   ")


def test_evidence_rejects_different_message_id():
    message1 = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    message2 = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message1.id,
        quote="A golden note",
    )

    with pytest.raises(ValueError):
        validate_evidence(evidence, message2)


def test_evidence_rejects_not_user_message():
    message = Message(
        role="assistant",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    with pytest.raises(ValueError):
        validate_evidence(evidence, message)


@pytest.mark.parametrize("label", ["", " ", "\t\n"])
def test_image_frame_rejects_blank_label(label: str):
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )

    evidence_ref = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    with pytest.raises(ValidationError):
        ImageFragment(label=label, evidence=[evidence_ref])


def test_image_frame_rejects_blank_evidence():
    with pytest.raises(ValidationError):
        ImageFragment(
            label="Golden note",
            evidence=[],
        )


def test_image_frame_accepts_created_evidenceref():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )

    evidence_ref = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    fragment = ImageFragment(
        label="Golden note",
        evidence=[
            evidence_ref,
        ],
    )

    assert fragment.evidence[0].quote == evidence_ref.quote
    assert fragment.evidence[0].message_id == evidence_ref.message_id


@pytest.mark.parametrize("evidence_fields", [{}, {"evidence": []}])
def test_image_fragment_requires_evidence(evidence_fields):
    with pytest.raises(ValidationError):
        ImageFragment(label="Golden note", **evidence_fields)


def test_hypothesis_defaults_to_proposed():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        image_ids=[uuid4()],
        evidence=[evidence],
    )

    assert hypothesis.status == "proposed"


@pytest.mark.parametrize("statement", ["", " ", "\t\n"])
def test_hypothesis_rejects_blank_statement(statement: str):
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    with pytest.raises(ValidationError):
        Hypothesis(statement=statement, image_ids=[uuid4()], evidence=[evidence])


@pytest.mark.parametrize("image_ids_fields", [{}, {"image_ids": []}])
def test_hypothesis_requires_image_ids(image_ids_fields):
    evidence = EvidenceRef(
        message_id=uuid4(),
        quote="A golden note",
    )

    with pytest.raises(ValidationError):
        Hypothesis(
            statement="The note may represent a selectable idea.",
            evidence=[evidence],
            **image_ids_fields,
        )


@pytest.mark.parametrize("evidence_fields", [{}, {"evidence": []}])
def test_hypothesis_requires_evidence(evidence_fields):
    with pytest.raises(ValidationError):
        Hypothesis(
            statement="The note may represent a selectable idea.",
            image_ids=[uuid4()],
            **evidence_fields,
        )


@pytest.mark.parametrize(
    "field_name",
    ["features", "constraints", "risks", "acceptance_criteria"],
)
def test_mvp_brief_rejects_blank_list_items(field_name):
    fields = {
        "idea_id": uuid4(),
        "problem": "Developers need a bounded way to inspect AI experiments.",
        "audience": "Developers building local AI prototypes.",
        "core_scenario": "Run an experiment and inspect its saved result.",
        "features": ["Run one experiment"],
        "constraints": ["Solo development"],
        "risks": ["Model responses may be invalid"],
        "acceptance_criteria": ["A valid result can be saved and reopened"],
    }
    fields[field_name] = ["Valid item", "   "]

    with pytest.raises(
        ValidationError,
        match="Brief list items must not be blank.",
    ):
        MVPBrief.model_validate(fields)
