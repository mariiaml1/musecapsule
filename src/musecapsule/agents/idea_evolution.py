from collections.abc import Callable
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from musecapsule.evidence import validate_evidence
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)


class ProposedIdeaHypothesis(BaseModel):
    """A new interpretation proposed as the foundation of a product idea.

    Application code assigns its ID and proposed status.
    """

    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    image_ids: list[UUID] = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)


class ProposedProductIdea(BaseModel):
    """A model-proposed product idea awaiting source validation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    goal_alignment: str = Field(min_length=1)
    image_ids: list[UUID] = Field(min_length=1)
    hypothesis_ids: list[UUID]
    new_hypotheses: list[ProposedIdeaHypothesis] = Field(
        default_factory=list,
        max_length=2,
    )


class IdeaGenerationResponse(BaseModel):
    """Two or three product proposals returned by the model."""

    model_config = ConfigDict(extra="forbid")

    ideas: list[ProposedProductIdea] = Field(
        min_length=2,
        max_length=3,
    )


class IdeaGenerationResult(BaseModel):
    """Validated ideas and the new hypotheses required by their references."""

    ideas: list[ProductIdea]
    new_hypotheses: list[Hypothesis]


def parse_product_ideas(
    raw_response: str,
    *,
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
    messages: list[Message],
) -> IdeaGenerationResult:
    """Validate idea foundations and assign IDs to new interpretations.

    Return the complete batch without changing session state.

    Raises:
        ValueError: If an idea has no meaning foundation or sources are invalid.
    """

    parsed = IdeaGenerationResponse.model_validate_json(raw_response)
    existing_image_ids = {image.id for image in images}
    hypotheses_by_id = {hypothesis.id: hypothesis for hypothesis in hypotheses}
    messages_by_id = {message.id: message for message in messages}

    ideas: list[ProductIdea] = []
    new_hypotheses: list[Hypothesis] = []

    for proposal in parsed.ideas:
        idea_image_ids = list(proposal.image_ids)

        for image_id in proposal.image_ids:
            if image_id not in existing_image_ids:
                raise ValueError("Idea references a missing image.")

        linked_ids = list(proposal.hypothesis_ids)

        for hypothesis_id in linked_ids:
            hypothesis = hypotheses_by_id.get(hypothesis_id)

            if hypothesis is None:
                raise ValueError("Idea references a missing hypothesis.")

            if hypothesis.status not in ("proposed", "supported"):
                raise ValueError("Idea references an inactive hypothesis.")

            for image_id in hypothesis.image_ids:
                if image_id not in existing_image_ids:
                    raise ValueError("Idea hypothesis references a missing image.")

                if image_id not in idea_image_ids:
                    idea_image_ids.append(image_id)

        for proposed_meaning in proposal.new_hypotheses:
            for image_id in proposed_meaning.image_ids:
                if image_id not in proposal.image_ids:
                    raise ValueError("New hypothesis must reference the idea's images.")

            for evidence in proposed_meaning.evidence:
                message = messages_by_id.get(evidence.message_id)

                if message is None:
                    raise ValueError("Evidence references a missing message.")

                validate_evidence(evidence, message)

            hypothesis = Hypothesis(
                statement=proposed_meaning.statement,
                image_ids=proposed_meaning.image_ids,
                evidence=proposed_meaning.evidence,
            )
            new_hypotheses.append(hypothesis)
            linked_ids.append(hypothesis.id)

        if not linked_ids:
            raise ValueError("Idea must have at least one meaning hypothesis.")

        ideas.append(
            ProductIdea(
                title=proposal.title,
                description=proposal.description,
                goal_alignment=proposal.goal_alignment,
                image_ids=idea_image_ids,
                hypothesis_ids=linked_ids,
            )
        )

    return IdeaGenerationResult(
        ideas=ideas,
        new_hypotheses=new_hypotheses,
    )


def generate_product_ideas(
    intent: Intent,
    *,
    messages: list[Message],
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
    generate: Callable[[str], str],
) -> IdeaGenerationResult:
    """Generate product ideas grounded in narrative sources and user intent.

    Exclude inactive hypotheses and validate returned source references.
    Keep session updates separate from generation.

    Raises:
        ValueError: If no images exist or the response is invalid.
    """
    if not images:
        raise ValueError("At least one image is required to generate ideas.")

    active_hypotheses = [
        hypothesis
        for hypothesis in hypotheses
        if hypothesis.status in ("proposed", "supported")
    ]

    context = json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "messages": [message.model_dump(mode="json") for message in messages],
            "images": [image.model_dump(mode="json") for image in images],
            "hypotheses": [
                hypothesis.model_dump(mode="json") for hypothesis in active_hypotheses
            ],
        },
        ensure_ascii=False,
    )
    raw_response = generate(context)

    return parse_product_ideas(
        raw_response,
        images=images,
        hypotheses=active_hypotheses,
        messages=messages,
    )
