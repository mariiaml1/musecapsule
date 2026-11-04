import type { ProductIdea, Session } from "./types";

export interface IdeaVersion {
  idea: ProductIdea;
  depth: number;
}

export interface IdeaVersionGroup {
  id: string;
  root: ProductIdea;
  versions: IdeaVersion[];
  issue: "missing_parent" | "cycle" | null;
}

/** Group explicit ancestry only; titles never establish a version relationship. */
export function groupIdeaVersions(ideas: ProductIdea[]): IdeaVersionGroup[] {
  const byId = new Map(ideas.map((idea) => [idea.id, idea]));
  const groups = new Map<string, IdeaVersionGroup>();

  for (const idea of ideas) {
    let root = idea;
    let depth = 0;
    let issue: IdeaVersionGroup["issue"] = null;
    const visited = new Set([idea.id]);

    while (root.previous_idea_id) {
      const parent = byId.get(root.previous_idea_id);
      if (!parent) {
        issue = "missing_parent";
        break;
      }
      if (visited.has(parent.id)) {
        // Keep malformed cyclic records visible without inventing an original.
        root = idea;
        depth = 0;
        issue = "cycle";
        break;
      }
      visited.add(parent.id);
      root = parent;
      depth += 1;
    }

    let group = groups.get(root.id);
    if (!group) {
      group = { id: root.id, root, versions: [], issue };
      groups.set(root.id, group);
    }
    group.versions.push({ idea, depth });
  }

  return [...groups.values()].map((group) => ({
    ...group,
    // Stable ordering keeps each parent before its descendants, including
    // restored data in which a child appears before its parent.
    versions: group.versions.toSorted((a, b) => a.depth - b.depth),
  }));
}

export type IdeaFoundation = "active" | "inactive" | "missing" | "unlinked";

/** Describe current references, not idea quality or confirmed user meaning. */
export function getIdeaFoundation(idea: ProductIdea, session: Session): IdeaFoundation {
  const images = new Set(session.images.map((image) => image.id));
  const hypotheses = new Map(session.hypotheses.map((item) => [item.id, item]));
  if (idea.image_ids.some((id) => !images.has(id)) ||
      idea.hypothesis_ids.some((id) => !hypotheses.has(id))) return "missing";
  if (idea.hypothesis_ids.some((id) =>
    hypotheses.get(id)!.image_ids.some((imageId) =>
      !images.has(imageId) || !idea.image_ids.includes(imageId)))) return "missing";
  if (idea.hypothesis_ids.some((id) =>
    !["proposed", "supported"].includes(hypotheses.get(id)!.status))) return "inactive";
  return idea.hypothesis_ids.length ? "active" : "unlinked";
}

export const foundationLabels: Record<IdeaFoundation, string> = {
  active: "Active foundation",
  inactive: "Needs review",
  missing: "Missing references",
  unlinked: "No linked interpretation",
};

/** Revision numbers are display labels within a group, not a linear history. */
export function versionLabel(group: IdeaVersionGroup, ideaId: string): string {
  const index = group.versions.findIndex((version) => version.idea.id === ideaId);
  if (index === 0 && group.issue === null) return "Original";
  return group.issue ? `Saved version ${index + 1}` : `Revision ${index}`;
}
