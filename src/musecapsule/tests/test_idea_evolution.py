import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from musecapsule.agents.idea_evolution import (
    IdeaGenerationResponse,
    IdeaRevisionResponse,
    ProposedProductIdea,
    generate_product_ideas,
    parse_idea_revision,
    parse_product_ideas,
    revise_product_idea,
)
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)


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
        assert idea.description == ("A local tool for inspecting small AI experiments.")
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


def test_parse_product_ideas_preserves_all_images_of_existing_hypothesis():
    note_image_id = uuid4()
    capsule_image_id = uuid4()
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image_note = ImageFragment(
        id=capsule_image_id,
        label="Golden note",
        evidence=[source],
    )
    capsule_source = EvidenceRef(
        message_id=message.id,
        quote="a transparent capsule",
    )
    image_capsule = ImageFragment(
        id=capsule_image_id,
        label="Transparent capsule",
        evidence=[capsule_source],
    )
    hypothesis = Hypothesis(
        statement=(
            "The note inside the capsule could represent "
            "a valuable result within a bounded workspace."
        ),
        image_ids=[image_note.id, image_capsule.id],
        evidence=[source, capsule_source],
    )
    raw_response = json.dumps(
        {
            "ideas": [
                {
                    "title": "Inspectable AI Sandbox",
                    "description": "A local tool for inspecting small AI experiments.",
                    "goal_alignment": "A bounded AI portfolio project for solo development.",
                    "image_ids": [str(image_note.id)],
                    "hypothesis_ids": [str(hypothesis.id)],
                    "new_hypotheses": [],
                },
                {
                    "title": "Inspectable AI Sandbox",
                    "description": "A local tool for inspecting small AI experiments.",
                    "goal_alignment": "A bounded AI portfolio project for solo development.",
                    "image_ids": [str(image_note.id)],
                    "hypothesis_ids": [str(hypothesis.id)],
                    "new_hypotheses": [],
                },
            ]
        }
    )
    parsed = parse_product_ideas(
        raw_response,
        images=[image_capsule, image_note],
        messages=[message],
        hypotheses=[hypothesis],
    )

    assert set(parsed.ideas[0].image_ids) == {
        image_note.id,
        image_capsule.id,
    }
    assert parsed.ideas[0].hypothesis_ids == [hypothesis.id]
    assert parsed.new_hypotheses == []


def test_idea_revision_response_accepts_one_proposal():
    image_id = uuid4()
    hypothesis_id = uuid4()

    response = IdeaRevisionResponse.model_validate(
        {
            "idea": {
                "title": "Revised Capsule Probe",
                "description": "Evaluate observable AI outputs.",
                "goal_alignment": "A bounded AI portfolio project.",
                "image_ids": [str(image_id)],
                "hypothesis_ids": [str(hypothesis_id)],
            }
        }
    )

    assert response.idea.image_ids == [image_id]
    assert response.idea.hypothesis_ids == [hypothesis_id]
    assert response.idea.new_hypotheses == []


@pytest.mark.parametrize("field", ["id", "previous_idea_id"])
def test_idea_revision_response_rejects_model_assigned_identifiers(field):
    proposal = {
        "title": "Revised Capsule Probe",
        "description": "Evaluate observable AI outputs.",
        "goal_alignment": "A bounded AI portfolio project.",
        "image_ids": [str(uuid4())],
        "hypothesis_ids": [],
        field: str(uuid4()),
    }

    with pytest.raises(
        ValidationError,
        match="Extra inputs are not permitted",
    ):
        IdeaRevisionResponse.model_validate({"idea": proposal})


