from collections.abc import Callable
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from musecapsule.agents.imagination_guide import generate_exploration_question
from musecapsule.agents.metaphor_explorer import (
    extract_images,
    propose_hypotheses,
)
from musecapsule.models import Message
from musecapsule.state import (
    SessionState,
    append_hypothesis,
    append_image_fragment,
    append_message,
)


class ExplorationState(TypedDict):
    """Workflow data for an initial narrative exploration."""

    session: SessionState
    incoming_message: Message


def build_initial_exploration_graph(
    *,
    generate_images: Callable[[str], str],
    generate_hypotheses: Callable[[str], str],
    generate_question: Callable[[str], str],
):
    """Compile the initial exploration workflow with injected generation."""

    def explore_images(state: ExplorationState) -> dict:
        """Validate extraction before adding the message and its images."""
        message = state["incoming_message"]
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

    builder = StateGraph(ExplorationState)
    builder.add_node("explore_images", explore_images)
    builder.add_node("explore_hypotheses", explore_hypotheses)
    builder.add_node("ask_question", ask_question)

    builder.add_edge(START, "explore_images")
    builder.add_edge("explore_images", "explore_hypotheses")
    builder.add_edge("explore_hypotheses", "ask_question")
    builder.add_edge("ask_question", END)

    return builder.compile()
