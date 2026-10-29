import assert from "node:assert/strict";
import test from "node:test";

import {
    streamBlueprint,
    streamIdeas,
    streamMessage,
} from "../src/api.ts";

/** Build a response whose UTF-8 bytes arrive individually. */
function createStreamResponse (text) {
    const bytes = new TextEncoder().encode(text);

    return new Response(
        new ReadableStream({
            start (controller) {
                for (const byte of bytes) {
                    controller.enqueue(new Uint8Array([byte]));
                }
                controller.close();
            },
        }),
        {
            headers: {
                "Content-Type": "text/event-stream; charset=utf-8",
            },
        },
    );
}

test("streams node events and returns persisted completion", async (t) => {
    const sessionId = "session-1";
    const received = [];

    const fetchMock = t.mock.method(globalThis, "fetch", async (url, options) => {
        assert.equal(url, "/api/sessions/session-1/messages/stream");
        assert.equal(options.method, "POST");
        assert.deepEqual(JSON.parse(options.body), {
            text: "  A golden note.\n",
        });

        return createStreamResponse(
            'event: node_started\n' +
            'data: {"node":"explore_images"}\n\n' +
            'event: node_completed\n' +
            'data: {"node":"explore_images"}\n\n' +
            'event: node_completed\n' +
            'data: {"node":"ask_question"}\n\n' +
            'event: session_completed\n' +
            'data: {"session_id":"session-1","revision":4}\n\n',
        );
    });

    const result = await streamMessage(
        sessionId,
        "  A golden note.\n",
        (event) => received.push(event),
    );

    assert.equal(fetchMock.mock.callCount(), 1);
    assert.deepEqual(received, [
        {
            event: "node_started",
            data: { node: "explore_images" },
        },
        {
            event: "node_completed",
            data: { node: "explore_images" },
        },
        {
            event: "node_completed",
            data: { node: "ask_question" },
        },
    ]);
    assert.deepEqual(result, {
        event: "session_completed",
        data: { session_id: sessionId, revision: 4 },
    });
});

test("preserves UTF-8 characters split across byte chunks", async (t) => {
    const message = "Сессия изменилась. Перезагрузите её.";

    t.mock.method(globalThis, "fetch", async () =>
        createStreamResponse(
            "event: run_failed\n" +
            `data: ${JSON.stringify({
                code: "session_conflict",
                message,
            })}\n\n`,
        ),
    );

    const result = await streamMessage("session-1", "A note.", () => {
        assert.fail("No node completion was sent.");
    });

    assert.deepEqual(result, {
        event: "run_failed",
        data: {
            code: "session_conflict",
            message,
        },
    });
});

test("rejects a stream without a terminal event and does not retry", async (t) => {
    const received = [];

    const fetchMock = t.mock.method(globalThis, "fetch", async () =>
        createStreamResponse(
            'event: node_completed\n' +
            'data: {"node":"explore_images"}\n\n',
        ),
    );

    await assert.rejects(
        streamMessage(
            "session-1",
            "A note.",
            (event) => received.push(event),
        ),
        /Agent stream ended without a final event/,
    );

    assert.equal(received.length, 1);
    assert.equal(fetchMock.mock.callCount(), 1);
});

test("rejects completion for a different session", async (t) => {
    t.mock.method(globalThis, "fetch", async () =>
        createStreamResponse(
            'event: session_completed\n' +
            'data: {"session_id":"another-session","revision":4}\n\n',
        ),
    );

    await assert.rejects(
        streamMessage("session-1", "A note.", () => { }),
        /Agent stream returned a different session/,
    );
});

test("streams ideas without sending a narrative body", async (t) => {
    const received = [];

    const fetchMock = t.mock.method(
        globalThis,
        "fetch",
        async (url, options) => {
            assert.equal(url, "/api/sessions/session-1/ideas/stream");
            assert.equal(options.method, "POST");
            assert.equal(options.body, undefined);
            assert.equal(options.headers.Accept, "text/event-stream");

            return createStreamResponse(
                'event: node_started\n' +
                'data: {"node":"create_ideas"}\n\n' +
                'event: node_completed\n' +
                'data: {"node":"create_ideas"}\n\n' +
                'event: session_completed\n' +
                'data: {"session_id":"session-1","revision":5}\n\n',
            );
        },
    );

    const result = await streamIdeas(
        "session-1",
        (event) => received.push(event),
    );

    assert.equal(fetchMock.mock.callCount(), 1);
    assert.deepEqual(received, [
        {
            event: "node_started",
            data: { node: "create_ideas" },
        },
        {
            event: "node_completed",
            data: { node: "create_ideas" },
        },
    ]);
    assert.deepEqual(result, {
        event: "session_completed",
        data: { session_id: "session-1", revision: 5 },
    });
});

test("streams a blueprint for the saved selection", async (t) => {
    const received = [];

    const fetchMock = t.mock.method(
        globalThis,
        "fetch",
        async (url, options) => {
            assert.equal(url, "/api/sessions/session-1/briefs/stream");
            assert.equal(options.method, "POST");
            assert.equal(options.body, undefined);
            assert.equal(options.headers.Accept, "text/event-stream");

            return createStreamResponse(
                'event: node_started\n' +
                'data: {"node":"build_blueprint"}\n\n' +
                'event: node_completed\n' +
                'data: {"node":"build_blueprint"}\n\n' +
                'event: session_completed\n' +
                'data: {"session_id":"session-1","revision":6}\n\n',
            );
        },
    );

    const result = await streamBlueprint(
        "session-1",
        (event) => received.push(event),
    );

    assert.equal(fetchMock.mock.callCount(), 1);
    assert.deepEqual(received, [
        {
            event: "node_started",
            data: { node: "build_blueprint" },
        },
        {
            event: "node_completed",
            data: { node: "build_blueprint" },
        },
    ]);
    assert.deepEqual(result, {
        event: "session_completed",
        data: { session_id: "session-1", revision: 6 },
    });
});
