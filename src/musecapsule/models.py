from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Intent(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    goal: str = Field(min_length=1)
    constraints: list[str] = Field(default_factory=list)


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Literal["user", "assistant"]
    text: str = Field(min_length=1)

    @field_validator("text", mode="after")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Message text must not be blank.")
        return value


class EvidenceRef(BaseModel):
    message_id: UUID
    quote: str = Field(min_length=1)

    @field_validator("quote", mode="after")
    @classmethod
    def reject_blank_quote(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Evidence quote must not be blank.")
        return value


class ImageFragment(BaseModel):
    """An image extracted from the user's narrative, grounded in source quotes.
    Represents narrative content rather than a symbolic interpretation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    label: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)


class Hypothesis(BaseModel):
    """A revisable interpretation grounded in narrative images and source quotes.

    Represents a model hypothesis rather than an established user fact.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    statement: str = Field(min_length=1)
    status: Literal["proposed", "supported", "unsupported", "superseded"] = "proposed"
    image_ids: list[UUID] = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)


class HypothesisRevision(BaseModel):
    """A recorded status change with the previous hypothesis and new evidence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    previous: Hypothesis
    new_status: Literal["proposed", "supported", "unsupported", "superseded"]
    reason: str = Field(min_length=1)
    evidence: list[EvidenceRef] = Field(min_length=1)
    session_revision: int = Field(ge=1)


class ProductIdea(BaseModel):
    """A product proposal linked to narrative sources and optional hypotheses.

    Represents an unvalidated idea, not evidence of novelty or market demand.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    id: UUID = Field(default_factory=uuid4)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    goal_alignment: str = Field(min_length=1)
    image_ids: list[UUID] = Field(min_length=1)
    hypothesis_ids: list[UUID] = Field(default_factory=list)
