/** A graph node finished; session persistence is not yet confirmed. */
export interface NodeCompletedEvent {
  event: "node_completed";
  data: {
    node: string;
  };
}

/** The workflow finished and its final session was persisted. */
export interface SessionCompletedEvent {
  event: "session_completed";
  data: {
    session_id: string;
    revision: number;
  };
}

/** The run did not report successful session persistence. */
export interface RunFailedEvent {
  event: "run_failed";
  data: {
    code: "session_conflict" | "execution_failed";
    message: string;
  };
}

export type AgentEvent =
  | NodeLifecycleEvent
  | SessionCompletedEvent
  | RunFailedEvent;

/** Client-side status of one streamed workflow request. */
export type AgentRunStatus =
  | "idle"
  | "running"
  | "completed"
  | "failed"
  | "interrupted";

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isNonblankString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

/** Parse and validate one complete SSE frame from the backend. */
export function parseAgentEvent(frame: string): AgentEvent | null {
  let eventName = "";
  const dataLines: string[] = [];

  for (const line of frame.split(/\r\n|\n|\r/)) {
    // SSE comments may be used as heartbeat messages.
    if (!line || line.startsWith(":")) continue;

    const separator = line.indexOf(":");
    const field = separator === -1 ? line : line.slice(0, separator);
    let value = separator === -1 ? "" : line.slice(separator + 1);

    if (value.startsWith(" ")) {
      value = value.slice(1);
    }

    if (field === "event") eventName = value;
    if (field === "data") dataLines.push(value);
  }

  if (dataLines.length === 0) return null;

  const data: unknown = JSON.parse(dataLines.join("\n"));

  if (!isRecord(data)) {
    throw new Error("Invalid agent event payload.");
  }

  switch (eventName) {
    case "node_started":
      if (!isNonblankString(data.node)) {
        throw new Error("Invalid node start event.");
      }

      return {
        event: "node_started",
        data: { node: data.node },
      };
    case "node_completed":
      if (!isNonblankString(data.node)) {
        throw new Error("Invalid node completion event.");
      }

      return {
        event: "node_completed",
        data: { node: data.node },
      };

    case "session_completed":
      if (
        !isNonblankString(data.session_id) ||
        typeof data.revision !== "number" ||
        !Number.isSafeInteger(data.revision) ||
        data.revision < 0
      ) {
        throw new Error("Invalid session completion event.");
      }

      return {
        event: "session_completed",
        data: {
          session_id: data.session_id,
          revision: data.revision,
        },
      };

    case "run_failed":
      if (
        (data.code !== "session_conflict" &&
          data.code !== "execution_failed") ||
        !isNonblankString(data.message)
      ) {
        throw new Error("Invalid run failure event.");
      }

      return {
        event: "run_failed",
        data: {
          code: data.code,
          message: data.message,
        },
      };

    default:
      throw new Error("Unsupported agent event.");
  }
}

/** Assemble complete SSE frames from incrementally decoded text. */
export class AgentEventBuffer {
  private pending = "";

  push(chunk: string): AgentEvent[] {
    this.pending += chunk;
    const events: AgentEvent[] = [];

    while (true) {
      const separator = /\r?\n\r?\n/.exec(this.pending);
      if (!separator) break;

      const frame = this.pending.slice(0, separator.index);
      this.pending = this.pending.slice(
        separator.index + separator[0].length,
      );

      const event = parseAgentEvent(frame);
      if (event !== null) events.push(event);
    }

    return events;
  }

  /** Reject an incomplete frame when the response body ends. */
  finish(): void {
    if (this.pending.trim()) {
      throw new Error("Agent stream ended with an incomplete event.");
    }

    this.pending = "";
  }
}

/** A graph node has begun executing. */
export interface NodeStartedEvent {
  event: "node_started";
  data: {
    node: string;
  };
}

export type NodeLifecycleEvent =
  | NodeStartedEvent
  | NodeCompletedEvent;
