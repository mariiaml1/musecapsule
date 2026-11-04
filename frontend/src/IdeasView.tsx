import { useState } from "react";
import type { ProductIdea, Session } from "./types";
import { IdeaOrigin } from "./IdeaOrigin";
import {
  foundationLabels,
  getIdeaFoundation,
  groupIdeaVersions,
  versionLabel,
} from "./idea-versions";
import type { IdeaVersionGroup } from "./idea-versions";
import "./IdeasView.css";

function FoundationBadge({ idea, session }: { idea: ProductIdea; session: Session }) {
  const status = getIdeaFoundation(idea, session);
  return <span className={`foundation-badge foundation-${status}`}>{foundationLabels[status]}</span>;
}

/** Browse saved versions independently from the user's persisted selection. */
export function IdeasView({
  session, loading, onGenerate, onSelect, onBlueprint, onRevise,
}: {
  session: Session;
  loading: boolean;
  onGenerate: () => void;
  onSelect: (id: string) => Promise<void>;
  onBlueprint: () => void;
  onRevise: (id: string) => Promise<string | void>;
}) {
  const [viewedId, setViewedId] = useState<string | null>(session.selected_idea_id);
  const [comparing, setComparing] = useState(false);
  const groups = groupIdeaVersions(session.ideas);
  const viewed = session.ideas.find((idea) => idea.id === viewedId)
    ?? session.ideas.find((idea) => idea.id === session.selected_idea_id)
    ?? session.ideas[0];
  const group = groups.find((item) => item.versions.some((version) => version.idea.id === viewed?.id));
  const selected = session.ideas.find((idea) => idea.id === session.selected_idea_id);
  const previous = session.ideas.find((idea) => idea.id === viewed?.previous_idea_id);
  const foundation = viewed ? getIdeaFoundation(viewed, session) : null;
  const brief = session.briefs.filter((item) => item.idea_id === viewed?.id).at(-1);
  const isSelected = viewed?.id === selected?.id;
  const previewQuotes = viewed ? [...new Map(
    viewed.image_ids.flatMap((id) => {
      const evidence = session.images.find((image) => image.id === id)?.evidence[0];
      return evidence ? [[`${evidence.message_id}:${evidence.quote}`, evidence] as const] : [];
    }),
  ).values()] : [];

  function view(ideaId: string) {
    setViewedId(ideaId);
    setComparing(false);
  }

  async function revise() {
    if (!viewed || loading) return;
    const newId = await onRevise(viewed.id);
    if (newId) view(newId);
  }

  function renderGroup(item: IdeaVersionGroup) {
    const expanded = item.id === group?.id;
    return (
      <li className="concept-group" key={item.id}>
        <button className={`concept-trigger ${expanded ? "is-viewed" : ""}`}
          aria-expanded={expanded}
          onClick={() => view(item.versions.find((version) => version.idea.id === selected?.id)?.idea.id ?? item.root.id)}>
          <span aria-hidden="true">{expanded ? "⌄" : "›"}</span>
          <span>{item.root.title}</span>
          <span className="version-count">{item.versions.length}</span>
        </button>
        {expanded && (
          <ul className="version-tree" aria-label={`Versions of ${item.root.title}`}>
            {item.versions.map(({ idea, depth }) => (
              <li key={idea.id}>
                <button className={`version-trigger ${viewed?.id === idea.id ? "is-viewed" : ""}`}
                  aria-current={viewed?.id === idea.id ? "true" : undefined}
                  aria-label={`View ${versionLabel(item, idea.id)}: ${idea.title}`}
                  onClick={() => view(idea.id)}>
                  <span className="version-dot" aria-hidden="true" />
                  <span className="version-copy">
                    <strong>{versionLabel(item, idea.id)}</strong>
                    {idea.previous_idea_id && <small>From {item.versions.some((v) => v.idea.id === idea.previous_idea_id)
                      ? versionLabel(item, idea.previous_idea_id) : "unavailable version"}</small>}
                    {depth > 1 && <small>{depth} steps from original</small>}
                  </span>
                  <FoundationBadge idea={idea} session={session} />
                  {idea.id === selected?.id && <span className="selected-marker">Chosen</span>}
                </button>
              </li>
            ))}
          </ul>
        )}
      </li>
    );
  }

  return (
    <section className="ideas-workspace" aria-labelledby="ideas-heading">
      <header className="ideas-heading">
        <div>
          <span className="eyebrow">POSSIBILITIES FROM YOUR IMAGINATION</span>
          <h2 id="ideas-heading">Ideas</h2>
          <p>Your ideas, evolving.</p>
          <span className="muted">Explore versions. Choose what to build.</span>
        </div>
        <div className="actions">
          <button onClick={onGenerate} disabled={loading || !session.images.length}>Generate ideas ✦</button>
          {selected && <button className="secondary" onClick={onBlueprint}>Open blueprint →</button>}
        </div>
      </header>

      {!viewed ? (
        <div className="panel empty-state">
          <span aria-hidden="true">✧</span>
          <h3>A new direction starts with an image.</h3>
          <p>{session.images.length ? "Your ideas will appear here. Generate ideas when you’re ready."
            : "Explore a scene first to extract its images."}</p>
        </div>
      ) : (
        <div className="ideas-layout">
          <aside className="panel concept-sidebar" aria-label="Concepts and versions">
            <div className="concept-sidebar-heading"><span className="eyebrow">CONCEPTS</span><span>{groups.length}</span></div>
            <ul className="concept-list">{groups.map(renderGroup)}</ul>
            <div className="selection-summary">
              <p>Viewing <strong>{group && versionLabel(group, viewed.id)}</strong></p>
              <p className="selection-saved">Selected for blueprint: <strong>{selected?.title ?? "None yet"}</strong></p>
              <small className="muted">Browsing does not change your selection.</small>
            </div>
          </aside>

          <article className="panel idea-detail" aria-label="Viewed idea">
            <header className="idea-detail-heading">
              <span className="eyebrow">{group && versionLabel(group, viewed.id)} · PRODUCT CONCEPT</span>
              <h3>{viewed.title}</h3>
              {viewed.previous_idea_id && <p className="muted">Revised from: {previous?.title ?? "Unavailable idea"}</p>}
              <div className="foundation-summary"><FoundationBadge idea={viewed} session={session} />
                <span className="muted">{foundation === "active"
                  ? "Linked interpretations are active; usefulness is unvalidated."
                  : foundation === "unlinked" ? "This saved idea has no linked meaning hypotheses."
                    : "Historical ideas remain available. Review the foundation before building."}</span>
              </div>
              {group?.issue && <p className="error" role="note">{group.issue === "cycle"
                ? "The saved version history contains a circular reference. This record is shown separately."
                : "An earlier version is unavailable. The available versions are still shown."}</p>}
            </header>

            <h4 className="trace-heading">Metaphor to mechanism</h4>
            <div className="meaning-trace">
              <section className="trace-card" aria-label="Source images">
                <span className="trace-step">01 · YOUR NARRATIVE</span><h5>Source images</h5>
                <div className="idea-sources">{viewed.image_ids.map((id) => {
                  const image = session.images.find((item) => item.id === id);
                  return <span className="source-tag" key={id}>{image?.label ?? "Image unavailable"}</span>;
                })}</div>
                {previewQuotes.map((source) => (
                  <blockquote key={`${source.message_id}:${source.quote}`}>{source.quote}</blockquote>
                ))}
              </section>
              <section className="trace-card" aria-label="AI interpretations">
                <span className="trace-step">02 · PROPOSED MEANING</span><h5>AI interpretations</h5>
                {!viewed.hypothesis_ids.length && <p className="muted">No linked interpretation.</p>}
                {viewed.hypothesis_ids.map((id) => {
                  const hypothesis = session.hypotheses.find((item) => item.id === id);
                  return <div className="trace-hypothesis" key={id}>
                    <p>{hypothesis?.statement ?? "Hypothesis unavailable."}</p>
                    {hypothesis && <span className="hypothesis-status">{hypothesis.status} · Not user-confirmed</span>}
                  </div>;
                })}
              </section>
              <section className="trace-card trace-product" aria-label="Product behavior">
                <span className="trace-step">03 · PRODUCT CONCEPT</span><h5>Product behavior</h5>
                <p>{brief?.metaphor_origin.mechanic_mapping ?? viewed.description}</p>
                {brief && <small className="muted">From this version’s saved blueprint.</small>}
              </section>
            </div>
            <div className="trace-footer">
              <span>{viewed.image_ids.length} source images · {viewed.hypothesis_ids.length} linked interpretations</span>
              <span>AI interpretations are proposals, not confirmed meanings.</span>
            </div>
            <details className="source-evidence"><summary>View source evidence</summary><IdeaOrigin idea={viewed} session={session} /></details>

            <section className="idea-alignment"><h4>How it serves your goal</h4><p>{viewed.goal_alignment}</p></section>
            {brief && <details><summary>Full product concept</summary><p className="concept-description">{viewed.description}</p></details>}

            {previous && <section className="version-comparison">
              <button className="comparison-toggle" aria-expanded={comparing} onClick={() => setComparing(!comparing)}>
                Compare with previous version <span aria-hidden="true">{comparing ? "−" : "+"}</span>
              </button>
              {comparing && <div className="comparison-columns">
                <div><h4>{previous.title}</h4><p>{previous.description}</p></div>
                <div><h4>{viewed.title}</h4><p>{viewed.description}</p></div>
                <p className="muted comparison-note">Saved descriptions shown verbatim. No automatic comparison or new generation.</p>
              </div>}
            </section>}

            <footer className="idea-detail-actions">
              <div className="actions">
                <button disabled={loading || isSelected} onClick={() => void onSelect(viewed.id)}>{isSelected ? "Selected ✓" : "Choose this version"}</button>
                <button className="secondary" disabled={loading} aria-label={`Revise ${viewed.title}`} onClick={() => void revise()}>Revise this idea</button>
                {isSelected && brief && <button className="secondary" onClick={onBlueprint}>View saved blueprint →</button>}
              </div>
              <p className="muted">Choosing a version does not generate a blueprint.</p>
            </footer>
          </article>
        </div>
      )}
    </section>
  );
}
