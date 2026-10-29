import { useState } from "react";
import {
  createSession,
  loadSession,
  streamMessage,
  generateIdeas,
  selectIdea,
  buildBlueprint,
} from "./api";
import type { AgentRunStatus } from "./agent-events";
import type { Session } from "./types";
import "./App.css";

const nodeLabels: Record<string, { agent: string; step: string }> = {
  explore_images: {
    agent: "Metaphor Explorer",
    step: "Extract images",
  },
  explore_hypotheses: {
    agent: "Metaphor Explorer",
    step: "Propose meaning hypotheses",
  },
  revise_hypotheses: {
    agent: "Metaphor Explorer",
    step: "Revise hypotheses",
  },
  ask_question: {
    agent: "Imagination Guide",
    step: "Ask an exploration question",
  },
  create_ideas: {
    agent: "Idea Evolution",
    step: "Generate product ideas",
  },
  build_blueprint: {
    agent: "Idea Architect",
    step: "Build an engineering blueprint",
  },
  select_idea: {
    agent: "User Selection",
    step: "Save the selected idea",
  },
};

export default function App() {
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

  async function run(operation: () => Promise<Session>) {
    setLoading(true);
    setError("");

    try {
      const result = await operation();
      setSession(result);
      setCompletedNodes([]);
      setAgentRunStatus("idle");
      setSessionId(result.id);
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

    setLoading(true);
    setError("");

    try {
      const updated = await generateIdeas(session.id);
      setSession(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Idea generation failed.");
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
        result = await streamMessage(
          currentSessionId,
          text,
          (event) => {
            if (event.event === "node_started") {
              setActiveNode(event.data.node);
              return;
            }

            setCompletedNodes((nodes) => [...nodes, event.data.node]);
            setActiveNode((current) =>
              current === event.data.node ? null : current,
            );
          },
        );
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

    setLoading(true);
    setError("");

    try {
      const updated = await buildBlueprint(session.id);
      setSession(updated);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Blueprint generation failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  const selectedIdea = session?.ideas.find(
    (idea) => idea.id === session.selected_idea_id,
  );

  const selectedBrief = session?.briefs
    .filter((brief) => brief.idea_id === session.selected_idea_id)
    .at(-1);

  return (
    <main className="app-shell">
      <header className="app-header">
        <div>
          <span className="eyebrow">AI IMAGINATION ENGINE</span>
          <h1>MuseCapsule</h1>
          <p>Where imagination becomes an idea.</p>
        </div>
        <span className="session-status">
          {session ? "Session connected" : "New exploration"}
        </span>
      </header>

      <div className="workspace">
        <section className="panel">
          <h2>Imagination Workspace</h2>
          <p className="muted">
            Start with a goal. Let your imagination take it further.
          </p>

          <label htmlFor="goal">Your goal</label>
          <textarea
            id="goal"
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
            placeholder="What would you like to create?"
            rows={3}
          />

          <label htmlFor="constraints">Constraints (one per line)</label>
          <textarea
            id="constraints"
            value={constraints}
            onChange={(event) => setConstraints(event.target.value)}
            placeholder={"Solo development\nSmall MVP"}
            rows={3}
          />

          <button onClick={handleCreate} disabled={loading}>
            Create session
          </button>

          <div className="separator" />

          <label htmlFor="session">Continue an exploration</label>
          <input
            id="session"
            value={sessionId}
            onChange={(event) => setSessionId(event.target.value)}
            placeholder="Existing session ID"
          />
          <button
            className="secondary"
            onClick={handleRestore}
            disabled={loading}
          >
            Open session
          </button>

          {error && (
            <p role="alert" className="error">
              {error}
            </p>
          )}

          {session && (
            <div className="session-details">
              <span className="eyebrow">ACTIVE GOAL</span>
              <h3>{session.intent.goal}</h3>
              <p className="muted">Revision {session.revision}</p>
            </div>
          )}

          {session && (
            <div className="conversation">
              <h3>Imagination Dialogue</h3>

              {session.messages.map((message) => (
                <div
                  key={message.id}
                  className={`chat-message ${message.role}`}
                >
                  <span className="eyebrow">
                    {message.role === "user" ? "YOU" : "IMAGINATION GUIDE"}
                  </span>
                  <p>{message.text}</p>
                </div>
              ))}

              <textarea
                value={narrative}
                onChange={(event) => setNarrative(event.target.value)}
                placeholder="Describe what you imagine..."
                rows={3}
                disabled={loading}
              />

              <button
                onClick={handleSendMessage}
                disabled={loading || !narrative.trim()}
              >
                {loading ? "Exploring..." : "Explore imagination"}
              </button>
            </div>
          )}
        </section>

        <section className="panel flow-panel">
          <h2>Agent Flow</h2>
          <p className="muted">
            Live execution stages from the latest exploration request.
          </p>

          <p role="status" aria-live="polite">
            {agentRunStatus === "idle" && "Waiting for an exploration."}
            {agentRunStatus === "running" && "Exploration in progress…"}
            {agentRunStatus === "completed" && "Exploration saved."}
            {agentRunStatus === "failed" && "Exploration failed."}
            {agentRunStatus === "interrupted" &&
              "Result unconfirmed. Reopen the session before retrying."}
          </p>

          <div className="agent-flow">
            {completedNodes.map((node, index) => {
              const label = nodeLabels[node];

              return (
                <div className="agent-step" key={`${index}-${node}`}>
                  <span className="agent-number">{index + 1}</span>
                  <div>
                    <strong>{label?.agent ?? node}</strong>
                    <p className="muted">
                      {label?.step ?? node} — Completed
                    </p>
                  </div>
                </div>
              );
            })}

            {activeNode && (
              <div className="agent-step">
                <span className="agent-number">
                  {completedNodes.length + 1}
                </span>
                <div>
                  <strong>
                    {nodeLabels[activeNode]?.agent ?? activeNode}
                  </strong>
                  <p className="muted">
                    {nodeLabels[activeNode]?.step ?? activeNode}
                    {" — "}
                    {agentRunStatus === "running"
                      ? "Running…"
                      : "Completion unconfirmed"}
                  </p>
                </div>
              </div>
            )}
          </div>

          <p className="flow-note">
            A completed node does not confirm that the session was saved.
          </p>
        </section>

        <section className="panel">
          <h2>Idea Studio</h2>

          <p className="muted">
            Turn your imagined images into meaningful product ideas.
          </p>

          <button
            onClick={handleGenerateIdeas}
            disabled={!session || loading || session.images.length === 0}
          >
            {loading ? "Working..." : "Generate ideas ✦"}
          </button>

          {session?.ideas.length ? (
            <div className="idea-list">
              {session.ideas.map((idea) => {
                const selected = session.selected_idea_id === idea.id;

                return (
                  <article
                    key={idea.id}
                    className={`idea-card ${selected ? "selected" : ""}`}
                  >
                    <h3>{idea.title}</h3>
                    <p>{idea.description}</p>

                    <p className="muted">
                      {idea.goal_alignment}
                    </p>

                    <div className="idea-sources">
                      {idea.image_ids.map((imageId) => {
                        const image = session.images.find(
                          (item) => item.id === imageId,
                        );

                        return image ? (
                          <span className="source-tag" key={imageId}>
                            {image.label}
                          </span>
                        ) : null;
                      })}
                    </div>

                    <button
                      className={selected ? "secondary" : ""}
                      disabled={loading || selected}
                      onClick={() => void handleSelectIdea(idea.id)}
                    >
                      {selected ? "Selected ✓" : "Choose this idea"}
                    </button>
                  </article>
                );
              })}
              {selectedIdea && (
                <div className="blueprint-panel">
                  <h3>Engineering Blueprint</h3>
                  <p className="muted">
                    Turn your selected idea into a practical implementation plan.
                  </p>

                  <button
                    onClick={() => void handleBuildBlueprint()}
                    disabled={loading}
                  >
                    {loading ? "Working..." : "Build my idea ✦"}
                  </button>

                  {selectedBrief && (
                    <div className="blueprint-content">
                      <h3>{selectedIdea.title}</h3>
                      <p>{selectedBrief.idea_summary}</p>

                      <h4>Metaphor Origin</h4>
                      <p>{selectedBrief.metaphor_origin.meaning_basis}</p>

                      <h4>How the metaphor becomes a product</h4>
                      <p>{selectedBrief.metaphor_origin.mechanic_mapping}</p>

                      <h4>Core User Flow</h4>
                      <p>{selectedBrief.core_scenario}</p>

                      <h4>MVP Features</h4>
                      <ul>
                        {selectedBrief.features.map((feature, index) => (
                          <li key={index}>{feature}</li>
                        ))}
                      </ul>

                      <h4>Suggested Architecture</h4>
                      {selectedBrief.suggested_architecture.length ? (
                        selectedBrief.suggested_architecture.map((component, index) => (
                          <div className="architecture-item" key={index}>
                            <strong>{component.name}</strong>
                            <p>{component.responsibility}</p>
                            {component.suggested_technology && (
                              <span className="muted">
                                {component.suggested_technology}
                              </span>
                            )}
                          </div>
                        ))
                      ) : (
                        <p className="muted">No additional components proposed.</p>
                      )}

                      <h4>Definition of Done</h4>
                      <ul>
                        {selectedBrief.acceptance_criteria.map((criterion, index) => (
                          <li key={index}>{criterion}</li>
                        ))}
                      </ul>

                      <p className="muted">
                        {selectedBrief.metaphor_origin.user_confirmed
                          ? "Meaning confirmed by the user."
                          : "Meaning proposed by AI — not yet confirmed by the user."}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="empty-state">
              <span>✦</span>
              <p>Your ideas will appear here.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
