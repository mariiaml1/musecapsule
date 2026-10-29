import type { Intent, Session } from "./types";
import { AgentEventBuffer } from "./agent-events.ts";
import type {
    NodeLifecycleEvent,
    RunFailedEvent,
    SessionCompletedEvent,
} from "./agent-events.ts";

export class ApiError extends Error {
    public readonly status: number;

    constructor(status: number, message: string) {
        super(message);
        this.name = "ApiError";
        this.status = status;
    }
}

/** Read an API response and preserve its HTTP error status. */
async function readResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
        let message = `Request failed (${response.status}).`;

        try {
            const body: unknown = await response.json();

            if (
                typeof body === "object" &&
                body !== null &&
                "detail" in body &&
                typeof body.detail === "string"
            ) {
                message = body.detail;
            }
        } catch {
            // Keep the fallback message when the error body is not JSON.
        }

        throw new ApiError(response.status, message);
    }

    return response.json() as Promise<T>;
}

/** Create a session with the user's explicit goal and constraints. */
export async function createSession(
    intent: Intent,
): Promise<Session> {
    const response = await fetch("/api/sessions", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(intent),
    });

    return readResponse<Session>(response);
}

/** Restore the latest saved session by its ID. */
export async function loadSession(
    sessionId: string,
): Promise<Session> {
    const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}`,
    );

    return readResponse<Session>(response);
}

/** Send a narrative message through the exploration workflow. */
export async function sendMessage(
    sessionId: string,
    text: string,
): Promise<Session> {
    const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/messages`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ text }),
        },
    );

    return readResponse<Session>(response);
}

/** Generate ideas from the existing exploration context. */
export async function generateIdeas(
    sessionId: string,
): Promise<Session> {
    const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/ideas`,
        { method: "POST" },
    );

    return readResponse<Session>(response);
}

/** Select one existing idea without invoking an LLM. */
export async function selectIdea(
    sessionId: string,
    ideaId: string,
): Promise<Session> {
    const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/selection`,
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ idea_id: ideaId }),
        },
    );

    return readResponse<Session>(response);
}

/** Build a new engineering blueprint for the selected idea. */
export async function buildBlueprint(
    sessionId: string,
): Promise<Session> {
    const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/briefs`,
        {
            method: "POST",
        },
    );

    return readResponse<Session>(response);
}

/** Execute one session command and consume its SSE response. */
async function streamSessionRequest(
    sessionId: string,
    action: "messages" | "ideas" | "briefs",
    body: { text: string } | undefined,
    onNodeEvent: (event: NodeLifecycleEvent) => void,
    signal?: AbortSignal,
): Promise<SessionCompletedEvent | RunFailedEvent> {
    const response = await fetch(
        `/api/sessions/${encodeURIComponent(sessionId)}/${action}/stream`,
        {
            method: "POST",
            headers: {
                ...(body === undefined
                    ? {}
                    : { "Content-Type": "application/json" }),
                Accept: "text/event-stream",
            },
            body: body === undefined ? undefined : JSON.stringify(body),
            signal,
        },
    );

    if (!response.ok) {
        // Reuse the existing HTTP error handling.
        await readResponse<never>(response);
        throw new Error("Unexpected HTTP error handling result.");
    }

    const contentType = response.headers
        .get("content-type")
        ?.split(";")[0]
        .trim();

    if (contentType !== "text/event-stream" || !response.body) {
        throw new Error("Expected an SSE response body.");
    }

    const reader = response.body
        .pipeThrough(new TextDecoderStream())
        .getReader();

    const buffer = new AgentEventBuffer();

    try {
        while (true) {
            const { value, done } = await reader.read();

            if (done) {
                buffer.finish();
                throw new Error(
                    "Agent stream ended without a final event. Reload the session.",
                );
            }

            const events = buffer.push(value);

            for (const event of events) {
                if (
                    event.event === "node_started" ||
                    event.event === "node_completed"
                ) {
                    onNodeEvent(event);
                    continue;
                }

                if (
                    event.event === "session_completed" &&
                    event.data.session_id !== sessionId
                ) {
                    throw new Error("Agent stream returned a different session.");
                }

                return event;
            }
        }
    } finally {
        try {
            await reader.cancel();
        } catch {
            // Cleanup must not replace the original result or error.
        }
        reader.releaseLock();
    }
}

/** Explore one narrative message through the streaming endpoint. */
export function streamMessage(
    sessionId: string,
    text: string,
    onNodeEvent: (event: NodeLifecycleEvent) => void,
    signal?: AbortSignal,
): Promise<SessionCompletedEvent | RunFailedEvent> {
    return streamSessionRequest(
        sessionId,
        "messages",
        { text },
        onNodeEvent,
        signal,
    );
}

/** Generate ideas from the saved session without adding a message. */
export function streamIdeas(
    sessionId: string,
    onNodeEvent: (event: NodeLifecycleEvent) => void,
    signal?: AbortSignal,
): Promise<SessionCompletedEvent | RunFailedEvent> {
    return streamSessionRequest(
        sessionId,
        "ideas",
        undefined,
        onNodeEvent,
        signal,
    );
}

/** Build a blueprint for the selected idea through the streaming endpoint. */
export function streamBlueprint(
    sessionId: string,
    onNodeEvent: (event: NodeLifecycleEvent) => void,
    signal?: AbortSignal,
): Promise<SessionCompletedEvent | RunFailedEvent> {
    return streamSessionRequest(
        sessionId,
        "briefs",
        undefined,
        onNodeEvent,
        signal,
    );
}
