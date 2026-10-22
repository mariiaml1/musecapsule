from musecapsule.models import EvidenceRef, Message


def validate_evidence(
        evidence: EvidenceRef,
        message: Message) -> None:

    if evidence.message_id != message.id:
        raise ValueError("Evidence references a different message.")

    if message.role != "user":
        raise ValueError("Evidence must reference a user message.")

    if evidence.quote not in message.text:
        raise ValueError("Evidence quote was not found in the message.")
