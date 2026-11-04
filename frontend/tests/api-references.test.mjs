import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, createReference } from "../src/api.ts";

test("creates a reference in the requested session", async () => {
  const originalFetch = globalThis.fetch;
  const document = {
    id: "document-1",
    session_id: "session-1",
    title: "Engineering notes",
    text: "  Preserve the original text.  ",
  };
  const calls = [];

  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return new Response(JSON.stringify(document), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const result = await createReference(
      "session-1",
      document.title,
      document.text,
    );

    assert.deepEqual(result, document);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, "/api/sessions/session-1/references");
    assert.equal(calls[0].options.method, "POST");
    assert.equal(calls[0].options.headers["Content-Type"], "application/json");
    assert.deepEqual(JSON.parse(calls[0].options.body), {
      title: document.title,
      text: document.text,
    });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("preserves reference API error status and message", async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({ detail: "Reference processing is unavailable." }),
      {
        status: 503,
        headers: { "Content-Type": "application/json" },
      },
    );

  try {
    await assert.rejects(
      () => createReference("session-1", "Notes", "Some reference text."),
      (error) =>
        error instanceof ApiError &&
        error.status === 503 &&
        error.message === "Reference processing is unavailable.",
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
