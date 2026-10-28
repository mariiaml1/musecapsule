import os
from collections.abc import Callable
from pathlib import Path

from fastapi import FastAPI

from musecapsule.api import create_app
from musecapsule.llm import request_generation
from musecapsule.models import Message
from musecapsule.state import SessionState
from musecapsule.workflow import build_exploration_graph


def create_local_app() -> FastAPI:
    """Configure the local API with the real exploration workflow."""
    configured_dir = os.environ.get("MUSECAPSULE_DEVKIT_DIR")
    if not configured_dir or not configured_dir.strip():
        raise RuntimeError("MUSECAPSULE_DEVKIT_DIR must be configured.")

    devkit_dir = Path(configured_dir).expanduser().resolve()
    if not devkit_dir.is_dir():
        raise RuntimeError("The configured DevKit directory does not exist.")

    model = os.environ.get("MUSECAPSULE_MODEL", "gpt-6.1-sol")
    database_path = Path(
        os.environ.get("MUSECAPSULE_DATABASE", "data/musecapsule.db")
    )
    prompts_dir = Path(__file__).resolve().parent / "prompts"

    def create_generator(prompt_name: str) -> Callable[[str], str]:
        """Bind task instructions to the configured local connection."""
        instructions = (prompts_dir / prompt_name).read_text(
            encoding="utf-8",
        )

        def generate(text: str) -> str:
            return request_generation(
                text=text,
                devkit_dir=devkit_dir,
                instructions=instructions,
                model=model,
            )

        return generate

    graph = build_exploration_graph(
        generate_images=create_generator("metaphor_explorer.md"),
        generate_hypotheses=create_generator("hypothesis_proposals.md"),
        generate_revisions=create_generator("hypothesis_revisions.md"),
        generate_question=create_generator("imagination_guide.md"),
        generate_ideas=create_generator("idea_evolution.md"),
        generate_architecture=create_generator("idea_architect.md"),
    )

    def process_message(
        session: SessionState,
        message: Message,
    ) -> SessionState:
        """Process one user turn through the compiled graph."""
        result = graph.invoke(
            {
                "session": session,
                "command": "explore",
                "incoming_message": message,
            }
        )
        return result["session"]

    return create_app(
        database_path,
        process_message=process_message,
    )
