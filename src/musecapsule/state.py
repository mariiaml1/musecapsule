from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from musecapsule.evidence import validate_evidence
from musecapsule.models import (
    EvidenceRef,
    Hypothesis,
    HypothesisRevision,
    ImageFragment,
    Intent,
    Message,
    ProductIdea,
)


class SessionState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    intent: Intent
    messages: list[Message] = Field(default_factory=list)
    revision: int = Field(default=0, ge=0)
    images: list[ImageFragment] = Field(default_factory=list)
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    hypothesis_history: list[HypothesisRevision] = Field(default_factory=list)
    ideas: list[ProductIdea] = Field(default_factory=list)
    selected_idea_id: UUID | None = None


def append_message(
    state: SessionState,
    message: Message,
) -> SessionState:
    """Return a new session state with the message appended.
    Preserve the input state and increment the revision.
    Raises:
        ValueError: If a message with the same ID already exists.
    """

    message_exists = any(item.id == message.id for item in state.messages)

    if message_exists:
        raise ValueError("Message with this id already exists")

    return SessionState(
        id=state.id,
        intent=state.intent,
        images=state.images,
        hypotheses=state.hypotheses,
        hypothesis_history=state.hypothesis_history,
        ideas=state.ideas,
        selected_idea_id=state.selected_idea_id,
        messages=[*state.messages, message],
        revision=state.revision + 1,
    )


def append_image_fragment(
    state: SessionState,
    fragment: ImageFragment,
) -> SessionState:
    """Return a new session state with a grounded image fragment appended.

    Validate every evidence reference against existing user messages.
    Preserve the input state and increment the revision.

    Raises:
        ValueError: If the fragment ID already exists, a source message
            is missing, or an evidence reference is invalid.
    """

    fragment_exists = any(item.id == fragment.id for item in state.images)
    if fragment_exists:
        raise ValueError("Image fragment already exists.")

    messages_by_id = {message.id: message for message in state.messages}

    for evidence_item in fragment.evidence:
        message = messages_by_id.get(evidence_item.message_id)

        if message is None:
            raise ValueError("Evidence references a missing message.")

        validate_evidence(evidence_item, message)

    return SessionState(
        id=state.id,
        intent=state.intent,
        messages=state.messages,
        hypotheses=state.hypotheses,
        ideas=state.ideas,
        selected_idea_id=state.selected_idea_id,
        hypothesis_history=state.hypothesis_history,
        images=[*state.images, fragment],
        revision=state.revision + 1,
    )


def append_hypothesis(
    state: SessionState,
    hypothesis: Hypothesis,
) -> SessionState:
    """Append a proposed hypothesis after validating its source references.

    Preserve the input state and increment the revision.

    Raises:
        ValueError: If the ID already exists, the status is not proposed,
            a referenced image or message is missing, or evidence is invalid.
    """

    if hypothesis.status != "proposed":
        raise ValueError("Hypothesis status is not proposed.")

    exists = any(item.id == hypothesis.id for item in state.hypotheses)
    if exists:
        raise ValueError("Hypothesis already exists.")

    existing_image_ids = {image.id for image in state.images}

    for image_id in hypothesis.image_ids:
        if image_id not in existing_image_ids:
            raise ValueError("Hypothesis references a missing image.")

    messages_by_id = {message.id: message for message in state.messages}

    for evidence_item in hypothesis.evidence:
        message = messages_by_id.get(evidence_item.message_id)

        if message is None:
            raise ValueError("Evidence references a missing message.")

        validate_evidence(evidence_item, message)

    return SessionState(
        id=state.id,
        intent=state.intent,
        messages=state.messages,
        ideas=state.ideas,
        selected_idea_id=state.selected_idea_id,
        hypothesis_history=state.hypothesis_history,
        hypotheses=[*state.hypotheses, hypothesis],
        images=state.images,
        revision=state.revision + 1,
    )


