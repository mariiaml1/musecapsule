import type { Session } from "./types";
import { IdeaOrigin } from "./IdeaOrigin";
export function IdeasView({
  session,
  loading,
  onGenerate,
  onSelect,
  onBlueprint,
}: {
  session: Session;
  loading: boolean;
  onGenerate: () => void;
  onSelect: (id: string) => Promise<void>;
  onBlueprint: () => void;
}) {
  return (
    <section className="panel">
      <span className="eyebrow">POSSIBILITIES FROM YOUR IMAGINATION</span>
      <h2>Ideas</h2>
      <p className="muted">
        Explore different directions. You can return to your imagination at any
        time.
      </p>
      <div className="actions">
        <button
          onClick={onGenerate}
          disabled={loading || !session.images.length}
        >
          Generate ideas ✦
        </button>
        {session.selected_idea_id && (
          <button className="secondary" onClick={onBlueprint}>
            Open blueprint →
          </button>
        )}
      </div>
      {!session.images.length && (
        <p className="muted">Explore a scene first to extract its images.</p>
      )}
      <div className="idea-list">
        {" "}
        {session.ideas.map((idea) => {
          const selected = session.selected_idea_id === idea.id;

          return (
            <article
              key={idea.id}
              className={`idea-card ${selected ? "selected" : ""}`}
            >
              <h3>{idea.title}</h3>
              <p>{idea.description}</p>

              <p className="muted">{idea.goal_alignment}</p>

              <div className="idea-sources">
                {idea.image_ids.map((imageId) => {
                  const image = session.images.find(
                    (item) => item.id === imageId,
                  );

                  return image ? (
                    <span className="source-tag" key={imageId}>
                      {image.label}
                    </span>
                  ) : null;
                })}
              </div>
              <details>
                <summary>Metaphor provenance</summary>
                <IdeaOrigin idea={idea} session={session} />
              </details>
              <button
                className={selected ? "secondary" : ""}
                disabled={loading || selected}
                onClick={() => void onSelect(idea.id)}
              >
                {selected ? "Selected ✓" : "Choose this idea"}
              </button>
            </article>
          );
        })}
      </div>
      {!session.ideas.length && (
        <div className="empty-state">
          <p>Your ideas will appear here.</p>
        </div>
      )}
    </section>
  );
}
