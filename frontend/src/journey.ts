import type { Session } from "./types";
export type Stage = "intention" | "imagination" | "ideas" | "blueprint";
export const stages: Stage[] = [
  "intention",
  "imagination",
  "ideas",
  "blueprint",
];
/** Choose a view from saved data without executing a workflow. */
export function restoredStage(session: Session): Stage {
  if (session.selected_idea_id) return "blueprint";
  return session.ideas.length ? "ideas" : "imagination";
}
