export interface Intent {
    goal: string;
    constraints: string[];
}

export interface SessionOverview {
    id: string;
    intent: Intent;
    revision: number;
}

export interface Message {
    id: string;
    role: "user" | "assistant";
    text: string;
}

export interface Session extends SessionOverview {
    messages: Message[];
    images: ImageFragment[];
    hypotheses: Hypothesis[];
    ideas: ProductIdea[];
    selected_idea_id: string | null;
    briefs: MVPBrief[];
}

export interface ImageFragment {
    id: string;
    label: string;
    evidence: EvidenceRef[];
}

export interface Hypothesis {
    id: string;
    statement: string;
    status: "proposed" | "supported" | "unsupported" | "superseded";
    image_ids: string[];
    evidence: EvidenceRef[];
}

export interface ProductIdea {
    id: string;
    title: string;
    description: string;
    goal_alignment: string;
    image_ids: string[];
    hypothesis_ids: string[];
}

export interface MetaphorOrigin {
    image_ids: string[];
    hypothesis_ids: string[];
    meaning_basis: string;
    mechanic_mapping: string;
    user_confirmed: boolean;
}

export interface ArchitectureComponent {
    name: string;
    responsibility: string;
    suggested_technology: string | null;
}

export interface MVPBrief {
    idea_id: string;
    idea_summary: string;
    metaphor_origin: MetaphorOrigin;
    problem: string;
    audience: string;
    core_scenario: string;
    features: string[];
    constraints: string[];
    risks: string[];
    acceptance_criteria: string[];
    suggested_architecture: ArchitectureComponent[];
}

/** An exact narrative quote linked to its original message. */
export interface EvidenceRef {
    message_id: string;
    quote: string;
}
