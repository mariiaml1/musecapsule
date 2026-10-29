import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import App from "../src/App";
import * as api from "../src/api";
import type { Session } from "../src/types";
vi.mock("../src/api");
// The graph's third-party canvas is covered by existing observed-transition tests.
vi.mock("../src/AgentFlow", () => ({
  AgentFlow: () => <div>Observed graph</div>,
}));
const fixture: Session = {
  id: "session-1",
  revision: 7,
  intent: { goal: "Build a creative tool", constraints: ["Solo development"] },
  messages: [
    { id: "m1", role: "user", text: "A note enters a capsule." },
    { id: "m2", role: "assistant", text: "What happens next?" },
  ],
  images: [
    {
      id: "image-1",
      label: "Note",
      evidence: [{ message_id: "m1", quote: "A note" }],
    },
  ],
  hypotheses: [
    {
      id: "h1",
      statement: "The note may represent an idea.",
      status: "proposed",
      image_ids: ["image-1"],
      evidence: [{ message_id: "m1", quote: "A note" }],
    },
  ],
  ideas: [
    {
      id: "idea-1",
      title: "Idea capsule",
      description: "Keep an idea for later.",
      goal_alignment: "A creative tool",
      image_ids: ["image-1"],
      hypothesis_ids: ["h1"],
    },
  ],
  selected_idea_id: null,
  briefs: [],
};
async function restore(session = fixture) {
  vi.mocked(api.loadSession).mockResolvedValue(structuredClone(session));
  render(<App />);
  fireEvent.change(screen.getByLabelText("Session ID"), {
    target: { value: session.id },
  });
  fireEvent.click(screen.getByRole("button", { name: "Open session" }));
  await screen.findByText(session.intent.goal);
}
function navigate(name: string) {
  fireEvent.click(
    within(screen.getByRole("navigation")).getByRole("button", {
      name: new RegExp(name),
    }),
  );
}
beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);

