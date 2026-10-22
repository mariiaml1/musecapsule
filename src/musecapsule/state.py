from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from musecapsule.models import Intent, Message


class SessionState(BaseModel):
    id:UUID = Field(default_factory=uuid4)
    intent: Intent
    messages: list[Message] = Field(default_factory=list)
    revision: int = Field(default=0, ge=0)


def append_message(
    state: SessionState,
    message: Message,
) -> SessionState:
    message_exists = any(item.id == message.id for item in state.messages)
    
    if message_exists:
        raise ValueError('Message with this id already exists')

    return SessionState(
    id=state.id,
    intent=state.intent,
    messages=[*state.messages, message],
    revision=state.revision + 1,
)
