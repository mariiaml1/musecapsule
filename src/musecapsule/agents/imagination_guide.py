import json
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, field_validator

from musecapsule.models import Hypothesis, ImageFragment, Intent, Message


class ExplorationQuestion(BaseModel):
    """One proposed question for continuing narrative exploration."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)

    @field_validator("question")
    @classmethod
    def reject_blank_question(cls, value: str) -> str:
        """Reject blank questions and trim surrounding whitespace."""
        if not value.strip():
            raise ValueError("Question must not be blank.")
        return value.strip()


def generate_exploration_question(
    intent: Intent,
    *,
    messages: list[Message],
    images: list[ImageFragment],
    hypotheses: list[Hypothesis],
    generate: Callable[[str], str],
) -> ExplorationQuestion:
    """Generate and parse a question using the current session context.

    Include the dialogue and hypothesis statuses without changing state.
    Semantic question quality requires separate evaluation.
    """
    context = json.dumps(
        {
            "intent": intent.model_dump(mode="json"),
            "messages": [
                message.model_dump(mode="json")
                for message in messages
            ],
            "images": [
                image.model_dump(mode="json")
                for image in images
            ],
            "hypotheses": [
                hypothesis.model_dump(mode="json")
                for hypothesis in hypotheses
            ],
        },
        ensure_ascii=False,
    )

    raw_response = generate(context)

    return ExplorationQuestion.model_validate_json(raw_response)
