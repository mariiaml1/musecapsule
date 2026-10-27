import json
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from musecapsule.evidence import validate_evidence
from musecapsule.models import EvidenceRef, Hypothesis, ImageFragment, Intent, Message
from collections.abc import Callable


class ExtractedImage(BaseModel):
    """An image proposed by the model, awaiting source validation."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class ImageExtractionResponse(BaseModel):
    """The expected JSON response for image extraction."""

    model_config = ConfigDict(extra="forbid")

    images: list[ExtractedImage]


def parse_image_extraction(
    raw_response: str,
    message: Message,
) -> list[ImageFragment]:
    """Parse extracted images and validate their source quotes.

    Assign application-generated IDs and bind evidence to the supplied message.

    Raises:
        ValueError: If the message is not from the user, the response is
            invalid, or a source quote cannot be verified.
    """

    result: list[ImageFragment] = []

    if message.role != "user":
        raise ValueError("Message is not from the user.")

    parsed = ImageExtractionResponse.model_validate_json(raw_response)

    for image in parsed.images:
        evidence_ref = EvidenceRef(
            message_id=message.id,
            quote=image.quote,
        )
        validate_evidence(evidence_ref, message)

        result.append(
            ImageFragment(
                label=image.label,
                evidence=[evidence_ref],
            )
        )

    return result


def extract_images(
    message: Message,
    *,
    generate: Callable[[str], str],
) -> list[ImageFragment]:
    """Extract grounded images using the supplied generation function.

    Validate the message role before generation and verify the full response
    before returning image fragments.

    Raises:
        ValueError: If the message is not from the user or the response is invalid.
        RuntimeError: If generation fails.
    """
    if message.role != "user":
        raise ValueError("Message not from the user role")

    generated_text = generate(message.text)

    return parse_image_extraction(generated_text, message)


class ProposedHypothesis(BaseModel):
    """A model-proposed interpretation awaiting source validation."""

    model_config = ConfigDict(extra="forbid")

    statement: str = Field(min_length=1)
    image_ids: list[UUID] = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)


class HypothesisProposalResponse(BaseModel):
    """The expected JSON response for hypothesis proposals."""

    model_config = ConfigDict(extra="forbid")

    hypotheses: list[ProposedHypothesis] = Field(max_length=3)


def parse_hypothesis_proposals(
    raw_response: str,
    *,
    images: list[ImageFragment],
    messages: list[Message],
) -> list[Hypothesis]:
    """Parse hypothesis proposals and validate their image and source references.

    Assign new IDs and the proposed status in application code.
    Return results only after all proposals pass validation.

    Raises:
        ValueError: If the response or any source reference is invalid.
    """

    result: list[Hypothesis] = []

    parsed = HypothesisProposalResponse.model_validate_json(raw_response)

    messages_by_id = {message.id: message for message in messages}
    existing_image_ids = {image.id for image in images}

    for proposal in parsed.hypotheses:
        for image_id in proposal.image_ids:
            if image_id not in existing_image_ids:
                raise ValueError("Hypothesis references a missing image.")

        for evidence in proposal.evidence:
            message = messages_by_id.get(evidence.message_id)

            if message is None:
                raise ValueError("Evidence references a missing message.")

            validate_evidence(evidence, message)

        result.append(
            Hypothesis(
                statement=proposal.statement,
                image_ids=proposal.image_ids,
                evidence=proposal.evidence,
            )
        )

    return result


def build_hypothesis_context(
    intent: Intent,
    *,
    images: list[ImageFragment],
    messages: list[Message],
) -> str:
    """Serialize the goal and narrative sources for hypothesis generation.

    Preserve existing identifiers so proposals can reference known sources.
    Include only user messages as narrative evidence.
    """
    return json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "messages": [
                message.model_dump(mode="json")
                for message in messages
                if message.role == "user"
            ],
            "images": [image.model_dump(mode="json") for image in images],
        },
        ensure_ascii=False,
    )


def propose_hypotheses(
    intent: Intent,
    *,
    images: list[ImageFragment],
    messages: list[Message],
    generate: Callable[[str], str],
) -> list[Hypothesis]:
    """Generate hypothesis proposals and validate their source references.

    Keep session updates separate from generation and validation.
    """

    if not images:
        return []

    context = build_hypothesis_context(
        intent,
        images=images,
        messages=messages,
    )
    raw_response = generate(context)

    return parse_hypothesis_proposals(
        raw_response,
        images=images,
        messages=messages,
    )


class ProposedHypothesisRevision(BaseModel):
    """A model-proposed status change awaiting application validation."""

    model_config = ConfigDict(extra="forbid")

    hypothesis_id: UUID
    new_status: Literal["supported", "unsupported"]
    reason: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def reject_blank_reason(cls, value: str) -> str:
        """Reject blank reasons while preserving their original text."""
        if not value.strip():
            raise ValueError("Revision reason must not be blank.")
        return value


class HypothesisRevisionResponse(BaseModel):
    """The expected JSON response for proposed hypothesis revisions."""

    model_config = ConfigDict(extra="forbid")

    revisions: list[ProposedHypothesisRevision] = Field(max_length=3)


def parse_hypothesis_revisions(
    raw_response: str,
    *,
    hypotheses: list[Hypothesis],
    message: Message,
) -> list[ProposedHypothesisRevision]:
    """Validate revision proposals against hypotheses and a new user message.

    Require every proposal to cite the supplied clarification.
    Keep session updates separate from response validation.

    Raises:
        ValueError: If the response, status transition or evidence is invalid.
    """
    if message.role != "user":
        raise ValueError("Message is not from the user.")

    parsed = HypothesisRevisionResponse.model_validate_json(raw_response)
    hypotheses_by_id = {hypothesis.id: hypothesis for hypothesis in hypotheses}
    seen_ids: set[UUID] = set()

    for proposal in parsed.revisions:
        hypothesis = hypotheses_by_id.get(proposal.hypothesis_id)

        if hypothesis is None:
            raise ValueError("Hypothesis is missing.")

        if proposal.hypothesis_id in seen_ids:
            raise ValueError("Duplicate hypothesis revision.")

        if hypothesis.status == "superseded":
            raise ValueError("Cannot revise a superseded hypothesis.")

        if hypothesis.status == proposal.new_status:
            raise ValueError("Hypothesis status is unchanged.")

        for evidence in proposal.evidence:
            validate_evidence(evidence, message)

        seen_ids.add(proposal.hypothesis_id)

    return parsed.revisions


def propose_hypothesis_revisions(
    intent: Intent,
    *,
    hypotheses: list[Hypothesis],
    messages: list[Message],
    clarification: Message,
    generate: Callable[[str], str],
) -> list[ProposedHypothesisRevision]:
    """Generate grounded status revisions after a user clarification.

    Include narrative context and require evidence from the clarification.
    Return validated proposals without changing session state.

    Raises:
        ValueError: If the clarification or model response is invalid.
    """
    if clarification.role != "user":
        raise ValueError("Message is not from the user.")

    revisable = [
        hypothesis for hypothesis in hypotheses if hypothesis.status != "superseded"
    ]
    if not revisable:
        return []

    context = json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "messages": [
                message.model_dump(mode="json")
                for message in messages
                if message.role == "user" and message.id != clarification.id
            ],
            "hypotheses": [
                hypothesis.model_dump(mode="json") for hypothesis in revisable
            ],
            "clarification": clarification.model_dump(mode="json"),
        },
        ensure_ascii=False,
    )
    raw_response = generate(context)

    return parse_hypothesis_revisions(
        raw_response,
        hypotheses=revisable,
        message=clarification,
    )
