from uuid import uuid4

import pytest

from musecapsule.models import EvidenceRef, Hypothesis, ImageFragment, Intent, Message
from musecapsule.state import (
    SessionState,
    append_hypothesis,
    append_image_fragment,
    append_message,
    revise_hypothesis_status,
)

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


def test_append_hypothesis_preserves_previous_state():
    message_id = uuid4()

    evidence = EvidenceRef(
        message_id=message_id,
        quote="A golden note",
    )

    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
        messages=[
            Message(
                id=message_id,
                role="user",
                text="A golden note floats inside the capsule.",
            )
        ],
        images=[
            ImageFragment(
                label="Golden note",
                evidence=[evidence],
            )
        ],
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        evidence=[evidence],
        image_ids=[state.images[0].id],
    )
    updated = append_hypothesis(state, hypothesis)

    assert updated.id == state.id
    assert updated.intent == state.intent
    assert updated.hypotheses == [hypothesis]
    assert updated.revision == 1
    assert updated.messages == state.messages
    assert updated.images == state.images

    assert state.hypotheses == []
    assert state.revision == 0


def test_append_hypothesis_rejects_missing_image():
    message_id = uuid4()
    image_id = uuid4()

    evidence = EvidenceRef(
        message_id=message_id,
        quote="A golden note",
    )

    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
        messages=[
            Message(
                id=message_id,
                role="user",
                text="A golden note floats inside the capsule.",
            )
        ],
        images=[
            ImageFragment(
                label="Golden note",
                evidence=[evidence],
            )
        ],
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        evidence=[evidence],
        image_ids=[image_id],
    )
    with pytest.raises(ValueError, match="Hypothesis references a missing image."):
        append_hypothesis(state, hypothesis)


def test_append_hypothesis_rejects_invalid_evidence():
    message_id = uuid4()

    evidence = EvidenceRef(
        message_id=message_id,
        quote="A golden note",
    )

    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
        messages=[
            Message(
                id=message_id,
                role="user",
                text="A golden note floats inside the capsule.",
            )
        ],
        images=[
            ImageFragment(
                label="Golden note",
                evidence=[evidence],
            )
        ],
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        image_ids=[state.images[0].id],
        evidence=[
            EvidenceRef(
                message_id=message_id,
                quote="A silver key",
            ),
            evidence,
        ],
    )

    with pytest.raises(ValueError, match="Evidence quote was not found"):
        append_hypothesis(state, hypothesis)

    assert state.hypotheses == []
    assert state.revision == 0


def test_append_hypothesis_rejects_duplicate_id():
    message_id = uuid4()

    evidence = EvidenceRef(
        message_id=message_id,
        quote="A golden note",
    )

    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
        messages=[
            Message(
                id=message_id,
                role="user",
                text="A golden note floats inside the capsule.",
            )
        ],
        images=[
            ImageFragment(
                label="Golden note",
                evidence=[evidence],
            )
        ],
    )

    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        evidence=[evidence],
        image_ids=[state.images[0].id],
    )
    updated = append_hypothesis(state, hypothesis)

    with pytest.raises(ValueError, match="Hypothesis already exists."):
        append_hypothesis(updated, hypothesis)


@pytest.mark.parametrize(
    "status",
    ["supported", "unsupported", "superseded"],
)
def test_append_hypothesis_rejects_non_proposed_status(status):
    message_id = uuid4()

    evidence = EvidenceRef(
        message_id=message_id,
        quote="A golden note",
    )

    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
        messages=[
            Message(
                id=message_id,
                role="user",
                text="A golden note floats inside the capsule.",
            )
        ],
        images=[
            ImageFragment(
                label="Golden note",
                evidence=[evidence],
            )
        ],
    )

    hypothesis = Hypothesis(
        status=status,
        statement="The note may represent a selectable idea.",
        evidence=[evidence],
        image_ids=[state.images[0].id],
    )

    with pytest.raises(ValueError, match="Hypothesis status is not proposed."):
        append_hypothesis(state, hypothesis)


