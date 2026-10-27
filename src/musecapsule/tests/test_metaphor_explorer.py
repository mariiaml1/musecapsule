import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from musecapsule.agents.metaphor_explorer import (
    ProposedHypothesisRevision,
    build_hypothesis_context,
    extract_images,
    parse_hypothesis_proposals,
    parse_hypothesis_revisions,
    parse_image_extraction,
    propose_hypotheses,
    propose_hypothesis_revisions,
)
from musecapsule.models import EvidenceRef, Hypothesis, ImageFragment, Intent, Message

def test_parse_image_extraction_returns_grounded_images():
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    raw_response = """
    {
        "images": [
            {"label": "Golden note", "quote": "A golden note"},
            {"label": "Transparent capsule", "quote": "a transparent capsule"}
        ]
    }
    """

    result = parse_image_extraction(raw_response, message)

    assert len(result) == 2
    assert result[0].id != result[1].id

    expected = [
        ("Golden note", "A golden note"),
        ("Transparent capsule", "a transparent capsule"),
    ]

    for fragment, (label, quote) in zip(result, expected, strict=True):
        assert fragment.label == label
        assert len(fragment.evidence) == 1
        assert fragment.evidence[0].message_id == message.id
        assert fragment.evidence[0].quote == quote


def test_parse_image_extraction_rejects_fabricated_quote():
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    raw_response = """
       {
           "images": [
               {"label": "Golden note", "quote": "some"}
           ]
       }
       """

    with pytest.raises(
        ValueError, match="Evidence quote was not found in the message."
    ):
        parse_image_extraction(raw_response, message)


def test_parse_image_extraction_accepts_empty_images():
    message = Message(
        role="user",
        text="Please continue.",
    )

    result = parse_image_extraction('{"images": []}', message)

    assert result == []


def test_extract_images_passes_message_text_to_generation():
    message = Message(
        role="user",
        text="A golden note floats.",
    )
    received_texts = []

    def generate(text: str) -> str:
        received_texts.append(text)
        return """
        {"images": [{"label": "Golden note", "quote": "A golden note"}]}
        """

    result = extract_images(message, generate=generate)

    assert received_texts == [message.text]
    assert len(result) == 1
    assert result[0].label == "Golden note"
    assert result[0].evidence[0].message_id == message.id


def test_extract_images_rejects_assistant_before_generation():
    message = Message(
        role="assistant",
        text="What happens inside the capsule?",
    )

    def generate(text: str) -> str:
        pytest.fail("Generation must not run for an assistant message.")

    with pytest.raises(ValueError, match="Message not from the user role"):
        extract_images(message, generate=generate)


def test_parse_hypothesis_proposals_returns_grounded_hypotheses():
    image_id = uuid4()
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image = ImageFragment(
        id=image_id,
        label="Golden note",
        evidence=[source],
    )
    raw_response = json.dumps(
        {
            "hypotheses": [
                {
                    "statement": "The note may represent choosing one idea to develop.",
                    "image_ids": [str(image_id)],
                    "evidence": [source.model_dump(mode="json")],
                }
            ]
        }
    )

    result = parse_hypothesis_proposals(
        raw_response, messages=[message], images=[image]
    )

    assert len(result) == 1

    hypothesis = result[0]

    assert hypothesis.statement == (
        "The note may represent choosing one idea to develop."
    )
    assert hypothesis.status == "proposed"
    assert hypothesis.image_ids == [image.id]
    assert hypothesis.evidence == [source]
    assert isinstance(hypothesis.id, UUID)


def test_parse_hypothesis_proposals_rejects_fabricated_quote():
    image_id = uuid4()
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image = ImageFragment(
        id=image_id,
        label="Golden note",
        evidence=[source],
    )
    raw_response = json.dumps(
        {
            "hypotheses": [
                {
                    "statement": "The note may represent choosing one idea to develop.",
                    "image_ids": [str(image_id)],
                    "evidence": [
                        {
                            "message_id": str(message.id),
                            "quote": "some",
                        }
                    ],
                }
            ]
        }
    )

    with pytest.raises(
        ValueError, match="Evidence quote was not found in the message."
    ):
        parse_hypothesis_proposals(raw_response, messages=[message], images=[image])


