import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, reviseIdea } from "../src/api.ts";

test("requests one idea revision and returns the saved session", async (t) => {
    const savedSession = {
        id: "session-1",
        revision: 8,
        selected_idea_id: "idea-1",
        ideas: [
            { id: "idea-1", previous_idea_id: null },
            { id: "idea-2", previous_idea_id: "idea-1" },
        ],
    };

    const fetchMock = t.mock.method(
        globalThis,
        "fetch",
        async (url, options) => {
            assert.equal(
                url,
                "/api/sessions/session-1/ideas/idea-1/revisions",
            );
            assert.equal(options.method, "POST");
            assert.equal(options.body, undefined);

            return new Response(JSON.stringify(savedSession), {
                headers: { "Content-Type": "application/json" },
            });
        },
    );

    const result = await reviseIdea("session-1", "idea-1");

    assert.deepEqual(result, savedSession);
    assert.equal(fetchMock.mock.callCount(), 1);
});

test("preserves revision conflicts without retrying", async (t) => {
    const fetchMock = t.mock.method(globalThis, "fetch", async () =>
        new Response(
            JSON.stringify({
                detail: "Session changed during processing.",
            }),
            {
                status: 409,
                headers: { "Content-Type": "application/json" },
            },
        ),
    );

    await assert.rejects(
        reviseIdea("session-1", "idea-1"),
        (error) => {
            assert.ok(error instanceof ApiError);
            assert.equal(error.status, 409);
            assert.equal(error.message, "Session changed during processing.");
            return true;
        },
    );

    assert.equal(fetchMock.mock.callCount(), 1);
});
