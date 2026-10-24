import argparse
from pathlib import Path

from musecapsule.agents.metaphor_explorer import parse_image_extraction
from musecapsule.llm import request_image_extraction
from musecapsule.models import Intent, Message
from musecapsule.state import (
    SessionState,
    append_image_fragment,
    append_message,
)


def main() -> None:
    """Extract images through ChatGPT and add validated results to a demo session."""

    parser = argparse.ArgumentParser(
        description="Extract grounded images through a local ChatGPT connection.",
    )
    parser.add_argument(
        "--devkit-dir",
        type=Path,
        required=True,
        help="Path to the built Sign in with ChatGPT DevKit checkout.",
    )
    args = parser.parse_args()

    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )
    state = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
    )
    state = append_message(state, message)

    raw_response = request_image_extraction(
        text=message.text,
        devkit_dir=args.devkit_dir,
    )

    fragments = parse_image_extraction(raw_response, message)

    for fragment in fragments:
        state = append_image_fragment(state, fragment)

    print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