@pytest.mark.parametrize("status", ["proposed", "unsupported"])
def test_parse_idea_revision_validates_new_foundation_and_preserves_history(
    status,
):
    message = Message(
        role="user",
        text="The capsule is opaque.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="The capsule is opaque",
    )
    image = ImageFragment(
        label="Opaque capsule",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        statement="Opacity could inspire black-box evaluation.",
        status=status,
        image_ids=[image.id],
        evidence=[source],
    )
    previous_idea = ProductIdea(
        title="Capsule Probe",
        description="Inspect an AI experiment.",
        goal_alignment="Build an AI portfolio project.",
        image_ids=[image.id],
        hypothesis_ids=[],
    )
    before = previous_idea.model_dump(mode="json")
    raw_response = json.dumps(
        {
            "idea": {
                "title": "Capsule Probe — Behavioral Evaluation",
                "description": "Evaluate observable AI outputs.",
                "goal_alignment": "Build an AI portfolio project.",
                "image_ids": [str(image.id)],
                "hypothesis_ids": [str(hypothesis.id)],
                "new_hypotheses": [],
            }
        }
    )

    if status == "unsupported":
        with pytest.raises(
            ValueError,
            match="Idea references an inactive hypothesis",
        ):
            parse_idea_revision(
                raw_response,
                previous_idea=previous_idea,
                images=[image],
                hypotheses=[hypothesis],
                messages=[message],
            )
    else:
        result = parse_idea_revision(
            raw_response,
            previous_idea=previous_idea,
            images=[image],
            hypotheses=[hypothesis],
            messages=[message],
        )

        assert len(result.ideas) == 1
        revised = result.ideas[0]
        assert revised.id != previous_idea.id
        assert revised.previous_idea_id == previous_idea.id
        assert revised.image_ids == [image.id]
        assert revised.hypothesis_ids == [hypothesis.id]
        assert result.new_hypotheses == []

    assert previous_idea.model_dump(mode="json") == before


def test_revise_product_idea_passes_current_context_and_preserves_previous_idea():
    intent = Intent(
        goal="Build an AI portfolio project",
        constraints=["Solo development"],
    )
    original = Message(
        role="user",
        text="A transparent capsule contains a note.",
    )
    clarification = Message(
        role="user",
        text="The capsule was never transparent. It is opaque.",
    )
    source = EvidenceRef(
        message_id=original.id,
        quote="A transparent capsule",
    )
    image = ImageFragment(
        label="Transparent capsule",
        evidence=[source],
    )
    old_hypothesis = Hypothesis(
        statement="Transparency could inspire inspectable execution.",
        status="unsupported",
        image_ids=[image.id],
        evidence=[source],
    )
    previous_idea = ProductIdea(
        title="Capsule Probe",
        description="Inspect the internal steps of an AI experiment.",
        goal_alignment="Build an AI portfolio project.",
        image_ids=[image.id],
        hypothesis_ids=[old_hypothesis.id],
    )
    before = previous_idea.model_dump(mode="json")
    received_contexts: list[dict] = []

    def generate(context: str) -> str:
        received_contexts.append(json.loads(context))
        return json.dumps(
            {
                "idea": {
                    "title": "Capsule Probe — Output Evaluation",
                    "description": "Evaluate observable AI outputs.",
                    "goal_alignment": "Build an AI portfolio project.",
                    "image_ids": [str(image.id)],
                    "hypothesis_ids": [],
                    "new_hypotheses": [
                        {
                            "statement": (
                                "The opaque capsule could inspire "
                                "evaluation through external behavior."
                            ),
                            "image_ids": [str(image.id)],
                            "evidence": [
                                {
                                    "message_id": str(clarification.id),
                                    "quote": "It is opaque",
                                }
                            ],
                        }
                    ],
                }
            }
        )

    result = revise_product_idea(
        previous_idea,
        intent,
        messages=[original, clarification],
        images=[image],
        hypotheses=[old_hypothesis],
        generate=generate,
    )

    assert len(received_contexts) == 1
    context = received_contexts[0]
    assert context["intent"] == intent.model_dump(mode="json")
    assert context["previous_idea"] == before
    assert context["messages"] == [
        original.model_dump(mode="json"),
        clarification.model_dump(mode="json"),
    ]
    assert context["hypotheses"][0]["status"] == "unsupported"
    assert context["images"] == [image.model_dump(mode="json")]

    revised = result.ideas[0]
    new_hypothesis = result.new_hypotheses[0]
    assert revised.previous_idea_id == previous_idea.id
    assert revised.hypothesis_ids == [new_hypothesis.id]
    assert old_hypothesis.id not in revised.hypothesis_ids
    assert new_hypothesis.status == "proposed"
    assert new_hypothesis.evidence[0].message_id == clarification.id
    assert previous_idea.model_dump(mode="json") == before
