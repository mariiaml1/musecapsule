from uuid import uuid4

import pytest

from musecapsule.models import Intent, Message
from musecapsule.state import SessionState, append_message
from musecapsule.storage import SessionStore


def test_session_store_restores_state_after_reopening(tmp_path):
    database_path = tmp_path / "sessions.db"
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development"],
        ),
    )
    session = append_message(
        session,
        Message(
            role="user",
            text="A golden note floats inside a capsule.",
        ),
    )

    SessionStore(database_path).save(session)

    reopened_store = SessionStore(database_path)
    restored = reopened_store.load(session.id)

    assert restored is not None
    assert restored == session
    assert restored is not session
    assert restored.messages[0].id == session.messages[0].id

def test_session_store_loads_latest_revision(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
    initial = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
    )
    updated = append_message(
        initial,
        Message(
            role="user",
            text="A golden note floats inside a capsule.",
        ),
    )

    # Save out of order to verify selection by revision, not insertion order.
    store.save(updated)
    store.save(initial)

    assert store.load(initial.id) == updated


def test_session_store_returns_none_for_unknown_session(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")

    assert store.load(uuid4()) is None


def test_session_store_rejects_overwriting_existing_revision(tmp_path):
    store = SessionStore(tmp_path / "sessions.db")
    session = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
    )
    store.save(session)

    conflicting = session.model_copy(deep=True)
    conflicting.intent.goal = "A different goal"

    with pytest.raises(
        ValueError,
        match="Session revision is already stored.",
    ):
        store.save(conflicting)

    assert store.load(session.id) == session
