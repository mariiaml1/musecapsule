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

vi.mock("../src/api", async () => {
  const actual =
    await vi.importActual<typeof import("../src/api")>("../src/api");

  return {
    ...actual,
    createSession: vi.fn(),
    loadSession: vi.fn(),
    streamMessage: vi.fn(),
    streamIdeas: vi.fn(),
    streamBlueprint: vi.fn(),
    selectIdea: vi.fn(),
    reviseIdea: vi.fn(),
  };
});

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
  await screen.findByText(session.intent.goal, { selector: "strong" });
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
  it("offers reference ingestion before an idea is selected", async () => {
    await restore();
    navigate("Blueprint");

    fireEvent.click(screen.getByText("Add supporting material"));

    expect(
      screen.getByRole("region", { name: "Add reference material" }),
    ).toBeTruthy();
    expect(screen.getByLabelText("Reference title")).toBeTruthy();
    expect(screen.getByLabelText("Reference text")).toBeTruthy();

    expect(api.streamBlueprint).not.toHaveBeenCalled();
  });
  it.each(["missing", "empty", "cited"] as const)(
    "renders blueprint references for the %s case without generation",
    async (referenceState) => {
      const references =
        referenceState === "cited"
          ? [
              {
                document_id: "document-1",
                chunk_id: "chunk-1",
                quote: "Preserve the learner's position.",
              },
            ]
          : [];

      await restore({
        ...fixture,
        selected_idea_id: "idea-1",
        briefs: [
          {
            idea_id: "idea-1",
            idea_summary: "Saved blueprint with reference support",
            problem: "Losing context",
            audience: "Learners",
            core_scenario: "Save and reopen a passage",
            features: ["Save a bookmark"],
            constraints: [],
            risks: ["Passage locations may change"],
            acceptance_criteria: ["A bookmark can be reopened"],
            suggested_architecture: [],
            metaphor_origin: {
              image_ids: ["image-1"],
              hypothesis_ids: ["h1"],
              meaning_basis: "A possible interpretation",
              mechanic_mapping: "Note becomes artifact",
              user_confirmed: false,
            },
            ...(referenceState === "missing" ? {} : { references }),
          },
        ],
      });

      navigate("Blueprint");

      const section = screen.getByRole("region", {
        name: "Reference material",
      });

      if (referenceState === "cited") {
        expect(
          within(section).getByText("Preserve the learner's position."),
        ).toBeTruthy();

        fireEvent.click(within(section).getByText("Source identifiers"));

        expect(
          within(section).getByText("Document ID: document-1"),
        ).toBeTruthy();
        expect(within(section).getByText("Chunk ID: chunk-1")).toBeTruthy();
      } else {
        expect(
          within(section).getByText(
            "No reference material was cited in this blueprint.",
          ),
        ).toBeTruthy();
      }

      expect(api.streamBlueprint).not.toHaveBeenCalled();
    },
  );

  it("adds a revised idea without changing selection or building a blueprint", async () => {
    const session = structuredClone(fixture);
    session.selected_idea_id = "idea-1";

    await restore(session);
    navigate("Ideas");

    const revisedSession = structuredClone(session);
    revisedSession.revision += 1;
    revisedSession.ideas.push({
      ...session.ideas[0],
      id: "idea-2",
      title: "Revised idea capsule",
      previous_idea_id: "idea-1",
    });

    vi.mocked(api.reviseIdea).mockResolvedValue(revisedSession);

    fireEvent.click(
      screen.getByRole("button", { name: "Revise Idea capsule" }),
    );

    await screen.findByRole("heading", {
      name: "Revised idea capsule",
    });

    expect(api.reviseIdea).toHaveBeenCalledTimes(1);
    expect(api.reviseIdea).toHaveBeenCalledWith("session-1", "idea-1");
    expect(screen.getByText("Revised from: Idea capsule")).toBeTruthy();

    fireEvent.click(
      screen.getByRole("button", { name: "View Original: Idea capsule" }),
    );
    const originalHeading = screen.getByRole("heading", {
      name: "Idea capsule",
      exact: true,
    });
    const originalCard = originalHeading.closest("article");
    expect(originalCard).not.toBeNull();

    expect(
      within(originalCard!).getByRole("button", { name: "Selected ✓" }),
    ).toBeTruthy();

    expect(api.selectIdea).not.toHaveBeenCalled();
    expect(api.streamBlueprint).not.toHaveBeenCalled();
    expect(api.streamIdeas).not.toHaveBeenCalled();
  });

  it.each(["unsupported", "superseded", "missing"] as const)(
    "blocks blueprint generation for a %s foundation and preserves the saved brief",
    async (status) => {
      const session = structuredClone(fixture);
      session.selected_idea_id = "idea-1";

      if (status === "missing") {
        session.hypotheses = [];
      } else {
        session.hypotheses[0].status = status;
      }

      session.briefs = [
        {
          idea_id: "idea-1",
          idea_summary: "Previously saved blueprint",
          problem: "Losing ideas",
          audience: "Creators",
          core_scenario: "Store a note",
          features: ["Save a note"],
          constraints: ["Solo development"],
          risks: ["Interpretations may change"],
          acceptance_criteria: ["A saved note can be reopened"],
          suggested_architecture: [],
          metaphor_origin: {
            image_ids: ["image-1"],
            hypothesis_ids: ["h1"],
            meaning_basis: "A possible interpretation",
            mechanic_mapping: "Note becomes artifact",
            user_confirmed: false,
          },
        },
      ];

      await restore(session);
      navigate("Blueprint");

      const buildButton = screen.getByRole("button", {
        name: "Generate another blueprint",
      });

      expect(buildButton.hasAttribute("disabled")).toBe(true);
      expect(screen.getByText("Previously saved blueprint")).toBeTruthy();
      expect(
        screen.getByRole("status", {
          name: "Blueprint foundation warning",
        }).textContent,
      ).toContain("This idea has a missing or inactive interpretation.");

      fireEvent.click(buildButton);
      expect(api.streamBlueprint).not.toHaveBeenCalled();

      fireEvent.click(screen.getByRole("button", { name: "Review ideas" }));

      expect(
        screen.getByRole("heading", { name: "Ideas", exact: true }),
      ).toBeTruthy();
      expect(api.streamIdeas).not.toHaveBeenCalled();
    },
  );

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
    expect(screen.queryByText("Saving or loading your session…")).toBeNull();
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
    fireEvent.click(
      screen.getByRole("button", { name: "Choose this version" }),
    );
    await screen.findByRole("heading", { name: "Engineering Blueprint" });
    expect(api.selectIdea).toHaveBeenCalledWith("session-1", "idea-1");
    expect(api.streamBlueprint).not.toHaveBeenCalled();
    expect(screen.getByText("Revision 8")).toBeTruthy();
  });
  it("keeps failed selection in the ideas view", async () => {
    await restore();
    vi.mocked(api.selectIdea).mockRejectedValue(new Error("Selection failed"));
    fireEvent.click(
      screen.getByRole("button", { name: "Choose this version" }),
    );
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
    fireEvent.click(screen.getByRole("button", { name: "Continue →" }));
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
    expect(screen.queryByText("Exploring your scene…")).toBeNull();
    expect(
      screen
        .getByRole("button", { name: "Continue →" })
        .hasAttribute("disabled"),
    ).toBe(false);
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

  it("preserves the selected idea and narrative draft when revision fails", async () => {
    const session = structuredClone(fixture);
    session.selected_idea_id = "idea-1";

    await restore(session);
    navigate("Imagination");

    fireEvent.change(
      screen.getByLabelText("Your imagined scene or next detail"),
      { target: { value: "My unsent narrative detail" } },
    );

    navigate("Ideas");

    vi.mocked(api.reviseIdea).mockRejectedValue(
      new Error("Generation could not be completed."),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Revise Idea capsule" }),
    );

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Generation could not be completed.");

    await waitFor(() => {
      expect(
        screen
          .getByRole("button", { name: "Revise Idea capsule" })
          .hasAttribute("disabled"),
      ).toBe(false);
    });

    expect(screen.getByRole("button", { name: "Selected ✓" })).toBeTruthy();
    expect(screen.getByText("Revision 7")).toBeTruthy();
    expect(api.reviseIdea).toHaveBeenCalledTimes(1);
    expect(api.selectIdea).not.toHaveBeenCalled();
    expect(api.streamBlueprint).not.toHaveBeenCalled();

    navigate("Imagination");

    expect(
      (
        screen.getByLabelText(
          "Your imagined scene or next detail",
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("My unsent narrative detail");
  });

  it("reloads a revision conflict without retrying or losing the draft", async () => {
    const session = structuredClone(fixture);
    session.selected_idea_id = "idea-1";

    await restore(session);
    navigate("Imagination");

    fireEvent.change(
      screen.getByLabelText("Your imagined scene or next detail"),
      { target: { value: "My unsent clarification" } },
    );

    navigate("Ideas");

    const latest = structuredClone(session);
    latest.revision = 11;

    vi.mocked(api.loadSession).mockResolvedValue(latest);
    vi.mocked(api.reviseIdea).mockRejectedValue(
      new api.ApiError(409, "Session changed during processing."),
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Revise Idea capsule" }),
    );

    await screen.findByText("Revision 11");

    expect(screen.getByRole("alert").textContent).toContain(
      "Session changed during processing.",
    );
    expect(api.loadSession).toHaveBeenCalledTimes(2);
    expect(api.loadSession).toHaveBeenLastCalledWith("session-1");
    expect(api.reviseIdea).toHaveBeenCalledTimes(1);
    expect(api.selectIdea).not.toHaveBeenCalled();
    expect(api.streamBlueprint).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Selected ✓" })).toBeTruthy();

    await waitFor(() => {
      expect(
        screen
          .getByRole("button", { name: "Revise Idea capsule" })
          .hasAttribute("disabled"),
      ).toBe(false);
    });

    navigate("Imagination");

    expect(
      (
        screen.getByLabelText(
          "Your imagined scene or next detail",
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("My unsent clarification");
  });
  it("shows submitted text immediately and uses real node events until persistence is confirmed", async () => {
    await restore();
    navigate("Imagination");
    let node!: Parameters<typeof api.streamMessage>[2];
    let finish!: (value: Awaited<ReturnType<typeof api.streamMessage>>) => void;
    vi.mocked(api.streamMessage).mockImplementation((_id, _text, onNode) => {
      node = onNode;
      return new Promise((resolve) => {
        finish = resolve;
      });
    });
    fireEvent.change(
      screen.getByLabelText("Your imagined scene or next detail"),
      {
        target: { value: "The note starts to glow." },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: "Continue →" }));
    const exchange = screen.getByRole("region", {
      name: "Current exploration",
    });
    expect(
      within(exchange).getByText("The note starts to glow.", { selector: "p" }),
    ).toBeTruthy();
    expect(within(exchange).getByText(/Processing/)).toBeTruthy();
    expect(within(exchange).getByText("Exploring your scene…")).toBeTruthy();
    expect(within(exchange).queryByText("What happens next?")).toBeNull();
    expect(
      screen
        .getByRole("button", { name: "Continuing…" })
        .hasAttribute("disabled"),
    ).toBe(true);
    act(() =>
      node({ event: "node_started", data: { node: "explore_images" } }),
    );
    expect(
      within(exchange).getByText("Finding images in your words…"),
    ).toBeTruthy();
    act(() =>
      node({ event: "node_completed", data: { node: "explore_images" } }),
    );
    expect(screen.queryByText("Workflow result saved.")).toBeNull();
    expect(api.loadSession).toHaveBeenCalledTimes(1);
    vi.mocked(api.loadSession).mockResolvedValue({
      ...fixture,
      revision: 8,
      messages: [
        ...fixture.messages,
        { id: "m3", role: "user", text: "The note starts to glow." },
        { id: "m4", role: "assistant", text: "What changes around it?" },
      ],
    });
    await act(async () =>
      finish({
        event: "session_completed",
        data: { session_id: fixture.id, revision: 8 },
      }),
    );
    expect(screen.getByText("What changes around it?")).toBeTruthy();
    expect(screen.queryByText("Exploring your scene…")).toBeNull();
    expect(screen.getByText("Workflow result saved.")).toBeTruthy();
    expect(
      (
        screen.getByLabelText(
          "Your imagined scene or next detail",
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("");
    expect(api.streamMessage).toHaveBeenCalledExactlyOnceWith(
      fixture.id,
      "The note starts to glow.",
      expect.any(Function),
    );
  });

  it("does not label idea generation as exploration of an unsent draft", async () => {
    await restore();
    navigate("Imagination");
    let finish!: (value: Awaited<ReturnType<typeof api.streamIdeas>>) => void;
    vi.mocked(api.streamIdeas).mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    fireEvent.change(
      screen.getByLabelText("Your imagined scene or next detail"),
      {
        target: { value: "An unsent scene" },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: /Generate ideas/ }));
    expect(screen.queryByText("Exploring your scene…")).toBeNull();
    expect(screen.queryByRole("button", { name: "Continuing…" })).toBeNull();
    await act(async () =>
      finish({
        event: "run_failed",
        data: { code: "execution_failed", message: "Generation failed" },
      }),
    );
    expect(
      (
        screen.getByLabelText(
          "Your imagined scene or next detail",
        ) as HTMLTextAreaElement
      ).value,
    ).toBe("An unsent scene");
  });
});
