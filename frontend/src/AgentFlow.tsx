import { ReactFlow } from "@xyflow/react";
import type { Edge, Node } from "@xyflow/react";

import type { AgentRunStatus } from "./agent-events";
import { getObservedTransitions } from "./flow-path";

interface AgentFlowProps {
    completedNodes: string[];
    activeNode: string | null;
    runStatus: AgentRunStatus;
}

const layout = [
    {
        id: "explore_images",
        label: "Metaphor Explorer\nExtract images",
        position: { x: 180, y: 0 },
    },
    {
        id: "explore_hypotheses",
        label: "Metaphor Explorer\nPropose hypotheses",
        position: { x: 0, y: 150 },
    },
    {
        id: "revise_hypotheses",
        label: "Metaphor Explorer\nRevise hypotheses",
        position: { x: 360, y: 150 },
    },
    {
        id: "ask_question",
        label: "Imagination Guide\nAsk a question",
        position: { x: 180, y: 320 },
    },
    {
        id: "create_ideas",
        label: "Idea Evolution\nGenerate product ideas",
        position: { x: 180, y: 490 },
    },
];

const edges: Edge[] = [
    {
        id: "images-proposals",
        source: "explore_images",
        target: "explore_hypotheses",
    },
    {
        id: "images-revisions",
        source: "explore_images",
        target: "revise_hypotheses",
    },
    {
        id: "images-question",
        source: "explore_images",
        target: "ask_question",
        style: { strokeDasharray: "5 5" },
    },
    {
        id: "proposals-question",
        source: "explore_hypotheses",
        target: "ask_question",
    },
    {
        id: "revisions-question",
        source: "revise_hypotheses",
        target: "ask_question",
    },
];

/** Display exploration topology with statuses grounded in backend events. */
export function AgentFlow({
    completedNodes,
    activeNode,
    runStatus,
}: AgentFlowProps) {
    const nodes: Node[] = layout.map((item) => {
        const completed = completedNodes.includes(item.id);
        const active = activeNode === item.id;

        const status = completed
            ? "Completed"
            : active
                ? runStatus === "running"
                    ? "Running…"
                    : "Completion unconfirmed"
                : "Not observed";

        return {
            id: item.id,
            position: item.position,
            data: { label: `${item.label}\n${status}` },
            style: {
                width: 220,
                whiteSpace: "pre-line",
                background: "#242235",
                color: "#f2efff",
                border: `2px solid ${completed ? "#70c7a3" : active ? "#bc9cff" : "#49445f"
                    }`,
                borderRadius: 12,
            },
        };
    });

    const observedTransitions = getObservedTransitions(
        completedNodes,
        activeNode,
    );

    const visibleEdges: Edge[] = edges.map((edge) => {
        const observed = observedTransitions.has(
            `${edge.source}->${edge.target}`,
        );

        return {
            ...edge,
            style: {
                ...edge.style,
                stroke: observed ? "#bc9cff" : "#49445f",
                strokeWidth: observed ? 3 : 1,
                opacity: observed ? 1 : 0.4,
            },
        };
    });

    return (
        <div style={{ width: "100%", height: 420 }}>
            <ReactFlow
                nodes={nodes}
                edges={visibleEdges}
                nodesDraggable={false}
                nodesConnectable={false}
                elementsSelectable={false}
                deleteKeyCode={null}
                colorMode="dark"
                fitView
            />
        </div>
    );
}
