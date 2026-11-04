import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { createReference } from "../src/api";
import { ReferenceForm } from "../src/ReferenceForm";

vi.mock("../src/api", () => ({
  createReference: vi.fn(),
}));

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

function fillForm() {
  fireEvent.change(screen.getByLabelText("Reference title"), {
    target: { value: "Notes" },
  });
  fireEvent.change(screen.getByLabelText("Reference text"), {
    target: { value: "  Preserve passage context.  " },
  });
}

it("saves exact text and clears the form after success", async () => {
  vi.mocked(createReference).mockResolvedValue({
    id: "document-1",
    session_id: "session-1",
    title: "Notes",
    text: "  Preserve passage context.  ",
  });

  render(<ReferenceForm sessionId="session-1" />);
  fillForm();
  fireEvent.click(screen.getByRole("button", { name: "Save reference" }));

  await screen.findByText("Reference saved and indexed: Notes");

  expect(createReference).toHaveBeenCalledExactlyOnceWith(
    "session-1",
    "Notes",
    "  Preserve passage context.  ",
  );
  expect(
    (screen.getByLabelText("Reference text") as HTMLTextAreaElement).value,
  ).toBe("");
});

it("preserves the draft when saving fails", async () => {
  vi.mocked(createReference).mockRejectedValue(
    new Error("Reference processing is unavailable."),
  );

  render(<ReferenceForm sessionId="session-1" />);
  fillForm();
  fireEvent.click(screen.getByRole("button", { name: "Save reference" }));

  expect((await screen.findByRole("alert")).textContent).toContain(
    "Reference processing is unavailable.",
  );
  expect(
    (screen.getByLabelText("Reference title") as HTMLInputElement).value,
  ).toBe("Notes");
  expect(
    (screen.getByLabelText("Reference text") as HTMLTextAreaElement).value,
  ).toBe("  Preserve passage context.  ");
  expect(screen.queryByText(/Reference saved and indexed:/)).toBeNull();
});
