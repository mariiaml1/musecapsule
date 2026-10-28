from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class MVPBrief(BaseModel):
    """An implementation proposal for a selected product idea.

    Does not establish market demand, novelty or external verification.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    idea_id: UUID
    problem: str = Field(min_length=1)
    audience: str = Field(min_length=1)
    core_scenario: str = Field(min_length=1)
    features: list[str] = Field(min_length=1, max_length=5)
    constraints: list[str] = Field(min_length=1)
    risks: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)

    @field_validator(
        "features",
        "constraints",
        "risks",
        "acceptance_criteria",
    )
    @classmethod
    def reject_blank_items(cls, values: list[str]) -> list[str]:
        """Reject empty list items and normalize surrounding whitespace."""
        normalized = [value.strip() for value in values]

        if any(not value for value in normalized):
            raise ValueError("Brief list items must not be blank.")

        return normalized


class SimilarSolution(BaseModel):
    """A similar solution returned by an external search adapter."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    snippet: str = Field(min_length=1)


class ExternalCheck(BaseModel):
    """The recorded outcome of an external search attempt.

    Assigned by application code, never inferred from an LLM response.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    idea_id: UUID
    status: Literal["not_run", "completed", "unavailable"]
    query: str | None = None
    results: list[SimilarSolution] = Field(default_factory=list)
    reason: str | None = None

    @model_validator(mode="after")
    def validate_search_outcome(self) -> Self:
        """Require fields consistent with the recorded search status."""
        if self.status == "not_run":
            if self.query is not None or self.results or self.reason is not None:
                raise ValueError(
                    "A check that was not run must not contain search data."
                )
            return self

        if self.query is None or not self.query.strip():
            raise ValueError("An attempted search requires a nonblank query.")

        if self.status == "completed":
            if self.reason is not None:
                raise ValueError("A completed search must not contain an error reason.")
            return self

        if self.results:
            raise ValueError("An unavailable search must not contain results.")

        if self.reason is None or not self.reason.strip():
            raise ValueError("An unavailable search requires a nonblank reason.")

        return self
