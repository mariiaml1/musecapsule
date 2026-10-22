from uuid import uuid4

import pytest
from pydantic import ValidationError

from musecapsule.models import EvidenceRef, Intent, Message
from src.musecapsule.evidence import validate_evidence


def test_intent_rejects_non_string_constrain():
    with pytest.raises(ValidationError):
        Intent(
            goal='Build an AI-agent portfolio project',
            constraints=[123],
        )

@pytest.mark.parametrize("goal", ["", " ", "\t\n"])
def test_intent_rejects_blank_goal(goal: str):
    with pytest.raises(ValidationError):
        Intent(goal=goal)

def test_message_preserves_original_text():
    original = "  A glowing capsule.\n"

    message = Message(role="user", text=original)

    assert message.text == original


def test_message_rejects_empty_text():
    with pytest.raises(ValidationError):
        Message(role="user", text="")

@pytest.mark.parametrize("text", [" ", "\t", "\n", " \t\n "])
def test_message_rejects_whitespace_only_text(text: str):
    with pytest.raises(ValidationError):
        Message(role="user", text=text)

def test_evidence_accepts_exact_user_quote():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )

    validate_evidence(evidence, message)

def test_evidence_rejects_wrong_user_quote():
    message = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A silver key",
    )
    
    with pytest.raises(ValueError):
     validate_evidence(evidence, message)

def test_evidence_rejects_blank_quote():
    with pytest.raises(ValidationError):
        EvidenceRef(message_id=uuid4(), quote="   ")

def test_evidence_rejects_different_message_id():
    message1 = Message(
        role="user",
        text="A golden note floats inside the capsule.",
    )
    message2 = Message(
            role="user",
            text="A golden note floats inside the capsule.",
        )
    evidence = EvidenceRef(
        message_id=message1.id,
        quote="A golden note",
    )
    
    with pytest.raises(ValueError):
     validate_evidence(evidence, message2)

def test_evidence_rejects_not_user_message():
    message = Message(
        role="assistant",
        text="A golden note floats inside the capsule.",
    )
    evidence = EvidenceRef(
        message_id=message.id,
        quote="A golden note",
    )
    
    with pytest.raises(ValueError):
     validate_evidence(evidence, message)
