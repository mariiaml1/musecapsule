import argparse
from collections.abc import Callable
from pathlib import Path

from musecapsule.llm import request_generation
from musecapsule.models import Intent, Message
from musecapsule.state import SessionState
from musecapsule.workflow import build_initial_exploration_graph

def main() -> None:
    """Run an initial exploration through the compiled workflow."""

    parser = argparse.ArgumentParser(
        description="Explore a narrative through the MuseCapsule workflow.",
    )
    parser.add_argument(
        "--devkit-dir",
        type=Path,
        required=True,
        help="Path to the built Sign in with ChatGPT DevKit checkout.",
    )
    parser.add_argument(
        "--model",
        default="gpt-6.1-sol",
        help="Model slug available to the connected ChatGPT account.",
    )
    args = parser.parse_args()

    prompts_dir = Path(__file__).resolve().parent / "prompts"

    def create_generator(prompt_name: str) -> Callable[[str], str]:
        """Bind prompt instructions and connection settings to generation."""
        instructions = (prompts_dir / prompt_name).read_text(
            encoding="utf-8",
        )

        def generate(text: str) -> str:
            return request_generation(
                text=text,
                devkit_dir=args.devkit_dir,
                instructions=instructions,
                model=args.model,
            )

        return generate

    graph = build_initial_exploration_graph(
        generate_images=create_generator("metaphor_explorer.md"),
        generate_hypotheses=create_generator("hypothesis_proposals.md"),
        generate_question=create_generator("imagination_guide.md"),
    )

    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
    )
    message = Message(
        role="user",
        text="A golden note floats inside a transparent capsule.",
    )

    result = graph.invoke(
        {
            "session": session,
            "incoming_message": message,
        }
    )
    updated_session = result["session"]

    print(updated_session.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
