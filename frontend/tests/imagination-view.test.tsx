import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { ImaginationView } from "../src/JourneyViews";
import type { Session } from "../src/types";

const session: Session = {
  id: "scene-1", revision: 5,
  intent: { goal: "Build a creative tool", constraints: [] },
  messages: [
    { id: "m1", role: "user", text: "A glass capsule floats." },
    { id: "m2", role: "assistant", text: "What is inside?" },
    { id: "m3", role: "user", text: "A golden note is inside." },
    { id: "m4", role: "assistant", text: "How does the note move?" },
  ],
  images: [{ id: "i1", label: "Golden note", evidence: [
    { message_id: "m3", quote: "A golden note" },
  ] }],
  hypotheses: [{ id: "h1", statement: "A possible precious result.",
    status: "unsupported", image_ids: ["i1"],
    evidence: [{ message_id: "m3", quote: "A golden note" }],
  }],
  hypothesis_history: [{
    previous: { id: "h1", statement: "A possible precious result.",
      status: "proposed", image_ids: ["i1"],
      evidence: [{ message_id: "m3", quote: "A golden note" }],
    },
    new_status: "unsupported", reason: "The user clarified the scene.",
    evidence: [{ message_id: "m3", quote: "A golden note" }], session_revision: 5,
  }],
  ideas: [], selected_idea_id: null, briefs: [],
};

let compact = false;
const mediaListeners = new Set<() => void>();
function resizeContext(isCompact: boolean) {
  act(() => { compact = isCompact; mediaListeners.forEach((notify) => notify()); });
}
beforeEach(() => {
  compact = false;
  vi.stubGlobal("matchMedia", () => ({
    matches: compact,
    addEventListener: (_event: string, notify: () => void) => mediaListeners.add(notify),
    removeEventListener: (_event: string, notify: () => void) => mediaListeners.delete(notify),
  }));
  // jsdom does not implement the browser's native dialog lifecycle.
  Object.defineProperty(HTMLDialogElement.prototype, "showModal", {
    configurable: true, value: function (this: HTMLDialogElement) { this.setAttribute("open", ""); },
  });
  Object.defineProperty(HTMLDialogElement.prototype, "close", {
    configurable: true, value: function (this: HTMLDialogElement) {
      this.removeAttribute("open"); this.dispatchEvent(new Event("close"));
    },
  });
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  mediaListeners.clear();
  Reflect.deleteProperty(HTMLDialogElement.prototype, "showModal");
  Reflect.deleteProperty(HTMLDialogElement.prototype, "close");
});

function setup(current = session) {
  const onSend = vi.fn();
  const onGenerate = vi.fn();
  render(<ImaginationView session={current} narrative="An unsent detail"
    onNarrative={vi.fn()} onSend={onSend} loading={false}
    onIdeas={vi.fn()} onGenerate={onGenerate} />);
  return { onSend, onGenerate };
}

it("focuses the latest exchange while retaining the complete saved conversation", () => {
  const before = structuredClone(session);
  const { onSend, onGenerate } = setup();
  expect(screen.getByText("How does the note move?")).toBeTruthy();
  expect(screen.queryByText("What is inside?")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /Conversation · 4/ }));
  const history = screen.getByRole("dialog", { name: "Conversation" });
  expect(within(history).getAllByRole("article").map((m) => m.querySelector("p")?.textContent))
    .toEqual(session.messages.map((m) => m.text));
  fireEvent.click(within(history).getByRole("button", { name: "Close conversation" }));
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(session).toEqual(before);
  expect(onSend).not.toHaveBeenCalled();
  expect(onGenerate).not.toHaveBeenCalled();
});

it("keeps source quotes, inactive meanings, and revision reasons accessible", () => {
  setup();
  const context = screen.getByRole("complementary", { name: "What we’ve discovered" });
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(within(context).getByRole("button", { name: /Golden note/ }).getAttribute("aria-pressed")).toBe("true");
  expect(within(context).getByText("No active meaning hypotheses.")).toBeTruthy();
  const previous = within(context).getByText(/Earlier interpretations/).closest("details")!;
  fireEvent.click(within(previous).getByText(/Earlier interpretations/));
  expect(within(previous).getByText("The user clarified the scene.")).toBeTruthy();
  expect(within(previous).getByText(/Revision 5 · proposed → unsupported/)).toBeTruthy();
  expect(within(previous).getAllByText("A golden note").length).toBeGreaterThan(0);
  fireEvent.click(within(context).getByRole("button", { name: "Close discoveries" }));
  expect(screen.queryByRole("complementary", { name: "What we’ve discovered" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /What we’ve discovered/ }));
  expect(screen.getByRole("complementary", { name: "What we’ve discovered" })).toBeTruthy();
});

it("does not present an older question as the answer to a new user message", () => {
  setup({ ...session, messages: session.messages.slice(0, 3) });
  const exchange = screen.getByRole("region", { name: "Current exploration" });
  expect(within(exchange).queryByText("What is inside?")).toBeNull();
  expect(within(exchange).getByText("A golden note is inside.")).toBeTruthy();
});

it("starts with an inviting empty state and allows ideas only after saved images exist", () => {
  setup({ ...session, messages: [], images: [], hypotheses: [], hypothesis_history: [] });
  expect(screen.getByText("What do you see in your imagination?")).toBeTruthy();
  expect(screen.getByRole("button", { name: /Generate ideas/ }).hasAttribute("disabled")).toBe(true);
});

it("switches image sources without changing the scene or generating new content", () => {
  const current = structuredClone(session);
  current.images.push({ id: "i2", label: "Capsule", evidence: [{ message_id: "m1", quote: "A glass capsule" }] });
  const before = structuredClone(current);
  const { onSend, onGenerate } = setup(current);
  const context = screen.getByRole("complementary", { name: "What we’ve discovered" });
  fireEvent.click(within(context).getByRole("button", { name: /Capsule/ }));
  expect(within(context).getByRole("button", { name: /Capsule/ }).getAttribute("aria-pressed")).toBe("true");
  const sources = within(context).getByLabelText("Sources for Capsule");
  expect(within(sources).getByText("A glass capsule", { exact: true })).toBeTruthy();
  expect(within(sources).getByText("A glass capsule floats.")).toBeTruthy();
  expect(current).toEqual(before);
  expect(onSend).not.toHaveBeenCalled();
  expect(onGenerate).not.toHaveBeenCalled();
});

it("uses a modal for compact screens and restores the sidebar when widened", () => {
  compact = true;
  setup();
  expect(screen.queryByRole("complementary", { name: "What we’ve discovered" })).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: /What we’ve discovered/ }));
  expect(screen.getByRole("dialog", { name: "What we’ve discovered" })).toBeTruthy();
  resizeContext(false);
  expect(screen.queryByRole("dialog")).toBeNull();
  expect(screen.getByRole("complementary", { name: "What we’ve discovered" })).toBeTruthy();
  expect(screen.getAllByRole("button", { name: /Golden note/ })).toHaveLength(1);
});