def revise_hypothesis_status(
    state: SessionState,
    hypothesis_id: UUID,
    *,
    new_status: Literal["supported", "unsupported"],
    reason: str,
    evidence: list[EvidenceRef],
) -> SessionState:
    """Change a hypothesis status and record its previous version.

    Preserve the input state and validate all new evidence.

    Raises:
        ValueError: If the hypothesis is missing or superseded, the target
            status is invalid or unchanged, or revision data is invalid.
    """
    hypothesis = next(
        (item for item in state.hypotheses if item.id == hypothesis_id), None
    )
    if hypothesis is None:
        raise ValueError("Hypothesis is missing.")

    if new_status not in ("supported", "unsupported"):
        raise ValueError("Target status must be supported or unsupported.")

    if hypothesis.status == new_status or hypothesis.status == "superseded":
        raise ValueError("Status is invalid or unchanged.")

    messages_by_id = {message.id: message for message in state.messages}

    for evidence_item in evidence:
        message = messages_by_id.get(evidence_item.message_id)

        if message is None:
            raise ValueError("Evidence references a missing message.")

        validate_evidence(evidence_item, message)

    revision_entry = HypothesisRevision(
        previous=hypothesis.model_copy(deep=True),
        new_status=new_status,
        reason=reason,
        evidence=evidence,
        session_revision=state.revision + 1,
    )

    updated_hypothesis = Hypothesis(
        id=hypothesis.id,
        statement=hypothesis.statement,
        status=new_status,
        image_ids=hypothesis.image_ids,
        evidence=[*hypothesis.evidence, *evidence],
    )

    updated_hypotheses = [
        updated_hypothesis if item.id == hypothesis_id else item
        for item in state.hypotheses
    ]

    return SessionState(
        id=state.id,
        intent=state.intent,
        messages=state.messages,
        ideas=state.ideas,
        selected_idea_id=state.selected_idea_id,
        hypothesis_history=[*state.hypothesis_history, revision_entry],
        hypotheses=updated_hypotheses,
        images=state.images,
        revision=state.revision + 1,
    )


def append_product_ideas(
    state: SessionState,
    ideas: list[ProductIdea],
) -> SessionState:
    """Append a complete idea batch after validating all source references.

    Preserve existing ideas and increment the session revision once.

    Raises:
        ValueError: If the batch size, IDs or source references are invalid.
    """
    if not 2 <= len(ideas) <= 3:
        raise ValueError("An idea batch must contain two or three ideas.")

    seen_ids = {idea.id for idea in state.ideas}
    existing_image_ids = {image.id for image in state.images}
    hypotheses_by_id = {hypothesis.id: hypothesis for hypothesis in state.hypotheses}

    for idea in ideas:
        if idea.id in seen_ids:
            raise ValueError("Product idea already exists.")

        seen_ids.add(idea.id)

        for image_id in idea.image_ids:
            if image_id not in existing_image_ids:
                raise ValueError("Idea references a missing image.")

        for hypothesis_id in idea.hypothesis_ids:
            hypothesis = hypotheses_by_id.get(hypothesis_id)

            if hypothesis is None:
                raise ValueError("Idea references a missing hypothesis.")

            if hypothesis.status not in ("proposed", "supported"):
                raise ValueError("Idea references an inactive hypothesis.")

    return SessionState(
        id=state.id,
        intent=state.intent,
        messages=state.messages,
        images=state.images,
        hypotheses=state.hypotheses,
        selected_idea_id=state.selected_idea_id,
        hypothesis_history=state.hypothesis_history,
        ideas=[*state.ideas, *ideas],
        revision=state.revision + 1,
    )


def select_product_idea(
    state: SessionState,
    idea_id: UUID,
) -> SessionState:
    """Select an existing product idea without changing its contents.

    Preserve the input state. Selecting the current idea is a no-op.

    Raises:
        ValueError: If the idea does not exist in the session.
    """
    if not any(idea.id == idea_id for idea in state.ideas):
        raise ValueError("Selected idea does not exist.")

    if state.selected_idea_id == idea_id:
        return state

    return SessionState(
        id=state.id,
        intent=state.intent,
        messages=state.messages,
        images=state.images,
        hypotheses=state.hypotheses,
        hypothesis_history=state.hypothesis_history,
        ideas=state.ideas,
        selected_idea_id=idea_id,
        revision=state.revision + 1,
    )
