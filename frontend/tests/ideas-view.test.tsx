import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { IdeasView } from "../src/IdeasView";
import type { Session } from "../src/types";

afterEach(cleanup);

const session: Session = {
  id: "session-1", revision: 12,
  intent: { goal: "Help learners ask for help", constraints: ["Browser-based"] },
  messages: [{ id: "m1", role: "user", text: "A capsule contains a note." }],
  images: [{ id: "i1", label: "Capsule", evidence: [{ message_id: "m1", quote: "A capsule" }] }],
  hypotheses: [
    { id: "h-old", statement: "Visible work could inspire inspection.", status: "unsupported", image_ids: ["i1"], evidence: [{ message_id: "m1", quote: "A capsule" }] },
    { id: "h-new", statement: "A boundary could inspire contextual help.", status: "proposed", image_ids: ["i1"], evidence: [{ message_id: "m1", quote: "A capsule" }] },
  ],
  ideas: [
    { id: "a", title: "Question Window", description: "Deliver a recorded explanation.", goal_alignment: "Help with one difficulty.", image_ids: ["i1"], hypothesis_ids: ["h-old"] },
    { id: "b", previous_idea_id: "a", title: "Contextual Question Window", description: "Send a contextual written help request.", goal_alignment: "Reduce the effort of asking.", image_ids: ["i1"], hypothesis_ids: ["h-new"] },
    { id: "c", previous_idea_id: "a", title: "Another Direction", description: "Try a different mechanism.", goal_alignment: "Help learners.", image_ids: ["i1"], hypothesis_ids: ["h-new"] },
  ],
  selected_idea_id: "a", briefs: [],
};

function setup(value = session, loading = false) {
  const handlers = { onGenerate: vi.fn(), onSelect: vi.fn(async () => {}), onRevise: vi.fn(async () => {}), onBlueprint: vi.fn() };
  render(<IdeasView session={value} loading={loading} {...handlers} />);
  return handlers;
}

it("browses and compares branches without selecting or generating", () => {
  const before = structuredClone(session);
  const handlers = setup();
  fireEvent.click(screen.getByRole("button", { name: "View Revision 1: Contextual Question Window" }));
  const detail = screen.getByRole("article", { name: "Viewed idea" });
  expect(within(detail).getByRole("heading", { name: "Contextual Question Window" })).toBeTruthy();
  expect(within(detail).getByText("Active foundation")).toBeTruthy();
  expect(screen.getByText("Selected for blueprint:").textContent).toContain("Question Window");
  fireEvent.click(screen.getByRole("button", { name: /Compare with previous version/ }));
  expect(screen.getByText("Deliver a recorded explanation.")).toBeTruthy();
  expect(screen.getAllByText("Send a contextual written help request.").length).toBeGreaterThan(0);
  // Both revisions name Original as their parent, rather than implying B → C.
  expect(screen.getAllByText("From Original")).toHaveLength(2);
  expect(handlers.onSelect).not.toHaveBeenCalled();
  expect(handlers.onGenerate).not.toHaveBeenCalled();
  expect(handlers.onRevise).not.toHaveBeenCalled();
  expect(handlers.onBlueprint).not.toHaveBeenCalled();
  expect(session).toEqual(before);
});

it("only selects the viewed revision after an explicit choice", () => {
  const handlers = setup();
  fireEvent.click(screen.getByRole("button", { name: "View Revision 1: Contextual Question Window" }));
  fireEvent.click(screen.getByRole("button", { name: "Choose this version" }));
  expect(handlers.onSelect).toHaveBeenCalledExactlyOnceWith("b");
  expect(handlers.onBlueprint).not.toHaveBeenCalled();
});

it("keeps browsing available but blocks mutations while loading", () => {
  const handlers = setup(session, true);
  fireEvent.click(screen.getByRole("button", { name: "View Revision 1: Contextual Question Window" }));
  for (const name of ["Choose this version", "Revise Contextual Question Window", /Generate ideas/]) {
    const button = screen.getByRole("button", { name });
    expect(button.hasAttribute("disabled")).toBe(true);
    fireEvent.click(button);
  }
  expect(handlers.onSelect).not.toHaveBeenCalled();
  expect(handlers.onRevise).not.toHaveBeenCalled();
  expect(handlers.onGenerate).not.toHaveBeenCalled();
});

it("distinguishes missing and legacy unlinked foundations from active ones", () => {
  const value = structuredClone(session);
  value.ideas = [{ ...value.ideas[0], hypothesis_ids: [] }, { ...value.ideas[1], hypothesis_ids: ["missing"] }];
  setup(value);
  expect(within(screen.getByRole("article", { name: "Viewed idea" })).getByText("No linked interpretation")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "View Revision 1: Contextual Question Window" }));
  expect(within(screen.getByRole("article", { name: "Viewed idea" })).getByText("Missing references")).toBeTruthy();
  expect(screen.getByText("Hypothesis unavailable.")).toBeTruthy();
});
