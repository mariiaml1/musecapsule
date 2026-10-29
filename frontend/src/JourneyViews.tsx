import type { Session } from "./types";
import { stages } from "./journey";
import type { Stage } from "./journey";
export function JourneyNav({
  stage,
  onNavigate,
  hasSession,
}: {
  stage: Stage;
  onNavigate: (stage: Stage) => void;
  hasSession: boolean;
}) {
  return (
    <nav className="journey-nav" aria-label="Creative journey">
      {stages.map((item, i) => (
        <button
          key={item}
          className={stage === item ? "current" : "secondary"}
          aria-current={stage === item ? "page" : undefined}
          disabled={!hasSession && item !== "intention"}
          onClick={() => onNavigate(item)}
        >
          <span>0{i + 1}</span>
          {item[0].toUpperCase() + item.slice(1)}
        </button>
      ))}
    </nav>
  );
}
export function GoalSummary({ session }: { session: Session }) {
  return (
    <aside className="goal-summary">
      <div>
        <span className="eyebrow">YOUR INTENTION</span>
        <strong>{session.intent.goal}</strong>
        <div className="idea-sources">
          {session.intent.constraints.map((c, i) => (
            <span className="source-tag" key={i}>
              {c}
            </span>
          ))}
        </div>
      </div>
      <details>
        <summary>Session details</summary>
        <p className="session-id">{session.id}</p>
        <p className="muted">Revision {session.revision}</p>
      </details>
    </aside>
  );
}
export function IntentionView({
  session,
  goal,
  constraints,
  onGoal,
  onConstraints,
  onCreate,
  loading,
  onContinue,
}: {
  session: Session | null;
  goal: string;
  constraints: string;
  onGoal: (s: string) => void;
  onConstraints: (s: string) => void;
  onCreate: () => void;
  loading: boolean;
  onContinue: () => void;
}) {
  return (
    <section className="panel intention">
      <span className="eyebrow">A PLACE TO BEGIN</span>
      <h2>What would you like to create?</h2>
      {session ? (
        <>
          <p>
            Your intention guides the exploration. Return to any stage as your
            ideas develop.
          </p>
          <button onClick={onContinue}>Continue imagining →</button>
        </>
      ) : (
        <>
          <p className="muted">
            Bring a goal. A spontaneous image can open an unexpected path.
          </p>
          <label htmlFor="goal">Your goal</label>
          <textarea
            id="goal"
            value={goal}
            onChange={(e) => onGoal(e.target.value)}
            rows={3}
            disabled={loading}
            placeholder="Build an unusual AI-agent portfolio project"
          />
          <label htmlFor="constraints">Constraints (one per line)</label>
          <textarea
            id="constraints"
            value={constraints}
            onChange={(e) => onConstraints(e.target.value)}
            rows={3}
            disabled={loading}
            placeholder={"Solo development\nSmall MVP"}
          />
          <button onClick={onCreate} disabled={loading}>
            Begin exploration ✦
          </button>
        </>
      )}
    </section>
  );
}
/** Display literal evidence separately from AI-proposed meanings. */
export function ExplorationSources({ session }: { session: Session }) {
  return (
    <aside className="panel sources">
      <span className="eyebrow">THREADS OF YOUR IMAGINATION</span>
      <h3>Images & meanings</h3>
      <p className="muted">
        Images come from your words. Meanings are AI interpretations, not user
        confirmation.
      </p>
      <h4>Extracted images</h4>
      {!session.images.length && (
        <p className="muted">Images will emerge as you describe your scene.</p>
      )}
      {session.images.map((image) => (
        <article className="source-item" key={image.id}>
          <strong>{image.label}</strong>
          {image.evidence.map((e, i) => (
            <blockquote key={i}>
              {e.quote}
              <details>
                <summary>Original narrative</summary>
                <p>
                  {session.messages.find((m) => m.id === e.message_id)?.text ??
                    "Source unavailable."}
                </p>
              </details>
            </blockquote>
          ))}
        </article>
      ))}
      <h4>AI-proposed meanings</h4>
      {!session.hypotheses.length && (
        <p className="muted">No meaning hypotheses yet.</p>
      )}
      {session.hypotheses.map((h) => (
        <article className="source-item" key={h.id}>
          <span className="source-tag">{h.status}</span>
          <p>{h.statement}</p>
          <p className="muted">
            {h.image_ids
              .map(
                (id) =>
                  session.images.find((i) => i.id === id)?.label ??
                  "Image unavailable",
              )
              .join(" · ")}
          </p>
          <details>
            <summary>Narrative evidence</summary>
            {h.evidence.map((e, i) => (
              <blockquote key={i}>{e.quote}</blockquote>
            ))}
          </details>
        </article>
      ))}
    </aside>
  );
}
export function ImaginationView({
  session,
  narrative,
  onNarrative,
  onSend,
  loading,
  onIdeas,
  onGenerate,
}: {
  session: Session;
  narrative: string;
  onNarrative: (s: string) => void;
  onSend: () => void;
  loading: boolean;
  onIdeas: () => void;
  onGenerate: () => void;
}) {
  return (
    <div className="imagination-layout">
      <section className="panel dialogue">
        <span className="eyebrow">LET YOUR MIND WANDER</span>
        <h2>Imagination</h2>
        <p className="muted">
          Describe a scene, follow a question, or explore an unexpected detail.
        </p>
        <div className="conversation" aria-label="Imagination dialogue">
          {!session.messages.length && (
            <div className="empty-state">
              <p>What do you see in your imagination?</p>
              <p className="muted">
                A place, an object, a movement — start anywhere.
              </p>
            </div>
          )}
          {session.messages.map((m) => (
            <article key={m.id} className={`chat-message ${m.role}`}>
              <span className="eyebrow">
                {m.role === "user" ? "YOU" : "IMAGINATION GUIDE"}
              </span>
              <p>{m.text}</p>
            </article>
          ))}
        </div>
        <label htmlFor="narrative">Your imagined scene or next detail</label>
        <textarea
          id="narrative"
          value={narrative}
          onChange={(e) => onNarrative(e.target.value)}
          rows={4}
          disabled={loading}
          placeholder="A golden note floats inside a transparent capsule…"
        />
        <div className="actions">
          <button onClick={onSend} disabled={loading || !narrative.trim()}>
            Explore imagination
          </button>
          <button
            className="secondary"
            onClick={onGenerate}
            disabled={loading || !session.images.length}
          >
            Generate ideas ✦
          </button>
          {!!session.ideas.length && (
            <button className="secondary" onClick={onIdeas}>
              View ideas →
            </button>
          )}
        </div>
        {!!session.images.length && (
          <p className="muted">
            Generate ideas from the saved exploration now. Answering the next
            question is optional. Unsent text is not included.
          </p>
        )}
      </section>
      <ExplorationSources session={session} />
    </div>
  );
}
