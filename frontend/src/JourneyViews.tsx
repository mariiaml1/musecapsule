import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { CreativeContext } from "./CreativeContext";
import type { AgentRunStatus } from "./agent-events";
import "./ImaginationView.css";
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
const compactContextQuery = "(max-width: 1000px)";
function subscribeToContextWidth(notify: () => void) {
  const media = window.matchMedia?.(compactContextQuery);
  media?.addEventListener("change", notify);
  return () => media?.removeEventListener("change", notify);
}
function isCompactContext() {
  return window.matchMedia?.(compactContextQuery).matches ?? false;
}

/** Keep the current exchange in focus without discarding saved conversation. */
export function ImaginationView({
  session, narrative, onNarrative, onSend, loading, onIdeas, onGenerate,
  pendingMessage = null, activeNode = null, runStatus = "idle",
}: {
  session: Session;
  narrative: string;
  onNarrative: (s: string) => void;
  onSend: () => void;
  loading: boolean;
  onIdeas: () => void;
  onGenerate: () => void;
  pendingMessage?: string | null;
  activeNode?: string | null;
  runStatus?: AgentRunStatus;
}) {
  const drawerRef = useRef<HTMLDialogElement>(null);
  const contextButtonRef = useRef<HTMLButtonElement>(null);
  const compactContext = useSyncExternalStore(subscribeToContextWidth, isCompactContext, () => true);
  const [contextOpen, setContextOpen] = useState(true);
  const [drawer, setDrawer] = useState<"context" | "history" | null>(null);
  useEffect(() => {
    const modalNeeded = drawer === "history" || (drawer === "context" && compactContext);
    if (modalNeeded && !drawerRef.current?.open) drawerRef.current?.showModal();
    if (!modalNeeded && drawerRef.current?.open) drawerRef.current.close();
  }, [drawer, compactContext]);
  const userIndex = session.messages.findLastIndex((m) => m.role === "user");
  const currentUser = session.messages[userIndex];
  const currentQuestion = session.messages.slice(userIndex + 1)
    .findLast((m) => m.role === "assistant");
  const stepLabels: Record<string, string> = {
    explore_images: "Finding images in your words…",
    explore_hypotheses: "Exploring possible meanings…",
    revise_hypotheses: "Reviewing interpretations…",
    ask_question: "Preparing your next question…",
  };
  const processing = pendingMessage !== null;


  return (
    <div className={`focused-imagination ${contextOpen && !compactContext ? "with-context" : ""}`}>
      <header className="imagination-heading">
        <div>
          <span className="eyebrow">ONE DETAIL CAN OPEN A NEW DIRECTION</span>
          <h2>Imagination</h2>
          <p className="muted">Follow your scene. There is no right answer.</p>
        </div>
        <button ref={contextButtonRef} className="secondary discovery-toggle"
          aria-haspopup={compactContext ? "dialog" : undefined}
          aria-expanded={compactContext ? drawer === "context" : contextOpen}
          aria-controls="creative-context-panel"
          onClick={() => {
            if (compactContext) { setContextOpen(true); setDrawer("context"); }
            else setContextOpen((open) => !open);
          }}>
          What we’ve discovered · {session.images.length + session.hypotheses.length}
        </button>
      </header>

      <div className="imagination-columns">
      <div className="imagination-main">
      <section className="panel imagination-scene" aria-label="Current exploration">
        <div className="scene-toolbar">
          <span className="eyebrow">YOUR IMAGINED WORLD</span>
          <button className="secondary conversation-toggle" aria-haspopup="dialog"
            onClick={() => setDrawer("history")}>
            Conversation · {session.messages.length} messages
          </button>
        </div>
        <div className="current-exchange" aria-busy={processing}>
          {(currentUser || processing) ? (
            <article className="scene-narrative">
              <span className="eyebrow">YOU {processing && "· Processing…"}</span>
              <p>{pendingMessage ?? currentUser?.text}</p>
            </article>
          ) : (
            <div className="scene-welcome">
              <span className="scene-symbol" aria-hidden="true">✦</span>
              <h3>What do you see in your imagination?</h3>
              <p className="muted">A place, an object, a movement. Start anywhere.</p>
            </div>
          )}
          {processing ? (
            <div className="guide-question processing-state" role="status" aria-live="polite">
              <span className="eyebrow">IMAGINATION GUIDE</span>
              <p><span className="processing-dot" aria-hidden="true" />
                {runStatus === "completed" ? "Exploration saved. Loading your question…" : "Exploring your scene…"}
              </p>
              <small className="muted">
                {runStatus === "completed" ? "Persistence confirmed." :
                  activeNode ? (stepLabels[activeNode] ?? `Working on ${activeNode}…`) :
                    "Waiting for the workflow result. Not yet confirmed saved."}
              </small>
            </div>
          ) : currentQuestion && (
            <article className="guide-question">
              <span className="eyebrow">IMAGINATION GUIDE</span>
              <p>{currentQuestion.text}</p>
            </article>
          )}
        </div>
        <form className="scene-composer" onSubmit={(event) => {
          event.preventDefault();
          if (!loading && narrative.trim()) onSend();
        }}>
          <label htmlFor="narrative">Your imagined scene or next detail</label>
          <textarea id="narrative" value={narrative}
            onChange={(e) => onNarrative(e.target.value)} rows={3} disabled={loading}
            placeholder={currentUser ? "What happens next in your scene?" : "A little bunny jumps across a field of glowing grass…"} />
          <div className="composer-footer">
            <span className="muted">Add a detail, answer the question, or change direction.</span>
            <button type="submit" disabled={loading || !narrative.trim()}>
              {processing ? "Continuing…" : "Continue →"}
            </button>
          </div>
        </form>
      </section>

      <section className="ideas-next" aria-label="Next creative step">
        <div><h3>Ready to see where this could lead?</h3>
          <p className="muted">Generate ideas from saved images whenever you’re ready.
            Answering the next question is optional. Unsent text is not included.</p></div>
        <div className="actions">
          <button className="secondary" onClick={onGenerate}
            disabled={loading || !session.images.length}>Generate ideas ✦</button>
          {!!session.ideas.length && <button className="secondary" onClick={onIdeas}>View ideas →</button>}
        </div>
      </section>

      </div>
      {contextOpen && !compactContext && (
        <aside id="creative-context-panel" className="context-sidebar panel" aria-label="What we’ve discovered">
          <CreativeContext session={session} onClose={() => {
            setContextOpen(false);
            contextButtonRef.current?.focus();
          }} />
        </aside>
      )}
      </div>

      <dialog ref={drawerRef} className="exploration-drawer"
        aria-label={drawer === "context" ? "What we’ve discovered" : "Conversation"}
        onClose={() => setDrawer(null)} onCancel={() => setDrawer(null)}>
        {drawer === "context" && compactContext && (
          <div id="creative-context-panel"><CreativeContext session={session}
            onClose={() => drawerRef.current?.close()} /></div>
        )}
        {drawer === "history" && <>
        <header className="drawer-heading"><div><span className="eyebrow">YOUR SAVED EXPLORATION</span>
          <h2 id="conversation-title">Conversation</h2></div>
          <button className="secondary" onClick={() => drawerRef.current?.close()}
            aria-label="Close conversation">✕</button></header>
        <p className="muted">The full conversation, in your original words.</p>
        {!session.messages.length && <p>No saved messages yet.</p>}
        {session.messages.map((m) => <article className={`chat-message ${m.role}`} key={m.id}>
          <span className="eyebrow">{m.role === "user" ? "YOU" : "IMAGINATION GUIDE"}</span><p>{m.text}</p>
        </article>)}
        </>}
      </dialog>
    </div>
  );
}
