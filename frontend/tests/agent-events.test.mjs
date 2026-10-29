import assert from "node:assert/strict";
import test from "node:test";

import {
    AgentEventBuffer,
    parseAgentEvent,
} from "../src/agent-events.ts";

test("parses a completed node without declaring session success", () => {
    const result = parseAgentEvent(
        'event: node_completed\ndata: {"node":"explore_images"}',
    );

    assert.deepEqual(result, {
        event: "node_completed",
        data: { node: "explore_images" },
    });
});

test("parses persisted session completion with CRLF line endings", () => {
    const result = parseAgentEvent(
        'event: session_completed\r\n' +
        'data: {"session_id":"session-1","revision":4}',
    );

    assert.deepEqual(result, {
        event: "session_completed",
        data: {
            session_id: "session-1",
            revision: 4,
        },
    });
});

test("preserves the session conflict error code", () => {
    const result = parseAgentEvent(
        'event: run_failed\n' +
        'data: {"code":"session_conflict","message":"Reload the session."}',
    );

    assert.deepEqual(result, {
        event: "run_failed",
        data: {
            code: "session_conflict",
            message: "Reload the session.",
        },
    });
});

test("joins multiple data lines before parsing JSON", () => {
    const result = parseAgentEvent(
        'event: node_completed\n' +
        'data: {\n' +
        'data: "node": "ask_question"\n' +
        'data: }',
    );

    assert.deepEqual(result, {
        event: "node_completed",
        data: { node: "ask_question" },
    });
});

test("ignores heartbeat comments", () => {
    assert.equal(parseAgentEvent(": heartbeat"), null);
});

test("rejects malformed JSON", () => {
    assert.throws(
        () => parseAgentEvent("event: node_completed\ndata: {"),
        SyntaxError,
    );
});

test("rejects invalid completion revisions", () => {
    for (const revision of [-1, 1.5, "4", null]) {
        const payload = JSON.stringify({
            session_id: "session-1",
            revision,
        });

        assert.throws(
            () =>
                parseAgentEvent(
                    `event: session_completed\ndata: ${payload}`,
                ),
            /Invalid session completion event/,
        );
    }
});

test("rejects unknown events", () => {
    assert.throws(
        () => parseAgentEvent("event: unexpected\ndata: {}"),
        /Unsupported agent event/,
    );
});

test("assembles an event split across chunks", () => {
    const buffer = new AgentEventBuffer();

    assert.deepEqual(
        buffer.push('event: node_completed\ndata: {"node":"explore_'),
        [],
    );

    assert.deepEqual(
        buffer.push('images"}\n\n'),
        [
            {
                event: "node_completed",
                data: { node: "explore_images" },
            },
        ],
    );

    assert.doesNotThrow(() => buffer.finish());
});

test("reads multiple events and handles a split CRLF separator", () => {
    const buffer = new AgentEventBuffer();

    assert.deepEqual(
        buffer.push(
            'event: node_completed\r\n' +
            'data: {"node":"explore_images"}\r\n\r',
        ),
        [],
    );

    assert.deepEqual(
        buffer.push(
            '\n' +
            'event: node_completed\n' +
            'data: {"node":"ask_question"}\n\n',
        ),
        [
            {
                event: "node_completed",
                data: { node: "explore_images" },
            },
            {
                event: "node_completed",
                data: { node: "ask_question" },
            },
        ],
    );

    assert.doesNotThrow(() => buffer.finish());
});

test("rejects a truncated final event", () => {
    const buffer = new AgentEventBuffer();

    buffer.push(
        'event: session_completed\ndata: {"session_id":"session-1"',
    );

    assert.throws(
        () => buffer.finish(),
        /Agent stream ended with an incomplete event/,
    );
});

test("parses a node start event", () => {
    const result = parseAgentEvent(
        'event: node_started\ndata: {"node":"explore_images"}',
    );

    assert.deepEqual(result, {
        event: "node_started",
        data: { node: "explore_images" },
    });
});
