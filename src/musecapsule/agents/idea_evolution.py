from collections.abc import Callable
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from musecapsule.models import Hypothesis, ImageFragment, Intent, Message, ProductIdea


class ProposedProductIdea(BaseModel):
    """A model-proposed product idea awaiting source validation."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    goal_alignment: str = Field(min_length=1)
    image_ids: list[UUID] = Field(min_length=1)
    hypothesis_ids: list[UUID]


class IdeaGenerationResponse(BaseModel):
    """Two or three product proposals returned by the model."""

    model_config = ConfigDict(extra="forbid")

    ideas: list[ProposedProductIdea] = Field(
        min_length=2,
        max_length=3,
    )


def parse_product_ideas(
    raw_response: str,
    *,
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
) -> list[ProductIdea]:
    """Parse product proposals and validate their source references.

    Allow only proposed or supported hypotheses as inspiration.
    Assign idea IDs in application code without changing session state.

    Raises:
        ValueError: If the response or a source reference is invalid.
    """
    parsed = IdeaGenerationResponse.model_validate_json(raw_response)
    existing_image_ids = {image.id for image in images}
    hypotheses_by_id = {hypothesis.id: hypothesis for hypothesis in hypotheses}
    result: list[ProductIdea] = []

    for proposal in parsed.ideas:
        for image_id in proposal.image_ids:
            if image_id not in existing_image_ids:
                raise ValueError("Idea references a missing image.")

        for hypothesis_id in proposal.hypothesis_ids:
            hypothesis = hypotheses_by_id.get(hypothesis_id)

            if hypothesis is None:
                raise ValueError("Idea references a missing hypothesis.")

            if hypothesis.status not in ("proposed", "supported"):
                raise ValueError("Idea references an inactive hypothesis.")

        result.append(
            ProductIdea(
                title=proposal.title,
                description=proposal.description,
                goal_alignment=proposal.goal_alignment,
                image_ids=proposal.image_ids,
                hypothesis_ids=proposal.hypothesis_ids,
            )
        )

    return result


def generate_product_ideas(
    intent: Intent,
    *,
    messages: list[Message],
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
    generate: Callable[[str], str],
) -> list[ProductIdea]:
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
    )