def test_revise_hypothesis_status_preserves_previous_version():
    message_id = uuid4()
    hypothesis_id = uuid4()

    evidence = EvidenceRef(
        message_id=message_id,
        quote="A golden note",
    )

    state = SessionState(
        intent=Intent(
            goal="Build an AI-agent portfolio project",
            constraints=["Local execution"],
        ),
        messages=[
            Message(
                id=message_id,
                role="user",
                text="A golden note floats inside the capsule.",
            )
        ],
        images=[
            ImageFragment(
                label="Golden note",
                evidence=[evidence],
            )
        ],
    )

    hypothesis = Hypothesis(
        id=hypothesis_id,
        statement="The note may represent a selectable idea.",
        evidence=[evidence],
        image_ids=[state.images[0].id],
    )
    updated = append_hypothesis(state, hypothesis)

    clarification = Message(
        role="user",
        text="The note cannot be selected; it only illuminates the capsule.",
    )

    before_revision = append_message(updated, clarification)

    new_evidence = EvidenceRef(
        message_id=clarification.id,
        quote="The note cannot be selected",
    )
    reason = "The user clarified that the note cannot be selected."

    after_revision = revise_hypothesis_status(
        state=before_revision,
        hypothesis_id=hypothesis_id,
        new_status="unsupported",
        evidence=[new_evidence],
        reason=reason,
    )
    current = after_revision.hypotheses[0]

    assert after_revision.id == before_revision.id
    assert after_revision.intent == before_revision.intent
    assert after_revision.messages == before_revision.messages
    assert after_revision.images == before_revision.images
    assert after_revision.revision == before_revision.revision + 1

    assert current.id == hypothesis.id
    assert current.statement == hypothesis.statement
    assert current.image_ids == hypothesis.image_ids
    assert current.status == "unsupported"
    assert current.evidence == [evidence, new_evidence]

    assert len(after_revision.hypothesis_history) == 1
    entry = after_revision.hypothesis_history[0]
    assert entry.previous == hypothesis
    assert entry.new_status == "unsupported"
    assert entry.reason == reason
    assert entry.evidence == [new_evidence]
    assert entry.session_revision == after_revision.revision

    assert before_revision.hypotheses[0].status == "proposed"
    assert before_revision.hypotheses[0].evidence == [evidence]
    assert before_revision.hypothesis_history == []


@pytest.mark.parametrize(
    ("quote", "reason", "expected_error"),
    [
        (
            "The capsule disappeared",
            "The user contradicted the interpretation.",
            "Evidence quote was not found",
        ),
        (
            "A golden note",
            "   ",
            None,
        ),
    ],
)
def test_revise_hypothesis_status_rejects_invalid_revision(
    quote,
    reason,
    expected_error,
):
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image = ImageFragment(
        label="Golden note",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        statement="The note may represent a selectable idea.",
        image_ids=[image.id],
        evidence=[source],
    )
    state = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
        messages=[message],
        images=[image],
        hypotheses=[hypothesis],
    )
    before = state.model_dump()

    with pytest.raises(ValueError, match=expected_error):
        revise_hypothesis_status(
            state=state,
            hypothesis_id=hypothesis.id,
            new_status="unsupported",
            reason=reason,
            evidence=[
                EvidenceRef(
                    message_id=message.id,
                    quote=quote,
                )
            ],
        )

    assert state.model_dump() == before


def test_revise_hypothesis_status_rejects_unchanged_status():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    source = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    image = ImageFragment(
        label="Golden note",
        evidence=[source],
    )
    hypothesis = Hypothesis(
        status="supported",
        statement="The note may represent a selectable idea.",
        image_ids=[image.id],
        evidence=[source],
    )
    state = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
        messages=[message],
        images=[image],
        hypotheses=[hypothesis],
    )

    with pytest.raises(ValueError, match="Status is invalid or unchanged."):
        revise_hypothesis_status(
            state=state,
            hypothesis_id=hypothesis.id,
            new_status="supported",
            reason="The user contradicted the interpretation.",
            evidence=[
                EvidenceRef(
                    message_id=message.id,
                    quote="A golden note",
                )
            ],
        )
