import argparse
from collections.abc import Callable
import logging
from pathlib import Path
import sqlite3
import sys
from uuid import UUID

from pydantic import ValidationError

from musecapsule.llm import request_generation
from musecapsule.models import Intent, Message
from musecapsule.state import SessionState
from musecapsule.storage import SessionStore
from musecapsule.workflow import build_exploration_graph


def main() -> None:
    """Run an initial exploration through the compiled workflow."""

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )

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
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/musecapsule.db"),
        help="Path to the local session database.",
    )
    parser.add_argument(
        "--session-id",
        type=UUID,
        help="Restore an existing session instead of starting the demo.",
    )
    parser.add_argument(
        "--message",
        help="Continue the restored session with a new narrative message.",
    )
    parser.add_argument(
        "--goal",
        help="Start a session with an explicit user goal.",
    )
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        help="A user constraint. Repeat this option for multiple constraints.",
    )
    parser.add_argument(
        "--generate-ideas",
        action="store_true",
        help="Generate ideas for a restored session instead of exploring.",
    )
    parser.add_argument(
        "--select-idea",
        type=UUID,
        help="Select an existing idea in a restored session.",
    )
    parser.add_argument(
        "--build-blueprint",
        action="store_true",
        help="Generate a blueprint for the selected idea.",
    )
    args = parser.parse_args()

    if args.generate_ideas:
        action_count = sum(
            (
                args.message is not None,
                args.generate_ideas,
                args.select_idea is not None,
                args.build_blueprint,
            )
        )

        if action_count > 1:
            parser.error("Choose only one action per invocation.")

        if action_count and args.session_id is None:
            parser.error("Session actions require --session-id.")

        if args.message is not None:
            parser.error("--generate-ideas cannot be combined with --message.")

    if args.goal is not None:
        if args.session_id is not None:
            parser.error("--goal cannot be combined with --session-id.")

        if not args.goal.strip():
            parser.error("--goal must not be blank.")

    if args.constraint and args.goal is None:
        parser.error("--constraint requires --goal.")

    if any(not value.strip() for value in args.constraint):
        parser.error("--constraint must not be blank.")

    if args.message is not None:
        if args.session_id is None:
            parser.error("--message requires --session-id.")

        if not args.message.strip():
            parser.error("--message must not be blank.")

    store = SessionStore(args.database)

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

    graph = build_exploration_graph(
        generate_revisions=create_generator("hypothesis_revisions.md"),
        generate_images=create_generator("metaphor_explorer.md"),
        generate_hypotheses=create_generator("hypothesis_proposals.md"),
        generate_question=create_generator("imagination_guide.md"),
        generate_ideas=create_generator("idea_evolution.md"),
        generate_architecture=create_generator("idea_architect.md"),
    )

    if args.session_id is not None:
        restored = store.load(args.session_id)

        if restored is None:
            parser.error("Session was not found in the selected database.")

        if args.message is not None:
            result = graph.invoke(
                {
                    "session": restored,
                    "command": "explore",
                    "incoming_message": Message(
                        role="user",
                        text=args.message,
                    ),
                }
            )
            restored = result["session"]
            store.save(restored)

        if args.generate_ideas:
            result = graph.invoke(
                {
                    "session": restored,
                    "command": "generate_ideas",
                }
            )
            updated = result["session"]
            store.save(updated)

            new_ideas = updated.ideas[len(restored.ideas) :]
            restored = updated

            print("\nGenerated ideas:")
            for idea in new_ideas:
                print(f"\n{idea.title}")
                print(f"ID: {idea.id}")
                print(idea.description)

        if args.select_idea is not None:
            result = graph.invoke(
                {
                    "session": restored,
                    "command": "select_idea",
                    "idea_id": args.select_idea,
                }
            )
            updated = result["session"]

            if updated.revision != restored.revision:
                store.save(updated)

            restored = updated

        if args.build_blueprint:
            result = graph.invoke(
                {
                    "session": restored,
                    "command": "build_blueprint",
                }
            )
            restored = result["session"]
            store.save(restored)

        print(restored.model_dump_json(indent=2))
        return

    if args.goal is not None:
        narrative = input("Describe your imagined scene: ")

        if not narrative.strip():
            parser.error("The narrative must not be blank.")

        session = SessionState(
            intent=Intent(
                goal=args.goal,
                constraints=args.constraint,
            ),
        )
        store.save(session)
        print(f"Session ID: {session.id}", flush=True)

        result = graph.invoke(
            {
                "session": session,
                "command": "explore",
                "incoming_message": Message(
                    role="user",
                    text=narrative,
                ),
            }
        )
        updated_session = result["session"]
        store.save(updated_session)

        print(f"\n{updated_session.messages[-1].text}")
        print(f"Saved revision: {updated_session.revision}")
        return

    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development", "Local execution"],
        ),
    )

    store.save(session)
    print(f"Session ID: {session.id}", flush=True)

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
    store.save(updated_session)

    clarification = Message(
        role="user",
        text=(
            "The capsule is opaque, not transparent. "
            "Nobody can see the note or anything happening inside."
        ),
    )

    continuation = graph.invoke(
        {
            "session": updated_session,
            "incoming_message": clarification,
        }
    )
    updated_session = continuation["session"]
    store.save(updated_session)

    idea_result = graph.invoke(
        {
            "session": updated_session,
            "command": "generate_ideas",
        }
    )
    updated_session = idea_result["session"]
    store.save(updated_session)

    print("\nGenerated ideas:")
    for index, idea in enumerate(updated_session.ideas, start=1):
        print(f"\n{index}. {idea.title}")
        print(idea.description)

    while True:
        try:
            choice = int(input("\nChoose an idea number: "))
        except ValueError:
            print("Enter a whole number.")
            continue

        if 1 <= choice <= len(updated_session.ideas):
            break

        print(f"Enter a number from 1 to {len(updated_session.ideas)}.")

    chosen_idea = updated_session.ideas[choice - 1]

    selection_result = graph.invoke(
        {
            "session": updated_session,
            "command": "select_idea",
            "idea_id": chosen_idea.id,
        }
    )
    updated_session = selection_result["session"]
    store.save(updated_session)

    blueprint_result = graph.invoke(
        {
            "session": updated_session,
            "command": "build_blueprint",
        }
    )

    updated_session = blueprint_result["session"]
    store.save(updated_session)

    print(updated_session.model_dump_json(indent=2))


def cli() -> int:
    """Run the CLI and translate expected failures into concise messages."""
    try:
        main()
    except ValidationError:
        print(
            "Error: Generated or stored data failed validation. "
            "Previously saved snapshots remain available.",
            file=sys.stderr,
        )
        return 1
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    except RuntimeError:
        print(
            "Error: Generation could not be completed. "
            "Check the local ChatGPT connection and try again.",
            file=sys.stderr,
        )
        return 1
    except (sqlite3.Error, OSError):
        print(
            "Error: A local file or database operation failed. "
            "Check paths, permissions, and available disk space.",
            file=sys.stderr,
        )
        return 1
    except EOFError:
        print("Error: Input ended before the action was completed.", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled.", file=sys.stderr)
        return 130

    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