def test_parse_hypothesis_proposals_rejects_unknown_image():
    image_id = uuid4()
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image = ImageFragment(
        label="Golden note",
        evidence=[source],
    )
    raw_response = json.dumps(
        {
            "hypotheses": [
                {
                    "statement": "The note may represent choosing one idea to develop.",
                    "image_ids": [str(image.id), str(image_id)],
                    "evidence": [source.model_dump(mode="json")],
                }
            ]
        }
    )

    with pytest.raises(ValueError, match="Hypothesis references a missing image."):
        parse_hypothesis_proposals(raw_response, messages=[message], images=[image])


def test_build_hypothesis_context_preserves_goal_and_sources():
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development", "Local execution"],
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
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

    context = build_hypothesis_context(
        intent,
        messages=[message],
        images=[image],
    )
    payload = json.loads(context)

    assert payload["intent"]["goal"] == intent.goal
    assert payload["intent"]["constraints"] == intent.constraints
    assert payload["messages"][0]["id"] == str(message.id)
    assert payload["messages"][0]["text"] == message.text
    assert payload["images"][0]["id"] == str(image.id)
    assert payload["images"][0]["evidence"][0]["message_id"] == str(message.id)
    assert payload["images"][0]["evidence"][0]["quote"] == "A golden note"


def test_propose_hypotheses_skips_generation_without_images():
    def generate(_: str) -> str:
        pytest.fail("Generation must not run without images.")

    result = propose_hypotheses(
        Intent(goal="Build an AI portfolio project"),
        images=[],
        messages=[],
        generate=generate,
    )

    assert result == []


@pytest.mark.parametrize("reason", ["", " ", "\t\n"])
def test_proposed_hypothesis_revision_rejects_blank_reason(reason):
    with pytest.raises(ValidationError):
        ProposedHypothesisRevision(
            hypothesis_id=uuid4(),
            new_status="unsupported",
            reason=reason,
            evidence=[
                EvidenceRef(
                    message_id=uuid4(),
                    quote="The note cannot be selected",
                )
            ],
        )


def test_parse_hypothesis_revisions_accepts_grounded_clarification():
    image_id = uuid4()
    message = Message(
        role="user",
        text="The note cannot be selected.",
    )
    original_message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=original_message.id,
        quote="A golden note",
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        image_ids=[image_id],
        evidence=[source],
    )

    raw_response = json.dumps(
        {
            "revisions": [
                {
                    "hypothesis_id": str(hypothesis.id),
                    "new_status": "unsupported",
                    "reason": "The user clarified that the note cannot be selected.",
                    "evidence": [
                        {
                            "message_id": str(message.id),
                            "quote": "The note cannot be selected",
                        }
                    ],
                }
            ]
        }
    )

    payload = parse_hypothesis_revisions(
        raw_response, hypotheses=[hypothesis], message=message
    )

    assert len(payload) == 1
    assert payload[0].evidence[0].quote == "The note cannot be selected"
    assert payload[0].hypothesis_id == hypothesis.id
    assert payload[0].new_status == "unsupported"
    assert payload[0].evidence[0].message_id == message.id


def test_parse_hypothesis_revisions_rejects_fabricated_quote():
    image_id = uuid4()
    message = Message(
        role="user",
        text="The note cannot be selected.",
    )
    original_message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=original_message.id,
        quote="A golden note",
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        image_ids=[image_id],
        evidence=[source],
    )

    raw_response = json.dumps(
        {
            "revisions": [
                {
                    "hypothesis_id": str(hypothesis.id),
                    "new_status": "unsupported",
                    "reason": "The user clarified that the note cannot be selected.",
                    "evidence": [
                        {
                            "message_id": str(message.id),
                            "quote": "Some text",
                        }
                    ],
                }
            ]
        }
    )

    with pytest.raises(
        ValueError, match="Evidence quote was not found in the message."
    ):
        parse_hypothesis_revisions(
            raw_response, hypotheses=[hypothesis], message=message
        )


def test_propose_hypothesis_revisions_skips_generation_without_hypotheses():
    def generate(_: str) -> str:
        pytest.fail("Generation must not run without hypotheses.")

    result = propose_hypothesis_revisions(
        Intent(goal="Build an AI portfolio project"),
        hypotheses=[],
        messages=[],
        clarification=Message(
            role="user",
            text="The note cannot be selected.",
        ),
        generate=generate,
    )

    assert result == []
