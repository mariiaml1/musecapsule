from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from musecapsule.evidence import validate_evidence
from musecapsule.models import ImageFragment, Intent, Message


class SessionState(BaseModel):
    id:UUID = Field(default_factory=uuid4)
    intent: Intent
    messages: list[Message] = Field(default_factory=list)
    revision: int = Field(default=0, ge=0)
    images: list[ImageFragment] = Field(default_factory=list)

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
        images=[*state.images, fragment],
        revision=state.revision + 1,
    )
