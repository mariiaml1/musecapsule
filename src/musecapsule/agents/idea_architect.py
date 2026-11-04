from collections.abc import Callable
import json
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from musecapsule.knowledge import ReferenceChunk
from musecapsule.models import (
    ArchitectureComponent,
    Hypothesis,
    ImageFragment,
    Intent,
    MVPBrief,
    Message,
    MetaphorOrigin,
    ProductIdea,
    ReferenceCitation,
)
from musecapsule.state import validate_idea_foundation

class ProposedMetaphorOrigin(BaseModel):
    """A proposed interpretation and its connection to product mechanics."""

    model_config = ConfigDict(extra="forbid")

    image_ids: list[UUID] = Field(min_length=1)
    hypothesis_ids: list[UUID]
    meaning_basis: str = Field(min_length=1)
    mechanic_mapping: str = Field(min_length=1)


class BlueprintResponse(BaseModel):
    """Blueprint content proposed by the model, awaiting validation.

    Application code assigns the idea ID and user confirmation state.
    """

    model_config = ConfigDict(extra="forbid")

    idea_summary: str = Field(min_length=1)
    metaphor_origin: ProposedMetaphorOrigin
    problem: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    core_scenario: str = Field(min_length=1)
    features: list[str] = Field(min_length=1, max_length=5)
    risks: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    suggested_architecture: list[ArchitectureComponent] = Field(
        default_factory=list,
        max_length=6,
    )
    references: list[ReferenceCitation] = Field(default_factory=list)


def parse_blueprint_response(
    raw_response: str,
    *,
    idea: ProductIdea,
    intent: Intent,
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
    reference_chunks: list[ReferenceChunk] | None = None,
) -> MVPBrief:
    """Validate blueprint sources and bind the result to the selected idea.

    Preserve user constraints and leave the proposed meaning unconfirmed.

    Raises:
        ValueError: If the response or its source references are invalid.
    """
    parsed = BlueprintResponse.model_validate_json(raw_response)
    origin = parsed.metaphor_origin

    existing_image_ids = {image.id for image in images}
    idea_image_ids = set(idea.image_ids)
    idea_hypothesis_ids = set(idea.hypothesis_ids)
    hypotheses_by_id = {hypothesis.id: hypothesis for hypothesis in hypotheses}

    for image_id in origin.image_ids:
        if image_id not in existing_image_ids:
            raise ValueError("Blueprint references a missing image.")

        if image_id not in idea_image_ids:
            raise ValueError("Blueprint image is not linked to the idea.")

    for hypothesis_id in origin.hypothesis_ids:
        hypothesis = hypotheses_by_id.get(hypothesis_id)

        if hypothesis is None:
            raise ValueError("Blueprint references a missing hypothesis.")

        if hypothesis_id not in idea_hypothesis_ids:
            raise ValueError("Blueprint hypothesis is not linked to the idea.")

        if hypothesis.status not in ("proposed", "supported"):
            raise ValueError("Blueprint references an inactive hypothesis.")

    if set(origin.image_ids) != set(idea.image_ids):
        raise ValueError("Blueprint must preserve all images linked to the idea.")

    if set(origin.hypothesis_ids) != set(idea.hypothesis_ids):
        raise ValueError("Blueprint must preserve all hypotheses linked to the idea.")

    chunks_by_id = {chunk.id: chunk for chunk in (reference_chunks or [])}

    for citation in parsed.references:
        chunk = chunks_by_id.get(citation.chunk_id)

        if chunk is None:
            raise ValueError(
                "Blueprint references a chunk outside the supplied context."
            )

        if citation.document_id != chunk.document_id:
            raise ValueError("Blueprint citation references a different document.")

        if citation.quote not in chunk.text:
            raise ValueError("Blueprint reference quote was not found in the chunk.")

    return MVPBrief(
        idea_id=idea.id,
        idea_summary=parsed.idea_summary,
        metaphor_origin=MetaphorOrigin(
            image_ids=origin.image_ids,
            hypothesis_ids=origin.hypothesis_ids,
            meaning_basis=origin.meaning_basis,
            mechanic_mapping=origin.mechanic_mapping,
            user_confirmed=False,
        ),
        problem=parsed.problem,
        audience=parsed.audience,
        core_scenario=parsed.core_scenario,
        features=parsed.features,
        constraints=list(intent.constraints),
        risks=parsed.risks,
        acceptance_criteria=parsed.acceptance_criteria,
        suggested_architecture=parsed.suggested_architecture,
        references=parsed.references,
    )


def generate_blueprint(
    idea: ProductIdea,
    intent: Intent,
    *,
    messages: list[Message],
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
    generate: Callable[[str], str],
    reference_chunks: list[ReferenceChunk] | None = None,
) -> MVPBrief:
    """Generate an engineering brief while preserving the idea's origin.

    Include dialogue corrections and related narrative sources.
    Do not perform external research or change session state.

    Raises:
        IdeaFoundationError: If a linked hypothesis is missing or inactive.
    """

    validate_idea_foundation(idea, hypotheses)

    supplied_chunks = list(reference_chunks or [])

    related_images = [
        image for image in images
        if image.id in idea.image_ids
    ]
    related_hypotheses = [
        hypothesis for hypothesis in hypotheses
        if hypothesis.id in idea.hypothesis_ids
    ]

    context = json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "idea": idea.model_dump(mode="json"),
            "messages": [message.model_dump(mode="json") for message in messages],
            "images": [image.model_dump(mode="json") for image in related_images],
            "hypotheses": [
                hypothesis.model_dump(mode="json") for hypothesis in related_hypotheses
            ],
            "reference_chunks": [
                {
                    "chunk_id": str(chunk.id),
                    "document_id": str(chunk.document_id),
                    "text": chunk.text,
                }
                for chunk in supplied_chunks
            ],
        },
        ensure_ascii=False,
    )

    raw_response = generate(context)

    return parse_blueprint_response(
        raw_response,
        idea=idea,
        intent=intent,
        images=related_images,
        hypotheses=related_hypotheses,
        reference_chunks=supplied_chunks,
    )
