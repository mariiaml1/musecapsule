import assert from "node:assert/strict";
import test from "node:test";

import { getObservedTransitions } from "../src/flow-path.ts";

test("does not invent transitions before another node starts", () => {
    const result = getObservedTransitions(["explore_images"], null);

    assert.deepEqual([...result], []);
});

test("includes the transition to the active node", () => {
    const result = getObservedTransitions(
        ["explore_images"],
        "revise_hypotheses",
    );

    assert.deepEqual([...result], [
        "explore_images->revise_hypotheses",
    ]);
});

test("preserves the proposal route without highlighting revisions", () => {
    const result = getObservedTransitions(
        ["explore_images", "explore_hypotheses", "ask_question"],
        null,
    );

    assert.deepEqual([...result], [
        "explore_images->explore_hypotheses",
        "explore_hypotheses->ask_question",
    ]);
});

test("preserves a direct transition to the question", () => {
    const result = getObservedTransitions(
        ["explore_images"],
        "ask_question",
    );

    assert.deepEqual([...result], [
        "explore_images->ask_question",
    ]);
});
