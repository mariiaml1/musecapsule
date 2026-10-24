import pytest

from musecapsule.agents.metaphor_explorer import parse_image_extraction
from musecapsule.models import Message


def test_parse_image_extraction_returns_grounded_images():
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    raw_response = """
    {
        "images": [
            {"label": "Golden note", "quote": "A golden note"},
            {"label": "Transparent capsule", "quote": "a transparent capsule"}
        ]
    }
    """

    result = parse_image_extraction(raw_response, message)

    assert len(result) == 2
    assert result[0].id != result[1].id

    expected = [
        ("Golden note", "A golden note"),
        ("Transparent capsule", "a transparent capsule"),
    ]

    for fragment, (label, quote) in zip(result, expected, strict=True):
        assert fragment.label == label
        assert len(fragment.evidence) == 1
        assert fragment.evidence[0].message_id == message.id
        assert fragment.evidence[0].quote == quote


def test_parse_image_extraction_rejects_fabricated_quote():
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    raw_response = """
       {
           "images": [
               {"label": "Golden note", "quote": "some"}
           ]
       }
       """

    with pytest.raises(
        ValueError, match="Evidence quote was not found in the message."
    ):
        parse_image_extraction(raw_response, message)


def test_parse_image_extraction_accepts_empty_images():
    message = Message(
        role="user",
        text="Please continue.",
    )

    result = parse_image_extraction('{"images": []}', message)

    assert result == []
