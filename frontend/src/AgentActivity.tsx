import { AgentFlow } from "./AgentFlow";
import type { AgentRunStatus } from "./agent-events";
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

export function AgentActivity({
  completedNodes,
  activeNode,
  agentRunStatus,
}: {
  completedNodes: string[];
  activeNode: string | null;
  agentRunStatus: AgentRunStatus;
}) {
  return (
    <details className="panel activity">
      <summary>
        Under the hood <span>Agent Activity · {agentRunStatus}</span>
      </summary>
      <p role="status" aria-live="polite">
        {agentRunStatus === "idle" && "Waiting for a workflow request."}
        {agentRunStatus === "running" && "Workflow in progress…"}
        {agentRunStatus === "completed" && "Workflow result saved."}
        {agentRunStatus === "failed" && "Workflow failed."}
        {agentRunStatus === "interrupted" &&
          "Result unconfirmed. Reopen the session before retrying."}
      </p>
      <AgentFlow
        completedNodes={completedNodes}
        activeNode={activeNode}
        runStatus={agentRunStatus}
      />
      <div className="agent-flow">
        {completedNodes.map((node, index) => {
          const label = nodeLabels[node];

          return (
            <div className="agent-step" key={`${index}-${node}`}>
              <span className="agent-number">{index + 1}</span>
              <div>
                <strong>{label?.agent ?? node}</strong>
                <p className="muted">{label?.step ?? node} — Completed</p>
              </div>
            </div>
          );
        })}

        {activeNode && (
          <div className="agent-step">
            <span className="agent-number">{completedNodes.length + 1}</span>
            <div>
              <strong>{nodeLabels[activeNode]?.agent ?? activeNode}</strong>
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
    </details>
  );
}
