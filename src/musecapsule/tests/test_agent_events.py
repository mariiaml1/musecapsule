from musecapsule.agent_events import collect_agent_events


def test_collect_agent_events_preserves_node_order():
    class FakeGraph:
        def stream(self, graph_input, *, stream_mode):
            assert graph_input == {"command": "explore"}
            assert stream_mode == "updates"

            yield {"explore_images": {"session": "updated"}}
            yield {"propose_hypotheses": {"session": "updated"}}
            yield {"ask_question": {"session": "updated"}}

    events = list(
        collect_agent_events(
            FakeGraph(),
            {"command": "explore"},
        )
    )

    assert events == [
        {"event": "node_completed", "node": "explore_images"},
        {"event": "node_completed", "node": "propose_hypotheses"},
        {"event": "node_completed", "node": "ask_question"},
    ]


import json

from musecapsule.agent_events import (
    encode_sse,
    stream_graph_run,
)
from musecapsule.models import Intent
from musecapsule.state import SessionState


def test_encode_sse_produces_valid_event_frame():
    result = encode_sse(
        "node_completed",
        {"node": "metaphor_explorer"},
    )

    assert result == (
        "event: node_completed\n" 'data: {"node": "metaphor_explorer"}\n\n'
    )


def test_stream_graph_run_saves_once_after_execution():
    session = SessionState(
        intent=Intent(
            goal="Build an AI portfolio project",
            constraints=["Solo development"],
        ),
    )
    updated = session.model_copy(
        update={"revision": 1},
    )

    graph_calls = []
    saved = []

    class FakeGraph:
        def stream(self, graph_input, *, stream_mode):
            graph_calls.append("stream")
            assert graph_input["session"] is session
            assert stream_mode == "updates"

            yield {"metaphor_explorer": {"session": updated}}
            yield {"imagination_guide": {"session": updated}}

    def save_result(result):
        graph_calls.append("save")
        saved.append(result)

    events = list(
        stream_graph_run(
            FakeGraph(),
            {"session": session},
            save_result,
        )
    )

    assert graph_calls == ["stream", "save"]
    assert saved == [updated]

    assert events[0] == encode_sse(
        "node_completed",
        {"node": "metaphor_explorer"},
    )
    assert events[1] == encode_sse(
        "node_completed",
        {"node": "imagination_guide"},
    )
    assert events[2] == encode_sse(
        "session_completed",
        {
            "session_id": str(updated.id),
            "revision": 1,
        },
    )


def test_stream_graph_run_does_not_report_success_when_save_fails():
    session = SessionState(
        intent=Intent(goal="Build an AI portfolio project"),
    )

    class FakeGraph:
        def stream(self, graph_input, *, stream_mode):
            yield {"metaphor_explorer": {"session": session}}

    def failing_save(_):
        raise RuntimeError("Database unavailable")

    events = list(
        stream_graph_run(
            FakeGraph(),
            {"session": session},
            failing_save,
        )
    )

    assert any("run_failed" in event for event in events)
    assert all("session_completed" not in event for event in events)
    assert all("Database unavailable" not in event for event in events)
