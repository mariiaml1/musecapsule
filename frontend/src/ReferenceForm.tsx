import { useState } from "react";
import { createReference } from "./api";

export function ReferenceForm({ sessionId }: { sessionId: string }) {
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [savedTitle, setSavedTitle] = useState("");

  async function saveReference() {
    if (saving || !title.trim() || !text.trim()) return;

    setSaving(true);
    setError("");
    setSavedTitle("");

    try {
      const document = await createReference(sessionId, title, text);
      setSavedTitle(document.title);
      setTitle("");
      setText("");
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Reference material could not be saved.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section aria-label="Add reference material">
      <h3>Add reference material</h3>
      <p className="muted">
        Add notes to support future blueprints in this session. Relevant
        passages may be used; existing blueprints stay unchanged.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void saveReference();
        }}
      >
        <fieldset disabled={saving}>
          <legend>Reference details</legend>

          <label>
            Reference title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              required
            />
          </label>

          <label>
            Reference text
            <textarea
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={6}
              required
            />
          </label>

          <button
            type="submit"
            disabled={saving || !title.trim() || !text.trim()}
          >
            {saving ? "Saving and indexing…" : "Save reference"}
          </button>
        </fieldset>
      </form>

      {saving && <p role="status">Saving and indexing reference material…</p>}
      {savedTitle && (
        <p role="status">Reference saved and indexed: {savedTitle}</p>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
