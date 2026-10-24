from pydantic import BaseModel, ConfigDict, Field

from musecapsule.evidence import validate_evidence
from musecapsule.models import EvidenceRef, ImageFragment, Message


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

    Raises:ß
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
