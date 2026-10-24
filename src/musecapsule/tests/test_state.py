import pytest

from musecapsule.models import EvidenceRef, ImageFragment, Intent, Message
from musecapsule.state import SessionState, append_image_fragment, append_message


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


def test_append_image_fragment_rejects_invalid_evidence():
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    state = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
        messages=[message],
    )
    fragment = ImageFragment(
        label="Golden note",
        evidence=[
            EvidenceRef(
                message_id=message.id,
                quote="A golden note",
            ),
            EvidenceRef(
                message_id=message.id,
                quote="A silver key",
            ),
        ],
    )

    with pytest.raises(ValueError, match="Evidence quote was not found"):
        append_image_fragment(state, fragment)

    assert state.images == []
    assert state.revision == 0
    assert state.messages == [message]


def test_append_image_fragment_rejects_missing_message():
    message1 = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    message2 = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    state = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
        messages=[message1],
    )
    fragment = ImageFragment(
        label="Golden note",
        evidence=[
            EvidenceRef(
                message_id=message1.id,
                quote="A golden note",
            ),
            EvidenceRef(
                message_id=message2.id,
                quote="A golden note",
            ),
        ],
    )
    with pytest.raises(ValueError, match="Evidence references a missing message."):
        append_image_fragment(state, fragment)


def test_append_image_fragment_rejects_duplicate_id():
    message = Message(
        role="user",
        text="A golden note floats inside a capsule.",
    )
    state = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
        messages=[message],
    )
    fragment = ImageFragment(
        label="Golden note",
        evidence=[
            EvidenceRef(
                message_id=message.id,
                quote="A golden note",
            )
        ],
    )

    updated = append_image_fragment(state, fragment)

    with pytest.raises(ValueError, match="Image fragment already exists."):
        append_image_fragment(updated, fragment)
