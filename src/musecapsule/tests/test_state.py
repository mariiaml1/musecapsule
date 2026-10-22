import pytest

from musecapsule.models import Intent, Message
from musecapsule.state import SessionState, append_message


def test_append_message_preserves_previous_state():
    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
    )
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )

    updated = append_message(state, message)

    assert updated.id == state.id
    assert updated.intent == state.intent
    assert updated.messages == [message]
    assert updated.revision == 1

    assert state.messages == []
    assert state.revision == 0

def test_append_rejects_the_same_message():
    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
    )
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    
    updated = append_message(state, message)

    with pytest.raises(ValueError):
     append_message(updated, message)