describe("creative journey", () => {
  it("creates a session then replaces the form with a goal summary", async () => {
    vi.mocked(api.createSession).mockResolvedValue({
      ...fixture,
      images: [],
      ideas: [],
      messages: [],
      hypotheses: [],
    });
    render(<App />);
    expect(
      within(screen.getByRole("navigation"))
        .getByRole("button", { name: /Imagination/ })
        .hasAttribute("disabled"),
    ).toBe(true);
    fireEvent.change(screen.getByLabelText("Your goal"), {
      target: { value: "Build a creative tool" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Begin exploration/ }));
    await screen.findByRole("heading", { name: "Imagination", exact: true });
    expect(screen.queryByLabelText("Your goal")).toBeNull();
    navigate("Intention");
    expect(
      screen.queryByRole("button", { name: /Begin exploration/ }),
    ).toBeNull();
    expect(api.createSession).toHaveBeenCalledTimes(1);
  });
  it("restores and navigates without generation or loss of draft or revision", async () => {
    await restore();
    navigate("Imagination");
    fireEvent.change(
      screen.getByLabelText("Your imagined scene or next detail"),
      { target: { value: "My unsent detail" } },
    );
    navigate("Blueprint");
    navigate("Intention");
    navigate("Ideas");
    navigate("Imagination");
    expect(
      (
        screen.getByLabelText(
          "Your imagined scene or next detail",
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("My unsent detail");
    expect(screen.getByText("Revision 7")).toBeTruthy();
    expect(screen.getByText("What happens next?")).toBeTruthy();
    expect(api.loadSession).toHaveBeenCalledTimes(1);
    expect(api.streamIdeas).not.toHaveBeenCalled();
    expect(api.streamMessage).not.toHaveBeenCalled();
    expect(api.streamBlueprint).not.toHaveBeenCalled();
  });
  it("selects an idea only after persistence succeeds, without building automatically", async () => {
    await restore();
    vi.mocked(api.selectIdea).mockResolvedValue({
      ...fixture,
      selected_idea_id: "idea-1",
      revision: 8,
    });
    fireEvent.click(screen.getByRole("button", { name: "Choose this idea" }));
    await screen.findByRole("heading", { name: "Engineering Blueprint" });
    expect(api.selectIdea).toHaveBeenCalledWith("session-1", "idea-1");
    expect(api.streamBlueprint).not.toHaveBeenCalled();
    expect(screen.getByText("Revision 8")).toBeTruthy();
  });
  it("keeps failed selection in the ideas view", async () => {
    await restore();
    vi.mocked(api.selectIdea).mockRejectedValue(new Error("Selection failed"));
    fireEvent.click(screen.getByRole("button", { name: "Choose this idea" }));
    await screen.findByRole("alert");
    expect(
      screen.getByRole("heading", { name: "Ideas", exact: true }),
    ).toBeTruthy();
  });
  it("restores the selected blueprint and its provenance without workflow calls", async () => {
    await restore({
      ...fixture,
      selected_idea_id: "idea-1",
      briefs: [
        {
          idea_id: "idea-1",
          idea_summary: "Saved blueprint",
          problem: "Losing ideas",
          audience: "Creators",
          core_scenario: "Store a note",
          features: [],
          constraints: [],
          risks: [],
          acceptance_criteria: [],
          suggested_architecture: [],
          metaphor_origin: {
            image_ids: ["image-1"],
            hypothesis_ids: ["h1"],
            meaning_basis: "A possible interpretation",
            mechanic_mapping: "Note becomes artifact",
            user_confirmed: false,
          },
        },
      ],
    });
    expect(screen.getByText("Saved blueprint")).toBeTruthy();
    expect(
      screen.getByText(
        "Meaning proposed by AI — not yet confirmed by the user.",
      ),
    ).toBeTruthy();
    expect(api.streamBlueprint).not.toHaveBeenCalled();
  });
  it("allows ideas without answering a pending question, and distinguishes nodes from saved completion", async () => {
    await restore();
    navigate("Imagination");
    let finish!: (result: Awaited<ReturnType<typeof api.streamIdeas>>) => void;
    vi.mocked(api.streamIdeas).mockImplementation((_id, onNode) => {
      onNode({ event: "node_started", data: { node: "create_ideas" } });
      onNode({ event: "node_completed", data: { node: "create_ideas" } });
      return new Promise((resolve) => {
        finish = resolve;
      });
    });
    fireEvent.click(screen.getByRole("button", { name: /Generate ideas/ }));
    expect(screen.getByText("Workflow in progress…")).toBeTruthy();
    expect(screen.queryByText("Workflow result saved.")).toBeNull();
    navigate("Ideas");
    expect(
      screen
        .getByRole("button", { name: /Generate ideas/ })
        .hasAttribute("disabled"),
    ).toBe(true);
    await act(async () =>
      finish({
        event: "session_completed",
        data: { session_id: "session-1", revision: 8 },
      }),
    );
    await screen.findByText("Workflow result saved.");
    expect(api.streamMessage).not.toHaveBeenCalled();
  });
  it("preserves draft and marks an interrupted exploration unconfirmed", async () => {
    await restore();
    navigate("Imagination");
    vi.mocked(api.streamMessage).mockRejectedValue(
      new Error("Connection interrupted"),
    );
    fireEvent.change(
      screen.getByLabelText("Your imagined scene or next detail"),
      { target: { value: "Another note" } },
    );
    fireEvent.click(
      screen.getByRole("button", { name: "Explore imagination" }),
    );
    await screen.findByText(
      "Result unconfirmed. Reopen the session before retrying.",
    );
    expect(screen.queryByText("Workflow result saved.")).toBeNull();
    expect(
      (
        screen.getByLabelText(
          "Your imagined scene or next detail",
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("Another note");
    expect(api.loadSession).toHaveBeenCalledTimes(1);
  });
  it("reloads a conflicting session and retains failed workflow status", async () => {
    await restore();
    navigate("Imagination");
    vi.mocked(api.loadSession).mockResolvedValue({ ...fixture, revision: 11 });
    vi.mocked(api.streamIdeas).mockResolvedValue({
      event: "run_failed",
      data: { code: "session_conflict", message: "Session changed" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Generate ideas/ }));
    await screen.findByText("Revision 11");
    expect(screen.getByText("Workflow failed.")).toBeTruthy();
  });
  it("keeps persistence confirmed when the follow-up read fails", async () => {
    await restore();
    vi.mocked(api.loadSession).mockRejectedValue(new Error("Read failed"));
    vi.mocked(api.streamIdeas).mockResolvedValue({
      event: "session_completed",
      data: { session_id: "session-1", revision: 8 },
    });
    fireEvent.click(screen.getByRole("button", { name: /Generate ideas/ }));
    await waitFor(() =>
      expect(screen.getByRole("alert").textContent).toMatch(
        /Ideas were saved, but reloading failed/,
      ),
    );
    expect(screen.getByText("Workflow result saved.")).toBeTruthy();
  });
});
