from collections.abc import Callable
from typing import Literal, NotRequired, TypedDict
from uuid import UUID

from langgraph.graph import END, START, StateGraph

from musecapsule.agents.idea_architect import generate_blueprint
from musecapsule.agents.idea_evolution import generate_product_ideas
from musecapsule.agents.imagination_guide import generate_exploration_question
from musecapsule.agents.metaphor_explorer import (
    extract_images,
    propose_hypotheses,
    propose_hypothesis_revisions,
)
from musecapsule.models import Message
from musecapsule.state import (
    SessionState,
    append_blueprint,
    append_hypothesis,
    append_image_fragment,
    append_message,
    append_product_ideas,
    revise_hypothesis_status,
    select_product_idea,
)
from langgraph.config import get_stream_writer

class ExplorationState(TypedDict):
    """Workflow input and session data for an exploration command."""

    session: SessionState
    command: NotRequired[
        Literal[
            "explore",
            "generate_ideas",
            "select_idea",
            "build_blueprint",
        ]
    ]
    idea_id: NotRequired[UUID]
    incoming_message: NotRequired[Message]


def with_start_event(
    node_name: str,
    operation: Callable[[ExplorationState], dict],
):
    """Emit a public start event before executing a graph node."""

    def run(state: ExplorationState) -> dict:
        writer = get_stream_writer()
        writer(
            {
                "event": "node_started",
                "node": node_name,
            }
        )
        return operation(state)

    return run


def build_exploration_graph(
    *,
    generate_images: Callable[[str], str],
    generate_hypotheses: Callable[[str], str],
    generate_revisions: Callable[[str], str],
    generate_question: Callable[[str], str],
    generate_ideas: Callable[[str], str],
    generate_architecture: Callable[[str], str],
):
    """Compile an exploration workflow for one user message."""

    def select_idea(state: ExplorationState) -> dict:
        """Apply the user's explicit idea selection without generation."""
        idea_id = state.get("idea_id")
        if idea_id is None:
            raise ValueError("Idea selection requires an idea ID.")

        return {
            "session": select_product_idea(state["session"], idea_id),
        }

    def explore_images(state: ExplorationState) -> dict:
        """Validate extraction before adding the message and its images."""

        message = state.get("incoming_message")
        if message is None:
            raise ValueError("Exploration requires an incoming message.")

        fragments = extract_images(message, generate=generate_images)

        session = append_message(state["session"], message)
        for fragment in fragments:
            session = append_image_fragment(session, fragment)

        return {"session": session}

    def explore_hypotheses(state: ExplorationState) -> dict:
        """Generate and append grounded hypothesis proposals."""
        session = state["session"]
        hypotheses = propose_hypotheses(
            session.intent,
            images=session.images,
            messages=session.messages,
            generate=generate_hypotheses,
        )

        for hypothesis in hypotheses:
            session = append_hypothesis(session, hypothesis)

        return {"session": session}

    def ask_question(state: ExplorationState) -> dict:
        """Generate and store one exploration question."""
        session = state["session"]
        question = generate_exploration_question(
            session.intent,
            messages=session.messages,
            images=session.images,
            hypotheses=session.hypotheses,
            generate=generate_question,
        )
        session = append_message(
            session,
            Message(role="assistant", text=question.question),
        )

        return {"session": session}

    def route_after_images(
        state: ExplorationState,
    ) -> Literal["explore_hypotheses", "revise_hypotheses", "ask_question"]:
        """Choose a route from the existing hypothesis state."""
        hypotheses = state["session"].hypotheses

        if not hypotheses:
            return "explore_hypotheses"

        if any(item.status != "superseded" for item in hypotheses):
            return "revise_hypotheses"

        return "ask_question"

    def revise_hypotheses(state: ExplorationState) -> dict:
        """Apply validated status revisions grounded in the new message."""

        message = state.get("incoming_message")
        if message is None:
            raise ValueError("Exploration requires an incoming message.")

        session = state["session"]
        proposals = propose_hypothesis_revisions(
            session.intent,
            hypotheses=session.hypotheses,
            messages=session.messages,
            clarification=message,
            generate=generate_revisions,
        )

        for proposal in proposals:
            session = revise_hypothesis_status(
                session,
                proposal.hypothesis_id,
                new_status=proposal.new_status,
                reason=proposal.reason,
                evidence=proposal.evidence,
            )

        return {"session": session}

    def route_command(
        state: ExplorationState,
    ) -> Literal["explore_images", "create_ideas", "select_idea", "build_blueprint"]:
        """Route an explicit command and validate its required input."""
        command = state.get("command", "explore")

        if command == "build_blueprint":
            return "build_blueprint"

        if command == "generate_ideas":
            if not state["session"].images:
                raise ValueError("At least one image is required to generate ideas.")
            return "create_ideas"

        if command == "select_idea":
            if state.get("idea_id") is None:
                raise ValueError("Idea selection requires an idea ID.")

            return "select_idea"

        if command == "explore":
            message = state.get("incoming_message")
            if message is None:
                raise ValueError("Exploration requires an incoming message.")

            if message.role != "user":
                raise ValueError("Message is not from the user.")

            return "explore_images"

        raise ValueError("Unknown exploration command.")

    def create_ideas(state: ExplorationState) -> dict:
        """Generate and store a validated batch of product ideas."""

        session = state["session"]

        generated = generate_product_ideas(
            session.intent,
            messages=session.messages,
            images=session.images,
            hypotheses=session.hypotheses,
            generate=generate_ideas,
        )

        for hypothesis in generated.new_hypotheses:
            session = append_hypothesis(session, hypothesis)

        session = append_product_ideas(session, generated.ideas)

        return {"session": session}

    def build_blueprint(state: ExplorationState) -> dict:
        """Build and save a blueprint for the explicitly selected idea."""
        session = state["session"]

        if session.selected_idea_id is None:
            raise ValueError("An idea must be selected before building a blueprint.")

        idea = next(
            (item for item in session.ideas if item.id == session.selected_idea_id),
            None,
        )
        if idea is None:
            raise ValueError("Selected idea does not exist.")

        brief = generate_blueprint(
            idea,
            session.intent,
            messages=session.messages,
            images=session.images,
            hypotheses=session.hypotheses,
            generate=generate_architecture,
        )

        return {
            "session": append_blueprint(session, brief),
        }

    builder = StateGraph(ExplorationState)

    builder.add_node(
        "explore_images",
        with_start_event("explore_images", explore_images),
    )
    builder.add_node(
        "explore_hypotheses",
        with_start_event("explore_hypotheses", explore_hypotheses),
    )
    builder.add_node(
        "revise_hypotheses",
        with_start_event("revise_hypotheses", revise_hypotheses),
    )
    builder.add_node(
        "ask_question",
        with_start_event("ask_question", ask_question),
    )
    builder.add_node(
        "create_ideas",
        with_start_event("create_ideas", create_ideas),
    )
    builder.add_node(
        "select_idea",
        with_start_event("select_idea", select_idea),
    )
    builder.add_node(
        "build_blueprint",
        with_start_event("build_blueprint", build_blueprint),
    )
    builder.add_edge("build_blueprint", END)

    builder.add_conditional_edges(START, route_command)
    builder.add_conditional_edges("explore_images", route_after_images)

    builder.add_edge("explore_hypotheses", "ask_question")
    builder.add_edge("revise_hypotheses", "ask_question")
    builder.add_edge("select_idea", END)
    builder.add_edge("create_ideas", END)
    builder.add_edge("build_blueprint", END)

    return builder.compile()
