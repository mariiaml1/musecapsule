import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from musecapsule.agents.idea_evolution import (
    IdeaGenerationResponse,
    ProposedProductIdea,
    generate_product_ideas,
    parse_product_ideas,
)
from musecapsule.models import EvidenceRef, Hypothesis, ImageFragment, Intent, Message


@pytest.mark.parametrize("count", [0, 1, 4])
def test_idea_generation_response_rejects_invalid_idea_count(count):
    from uuid import uuid4

    proposal = {
        "title": "Inspectable AI Sandbox",
        "description": "A local tool for inspecting small AI experiments.",
        "goal_alignment": "A bounded AI portfolio project for solo development.",
        "image_ids": [str(uuid4())],
        "hypothesis_ids": [],
    }

    with pytest.raises(ValidationError):
        IdeaGenerationResponse.model_validate(
            {"ideas": [proposal.copy() for _ in range(count)]}
        )


def test_parse_product_ideas_returns_grounded_ideas():
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
            "ideas": [
                {
                    "title": "Inspectable AI Sandbox",
                    "description": "A local tool for inspecting small AI experiments.",
                    "goal_alignment": "A bounded AI portfolio project for solo development.",
                    "image_ids": [str(image_id)],
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
                    "title": "Inspectable AI Sandbox",
                    "description": "A local tool for inspecting small AI experiments.",
                    "goal_alignment": "A bounded AI portfolio project for solo development.",
                    "image_ids": [str(image_id)],
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
            ]
        }
    )
    parsed = parse_product_ideas(
        raw_response,
        images=[image],
        hypotheses=[],
        messages=[message],
    )

    assert len(parsed.ideas) == 2
    assert len(parsed.new_hypotheses) == 2
    assert parsed.ideas[0].id != parsed.ideas[1].id
    assert parsed.new_hypotheses[0].id != parsed.new_hypotheses[1].id

    for idea, hypothesis in zip(
        parsed.ideas,
        parsed.new_hypotheses,
        strict=True,
    ):
        assert idea.title == "Inspectable AI Sandbox"
        assert idea.description == (
            "A local tool for inspecting small AI experiments."
        )
        assert idea.goal_alignment == (
            "A bounded AI portfolio project for solo development."
        )
        assert idea.image_ids == [image.id]
        assert idea.hypothesis_ids == [hypothesis.id]

        assert hypothesis.status == "proposed"
        assert hypothesis.image_ids == [image.id]
        assert hypothesis.evidence == [source]
        assert hypothesis.statement == (
            "The golden note could represent one valuable result "
            "within a bounded workspace."
        )


@pytest.mark.parametrize(
    "status",
    ["unsupported", "superseded"],
)
def test_parse_product_ideas_rejects_inactive_hypothesis(status):
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
    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        image_ids=[image_id],
        evidence=[source],
        status=status,
    )
    raw_response = json.dumps(
        {
            "ideas": [
                {
                    "title": "Inspectable AI Sandbox",
                    "description": "A local tool for inspecting small AI experiments.",
                    "goal_alignment": "A bounded AI portfolio project for solo development.",
                    "image_ids": [str(image_id)],
                    "hypothesis_ids": [str(hypothesis.id)],
                },
                {
                    "title": "Inspectable AI Sandbox",
                    "description": "A local tool for inspecting small AI experiments.",
                    "goal_alignment": "A bounded AI portfolio project for solo development.",
                    "image_ids": [str(image_id)],
                    "hypothesis_ids": [str(hypothesis.id)],
                },
            ]
        }
    )

    with pytest.raises(ValueError, match="Idea references an inactive hypothesis."):
        parse_product_ideas(
            raw_response,
            images=[image],
            hypotheses=[hypothesis],
            messages=[message],
        )


def test_generate_product_ideas_rejects_missing_images_before_generation():
    def generate(_: str) -> str:
        pytest.fail("Generation must not run without images.")

    with pytest.raises(
        ValueError,
        match="At least one image is required to generate ideas.",
    ):
        generate_product_ideas(
            Intent(goal="Build an AI portfolio project"),
            messages=[],
            images=[],
            hypotheses=[],
            generate=generate,
        )


def test_proposed_idea_accepts_new_grounded_hypothesis():
    image_id = uuid4()
    message_id = uuid4()

    proposal = ProposedProductIdea.model_validate(
        {
            "title": "Hidden Melody",
            "description": (
                "An ear-training app that hides the answer until an attempt."
            ),
            "goal_alignment": "A small local AI portfolio project.",
            "image_ids": [str(image_id)],
            "hypothesis_ids": [],
            "new_hypotheses": [
                {
                    "statement": (
                        "The opaque capsule could represent withholding "
                        "an answer until the user makes an attempt."
                    ),
                    "image_ids": [str(image_id)],
                    "evidence": [
                        {
                            "message_id": str(message_id),
                            "quote": "The capsule is opaque",
                        }
                    ],
                }
            ],
        }
    )

    assert proposal.hypothesis_ids == []
    assert len(proposal.new_hypotheses) == 1

    meaning = proposal.new_hypotheses[0]
    assert meaning.image_ids == [image_id]
    assert meaning.evidence[0].message_id == message_id
