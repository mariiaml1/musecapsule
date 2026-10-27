import argparse
from pathlib import Path

from musecapsule.agents.imagination_guide import generate_exploration_question
from musecapsule.agents.metaphor_explorer import (
    parse_image_extraction,
    propose_hypotheses,
    propose_hypothesis_revisions,
)
from musecapsule.llm import request_generation
from musecapsule.models import Intent, Message
from musecapsule.state import (
    SessionState,
    append_hypothesis,
    append_image_fragment,
    append_message,
    revise_hypothesis_status,
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
    parser.add_argument(
        "--model",
        default="gpt-6.1-sol",
        help="Model slug available to the connected ChatGPT account.",
    ),
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

    prompt_path = Path(__file__).resolve().parent / "prompts" / "metaphor_explorer.md"
    instructions = prompt_path.read_text(encoding="utf-8")

    raw_response = request_generation(
        text=message.text,
        devkit_dir=args.devkit_dir,
        instructions=instructions,
        model=args.model,
    )

    fragments = parse_image_extraction(raw_response, message)

    for fragment in fragments:
        state = append_image_fragment(state, fragment)

    hypothesis_prompt_path = (
        Path(__file__).resolve().parent / "prompts" / "hypothesis_proposals.md"
    )

    hypothesis_instructions = hypothesis_prompt_path.read_text(
        encoding="utf-8",
    )

    def generate_hypotheses(context: str) -> str:
        """Send hypothesis context through the configured local bridge."""
        return request_generation(
            text=context,
            devkit_dir=args.devkit_dir,
            instructions=hypothesis_instructions,
            model=args.model,
        )

    hypotheses = propose_hypotheses(
        state.intent,
        images=state.images,
        messages=state.messages,
        generate=generate_hypotheses,
    )

    for hypothesis in hypotheses:
        state = append_hypothesis(state, hypothesis)

    clarification = Message(
        role="user",
        text=(
            "The capsule is opaque, not transparent. "
            "Nobody can see the note or anything happening inside."
        ),
    )
    state = append_message(state, clarification)

    revision_prompt_path = (
        Path(__file__).resolve().parent / "prompts" / "hypothesis_revisions.md"
    )
    revision_instructions = revision_prompt_path.read_text(
        encoding="utf-8",
    )

    def generate_revisions(context: str) -> str:
        """Request hypothesis revisions through the configured bridge."""
        return request_generation(
            text=context,
            devkit_dir=args.devkit_dir,
            instructions=revision_instructions,
            model=args.model,
        )

    revisions = propose_hypothesis_revisions(
        state.intent,
        hypotheses=state.hypotheses,
        messages=state.messages,
        clarification=clarification,
        generate=generate_revisions,
    )

    for proposal in revisions:
        state = revise_hypothesis_status(
            state,
            proposal.hypothesis_id,
            new_status=proposal.new_status,
            reason=proposal.reason,
            evidence=proposal.evidence,
        )

    guide_prompt_path = (
        Path(__file__).resolve().parent / "prompts" / "imagination_guide.md"
    )
    guide_instructions = guide_prompt_path.read_text(encoding="utf-8")

    def generate_question(context: str) -> str:
        """Request an exploration question through the configured bridge."""
        return request_generation(
            text=context,
            devkit_dir=args.devkit_dir,
            instructions=guide_instructions,
            model=args.model,
        )

    question = generate_exploration_question(
        state.intent,
        messages=state.messages,
        images=state.images,
        hypotheses=state.hypotheses,
        generate=generate_question,
    )

    state = append_message(
        state,
        Message(
            role="assistant",
            text=question.question,
        ),
    )

    print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
