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
  hypothesis_history?: HypothesisRevision[];
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
  /** The source idea when this proposal is a revised version. */
  previous_idea_id?: string | null;
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

/** An exact quotation from reference material supplied to the architect. */
export interface ReferenceCitation {
  document_id: string;
  chunk_id: string;
  quote: string;
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
  references?: ReferenceCitation[];
}

/** An exact narrative quote linked to its original message. */
export interface EvidenceRef {
  message_id: string;
  quote: string;
}

/** Historical status change returned by the session API. */
export interface HypothesisRevision {
  previous: Hypothesis;
  new_status: Hypothesis["status"];
  reason: string;
  evidence: EvidenceRef[];
  session_revision: number;
}

/** Reference material stored within one session. */
export interface ReferenceDocument {
  id: string;
  session_id: string;
  title: string;
  text: string;
}
