import { useState } from "react";
import {
  createSession,
  loadSession,
  streamMessage,
  selectIdea,
  streamBlueprint,
  streamIdeas,
} from "./api";
import type { AgentRunStatus, NodeLifecycleEvent } from "./agent-events";
import type { Session } from "./types";
import "./App.css";
import { AgentActivity } from "./AgentActivity";
import { BlueprintView } from "./BlueprintView";
import { IdeasView } from "./IdeasView";
import {
  JourneyNav,
  GoalSummary,
  IntentionView,
  ImaginationView,
} from "./JourneyViews";
import { restoredStage } from "./journey";
import type { Stage } from "./journey";

export default function App() {
  const [stage, setStage] = useState<Stage>("intention");
  const [goal, setGoal] = useState("");
  const [constraints, setConstraints] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [session, setSession] = useState<Session | null>(null);
  const [narrative, setNarrative] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agentRunStatus, setAgentRunStatus] = useState<AgentRunStatus>("idle");
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>(null);

  function handleNodeEvent(event: NodeLifecycleEvent) {
    if (event.event === "node_started") {
      setActiveNode(event.data.node);
      return;
    }

    setCompletedNodes((nodes) => [...nodes, event.data.node]);
    setActiveNode((current) => (current === event.data.node ? null : current));
  }

  async function run(operation: () => Promise<Session>) {
    setLoading(true);
    setError("");

    try {
      const result = await operation();
      setSession(result);
      setStage(restoredStage(result));
      setSessionId(result.id);
      setNarrative("");
      setCompletedNodes([]);
      setActiveNode(null);
      setAgentRunStatus("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected error.");
    } finally {
      setLoading(false);
    }
  }

  async function handleGenerateIdeas() {
    if (!session || loading || session.images.length === 0) return;

    const currentSessionId = session.id;

    setLoading(true);
    setError("");
    setCompletedNodes([]);
    setActiveNode(null);
    setAgentRunStatus("running");

    try {
      let result;

      try {
        result = await streamIdeas(currentSessionId, handleNodeEvent);
      } catch (err) {
        setAgentRunStatus("interrupted");
        setError(
          err instanceof Error
            ? err.message
            : "Idea stream interrupted. Reopen the session.",
        );
        return;
      }

      if (result.event === "run_failed") {
        setAgentRunStatus("failed");
        setError(result.data.message);

        if (result.data.code === "session_conflict") {
          try {
            setSession(await loadSession(currentSessionId));
          } catch {
            setError(
              "Session changed, but reloading failed. Open the session again.",
            );
          }
        }

        return;
      }

      setAgentRunStatus("completed");

      try {
        setSession(await loadSession(currentSessionId));
        setStage("ideas");
      } catch {
        setError(
          "Ideas were saved, but reloading failed. Open the session again.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectIdea(ideaId: string) {
    if (!session || loading) return;

    setLoading(true);
    setError("");

    try {
      const updated = await selectIdea(session.id, ideaId);
      setSession(updated);
      setStage("blueprint");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Idea selection failed.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSendMessage() {
    if (!session || !narrative.trim() || loading) return;

    const currentSessionId = session.id;
    const text = narrative;

    setLoading(true);
    setError("");
    setActiveNode(null);
    setCompletedNodes([]);
    setAgentRunStatus("running");

    try {
      let result;

      try {
        result = await streamMessage(currentSessionId, text, handleNodeEvent);
      } catch (err) {
        // Without a terminal event, persistence remains unconfirmed.
        setAgentRunStatus("interrupted");
        setError(
          err instanceof Error ? err.message : "Agent stream interrupted.",
        );
        return;
      }

      if (result.event === "run_failed") {
        setAgentRunStatus("failed");
        setError(result.data.message);

        if (result.data.code === "session_conflict") {
          try {
            const restored = await loadSession(currentSessionId);
            setSession(restored);
          } catch {
            setError(
              "Session changed, but reloading failed. Open the session again.",
            );
          }
        }

        return;
      }

      setAgentRunStatus("completed");
      setNarrative("");

      try {
        const restored = await loadSession(currentSessionId);
        setSession(restored);
      } catch {
        // Persistence succeeded even if this follow-up read failed.
        setError(
          "Exploration was saved, but reloading failed. Open the session again.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  function handleCreate() {
    if (!goal.trim()) {
      setError("Please enter your goal.");
      return;
    }

    void run(() =>
      createSession({
        goal: goal.trim(),
        constraints: constraints
          .split("\n")
          .map((value) => value.trim())
          .filter(Boolean),
      }),
    );
  }

  function handleRestore() {
    if (!sessionId.trim()) {
      setError("Please enter a session ID.");
      return;
    }

    void run(() => loadSession(sessionId.trim()));
  }

  async function handleBuildBlueprint() {
    if (!session || !session.selected_idea_id || loading) return;

    const currentSessionId = session.id;

    setLoading(true);
    setError("");
    setCompletedNodes([]);
    setActiveNode(null);
    setAgentRunStatus("running");

    try {
      let result;

      try {
        result = await streamBlueprint(currentSessionId, handleNodeEvent);
      } catch (err) {
        setAgentRunStatus("interrupted");
        setError(
          err instanceof Error
            ? err.message
            : "Blueprint stream interrupted. Reopen the session.",
        );
        return;
      }

      if (result.event === "run_failed") {
        setAgentRunStatus("failed");
        setError(result.data.message);

        if (result.data.code === "session_conflict") {
          try {
            setSession(await loadSession(currentSessionId));
          } catch {
            setError(
              "Session changed, but reloading failed. Open the session again.",
            );
          }
        }

        return;
      }

      setAgentRunStatus("completed");

      try {
        setSession(await loadSession(currentSessionId));
      } catch {
        setError(
          "Blueprint was saved, but reloading failed. Open the session again.",
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <span className="eyebrow">AI IMAGINATION ENGINE</span>
          <h1>MuseCapsule</h1>
          <p className="muted">Where imagination becomes an idea.</p>
        </div>
        <details className="restore">
          <summary>Continue an exploration</summary>
          <label htmlFor="session">Session ID</label>
          <input
            id="session"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
          />
          <button
            className="secondary"
            onClick={handleRestore}
            disabled={loading}
          >
            Open session
          </button>
        </details>
      </header>
      {session && <GoalSummary session={session} />}
      <JourneyNav stage={stage} onNavigate={setStage} hasSession={!!session} />
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {loading && (
        <p role="status" className="muted">
          {agentRunStatus === "running"
            ? "Your imagination is taking shape…"
            : "Saving or loading your session…"}
        </p>
      )}
      {stage === "intention" && (
        <IntentionView
          session={session}
          goal={goal}
          constraints={constraints}
          onGoal={setGoal}
          onConstraints={setConstraints}
          onCreate={handleCreate}
          loading={loading}
          onContinue={() => setStage("imagination")}
        />
      )}
      {session && stage === "imagination" && (
        <ImaginationView
          session={session}
          narrative={narrative}
          onNarrative={setNarrative}
          onSend={handleSendMessage}
          loading={loading}
          onIdeas={() => setStage("ideas")}
          onGenerate={handleGenerateIdeas}
        />
      )}
      {session && stage === "ideas" && (
        <IdeasView
          session={session}
          loading={loading}
          onGenerate={handleGenerateIdeas}
          onSelect={handleSelectIdea}
          onBlueprint={() => setStage("blueprint")}
        />
      )}
      {session && stage === "blueprint" && (
        <BlueprintView
          session={session}
          loading={loading}
          onBuild={handleBuildBlueprint}
          onIdeas={() => setStage("ideas")}
        />
      )}
      <AgentActivity
        completedNodes={completedNodes}
        activeNode={activeNode}
        agentRunStatus={agentRunStatus}
      />
    </main>
  );
}
