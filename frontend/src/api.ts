import type { Intent, Session } from "./types";

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
