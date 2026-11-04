import { useState } from "react";
import type { EvidenceRef, Hypothesis, Session } from "./types";

/** Reveal exact source text without generating summaries or merging source IDs. */
function SourceQuotes({ evidence, session }: { evidence: EvidenceRef[]; session: Session }) {
  return evidence.map((source, index) => (
    <div className="context-quote" key={`${source.message_id}-${index}`}>
      <blockquote>{source.quote}</blockquote>
      <details>
        <summary>View original message</summary>
        <p>{session.messages.find((message) => message.id === source.message_id)?.text ?? "Source unavailable."}</p>
      </details>
    </div>
  ));
}

function MeaningCard({ hypothesis, session }: { hypothesis: Hypothesis; session: Session }) {
  return (
    <details className="meaning-card">
      <summary>
        <span className="meaning-statement">{hypothesis.statement}</span>
        <span className={`meaning-status ${hypothesis.status}`}>{hypothesis.status}</span>
      </summary>
      <p className="muted">An AI interpretation — not a user-confirmed meaning.</p>
      <div className="idea-sources">
        {hypothesis.image_ids.map((id) => (
          <span className="source-tag" key={id}>
            {session.images.find((image) => image.id === id)?.label ?? "Image unavailable"}
          </span>
        ))}
      </div>
      <details><summary>Why this interpretation? Source evidence</summary>
        <SourceQuotes evidence={hypothesis.evidence} session={session} />
      </details>
    </details>
  );
}

/** Present saved discoveries as image choices and expandable meaning proposals. */
export function CreativeContext({ session, onClose }: { session: Session; onClose: () => void }) {
  const [selectedImageId, setSelectedImageId] = useState<string | null>(null);
  const selectedImage = session.images.find((image) => image.id === selectedImageId) ?? session.images[0];
  const active = session.hypotheses.filter((h) => h.status === "proposed" || h.status === "supported");
  const inactive = session.hypotheses.filter((h) => h.status === "unsupported" || h.status === "superseded");
  const history = session.hypothesis_history ?? [];

  return (
    <div className="creative-context">
      <header className="drawer-heading">
        <div><h2>What we’ve discovered</h2>
          <p className="muted">Drawn from your scene. Meanings remain possibilities.</p></div>
        <button className="secondary" onClick={onClose} aria-label="Close discoveries">✕</button>
      </header>
      <section className="context-section" aria-label="Your images">
        <h3>Your images <span>· {session.images.length}</span></h3>
        {!selectedImage && <p className="muted">Images will emerge from your words.</p>}
        <div className="context-image-grid">
          {session.images.map((image, index) => (
            <button className="context-image-card" key={image.id}
              aria-pressed={image.id === selectedImage?.id}
              onClick={() => setSelectedImageId(image.id)}>
              <span className="image-mark" aria-hidden="true">✦</span>
              <span className="image-index">IMAGE {String(index + 1).padStart(2, "0")}</span>
              <strong>{image.label}</strong>
            </button>
          ))}
        </div>
        {selectedImage && <div className="selected-image-source" aria-label={`Sources for ${selectedImage.label}`}>
          <SourceQuotes evidence={selectedImage.evidence} session={session} />
        </div>}
      </section>
      <section className="context-section" aria-label="Possible meanings">
        <h3>Possible meanings <span>· {active.length}</span></h3>
        {!active.length && <p className="muted">No active meaning hypotheses.</p>}
        {active.map((hypothesis) => <MeaningCard key={hypothesis.id} hypothesis={hypothesis} session={session} />)}
      </section>
      <details className="context-earlier">
        <summary>Earlier interpretations · {inactive.length + history.length}</summary>
        <p className="muted">Inactive meanings and previous versions remain in the record, not an active foundation.</p>
        {inactive.map((hypothesis) => <MeaningCard key={hypothesis.id} hypothesis={hypothesis} session={session} />)}
        {!!history.length && <h4>Status changes</h4>}
        {history.map((entry, index) => (
          <details className="meaning-card" key={`${entry.previous.id}-${index}`}>
            <summary>Revision {entry.session_revision} · {entry.previous.status} → {entry.new_status}</summary>
            <p>{entry.previous.statement}</p><p>{entry.reason}</p>
            <SourceQuotes evidence={entry.evidence} session={session} />
          </details>
        ))}
      </details>
    </div>
  );
}
