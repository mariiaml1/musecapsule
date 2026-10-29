from collections.abc import Callable, Iterator
import json
from typing import Any

from musecapsule.state import SessionState


def collect_agent_events(
    graph: Any,
    graph_input: dict,
) -> Iterator[dict]:
    """Expose completed LangGraph node events without leaking state."""

    for update in graph.stream(
        graph_input,
        stream_mode="updates",
    ):
        for node_name in update:
            yield {
                "event": "node_completed",
                "node": node_name,
            }


def encode_sse(event: str, data: dict) -> str:
    """Encode a named Server-Sent Event."""
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {payload}\n\n"


def stream_graph_run(
    graph,
    graph_input: dict,
    save_result: Callable[[SessionState], None],
) -> Iterator[str]:
    """Stream graph progress and persist the final session once."""
    latest_session: SessionState = graph_input["session"]

    try:
        for update in graph.stream(
            graph_input,
            stream_mode="updates",
        ):
            for node_name, node_output in update.items():
                if isinstance(node_output, dict) and isinstance(
                    node_output.get("session"),
                    SessionState,
                ):
                    latest_session = node_output["session"]

                yield encode_sse(
                    "node_completed",
                    {"node": node_name},
                )

        save_result(latest_session)

        yield encode_sse(
            "session_completed",
            {
                "session_id": str(latest_session.id),
                "revision": latest_session.revision,
            },
        )

    except Exception:
        # Do not expose prompts, internal state, or exception details.
        yield encode_sse(
            "run_failed",
            {"message": "Agent execution failed."},
        )
