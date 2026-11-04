import type { Session } from "./types";
import { IdeaOrigin } from "./IdeaOrigin";
import { ReferenceForm } from "./ReferenceForm";
import "./BlueprintView.css";

export function BlueprintView({
  session,
  loading,
  onBuild,
  onIdeas,
}: {
  session: Session;
  loading: boolean;
  onBuild: () => void;
  onIdeas: () => void;
}) {
  const selectedIdea = session.ideas.find(
    (idea) => idea.id === session.selected_idea_id,
  );
  const brief = session.briefs
    .filter((item) => item.idea_id === session.selected_idea_id)
    .at(-1);
  const foundationBlocked =
    selectedIdea?.hypothesis_ids.some((id) => {
      const hypothesis = session.hypotheses.find((item) => item.id === id);
      return (
        !hypothesis || !["proposed", "supported"].includes(hypothesis.status)
      );
    }) ?? false;
  const references = brief?.references ?? [];
  return (
    <section className="blueprint-workspace" aria-label="Blueprint workspace">
      <header className="bp-hero">
        <div>
          <span className="eyebrow">FROM IDEA TO IMPLEMENTATION</span>
          <h2>Engineering Blueprint</h2>
          <h3>{selectedIdea?.title ?? "Give your idea a plan."}</h3>
          <p className="bp-summary">
            {brief?.idea_summary ??
              selectedIdea?.description ??
              "Choose an idea to develop into an engineering plan."}
          </p>
          {brief && (
            <div className="bp-badges">
              <span>AI-proposed plan</span>
              <span>{brief.features.length} MVP features</span>
              <span>
                {brief.suggested_architecture.length} architecture components
              </span>
            </div>
          )}
        </div>
        <div className="bp-hero-actions">
          {selectedIdea ? (
            <button onClick={onBuild} disabled={loading || foundationBlocked}>
              {brief ? "Generate another blueprint" : "Build my idea ✦"}
            </button>
          ) : (
            <button onClick={onIdeas}>Explore ideas</button>
          )}
          {brief && (
            <p className="muted">
              A new generation keeps your saved blueprints.
            </p>
          )}
        </div>
      </header>
      {foundationBlocked && (
        <div
          className="bp-warning"
          role="status"
          aria-label="Blueprint foundation warning"
        >
          <p>
            This idea has a missing or inactive interpretation. Generate and
            select a new idea before building another blueprint. Previously
            saved blueprints remain available for review.
          </p>
          <button className="secondary" onClick={onIdeas} disabled={loading}>
            Review ideas
          </button>
        </div>
      )}
      <div className="bp-layout">
        <div className="bp-main">
          {brief ? (
            <>
              <section className="bp-card" aria-label="The experience">
                <span className="eyebrow">01 / THE EXPERIENCE</span>
                <h3>What you’re building</h3>
                <dl className="bp-experience">
                  <div>
                    <dt>Intended Audience</dt>
                    <dd>{brief.audience}</dd>
                  </div>
                  <div>
                    <dt>Problem</dt>
                    <dd>{brief.problem}</dd>
                  </div>
                  <div className="bp-scenario">
                    <dt>Core User Flow</dt>
                    <dd>{brief.core_scenario}</dd>
                  </div>
                </dl>
              </section>
              <section className="bp-card" aria-label="MVP scope">
                <span className="eyebrow">02 / MVP SCOPE</span>
                <h3>Start with the essentials</h3>
                <ol className="bp-features">
                  {brief.features.map((feature, index) => (
                    <li key={index}>
                      <span aria-hidden="true">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <p>{feature}</p>
                    </li>
                  ))}
                </ol>
              </section>
              <section className="bp-card" aria-label="Suggested Architecture">
                <span className="eyebrow">03 / SUGGESTED ARCHITECTURE</span>
                <h3>How it fits together</h3>
                <p className="muted">
                  Technical choices and assumptions require review before
                  implementation.
                </p>
                <div className="bp-components">
                  {brief.suggested_architecture.map((component, index) => (
                    <article className="bp-component" key={index}>
                      <span className="bp-component-number" aria-hidden="true">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <h4>{component.name}</h4>
                      <p>{component.responsibility}</p>
                      {component.suggested_technology && (
                        <p className="bp-technology">
                          {component.suggested_technology}
                        </p>
                      )}
                    </article>
                  ))}
                </div>
                {!brief.suggested_architecture.length && (
                  <p className="muted">No additional components proposed.</p>
                )}
              </section>
              <section className="bp-card" aria-label="Definition of Done">
                <span className="eyebrow">04 / DEFINITION OF DONE</span>
                <h3>What the MVP should demonstrate</h3>
                <p className="muted">
                  Proposed acceptance criteria for implementation.
                </p>
                <ul className="bp-criteria">
                  {brief.acceptance_criteria.map((criterion, index) => (
                    <li key={index}>{criterion}</li>
                  ))}
                </ul>
              </section>
            </>
          ) : (
            <div className="bp-card bp-empty">
              <span aria-hidden="true">✧</span>
              <h3>
                {selectedIdea
                  ? "Your next step, made concrete."
                  : "From possibility to a buildable idea."}
              </h3>
              <p className="muted">
                {selectedIdea
                  ? "Build a proposal with an MVP scope, suggested architecture, and acceptance criteria grounded in your selected idea."
                  : "Explore and select an idea first. You can already add supporting material for this session."}
              </p>
            </div>
          )}
        </div>
        <aside className="bp-sidebar" aria-label="Blueprint context">
          <section className="bp-card">
            <span className="eyebrow">YOUR INTENTION</span>
            <h3>Your north star</h3>
            <p>{session.intent.goal}</p>
            <h4>User Constraints</h4>
            {(brief?.constraints ?? session.intent.constraints).length ? (
              <ul>
                {(brief?.constraints ?? session.intent.constraints).map(
                  (constraint, index) => (
                    <li key={index}>{constraint}</li>
                  ),
                )}
              </ul>
            ) : (
              <p className="muted">No explicit constraints were provided.</p>
            )}
          </section>
          {selectedIdea && (
            <section className="bp-card">
              <span className="eyebrow">CREATIVE FOUNDATION</span>
              <h3>Rooted in your imagination</h3>
              <div className="bp-badges">
                {(
                  brief?.metaphor_origin.image_ids ?? selectedIdea.image_ids
                ).map((id) => (
                  <span key={id}>
                    {session.images.find((image) => image.id === id)?.label ??
                      "Image unavailable"}
                  </span>
                ))}
              </div>
              {brief && (
                <>
                  <h4>Metaphor Origin</h4>
                  <p>{brief.metaphor_origin.meaning_basis}</p>
                  <h4>How the metaphor becomes a product</h4>
                  <p>{brief.metaphor_origin.mechanic_mapping}</p>
                  <p className="bp-meaning-note">
                    {brief.metaphor_origin.user_confirmed
                      ? "Meaning confirmed by the user."
                      : "Meaning proposed by AI — not yet confirmed by the user."}
                  </p>
                  <details>
                    <summary>Blueprint source images &amp; hypotheses</summary>
                    <IdeaOrigin
                      idea={{ ...selectedIdea, ...brief.metaphor_origin }}
                      session={session}
                    />
                  </details>
                </>
              )}
              <details>
                <summary>Selected idea provenance</summary>
                <IdeaOrigin idea={selectedIdea} session={session} />
              </details>
            </section>
          )}
          <section className="bp-card" aria-label="Reference material">
            <span className="eyebrow">SUPPORTING MATERIAL</span>
            <h3>Reference material</h3>
            <p className="muted">
              Supporting material cited in this blueprint. Citations do not
              establish external verification.
            </p>
            <details className="bp-add-material">
              <summary>Add supporting material</summary>
              <ReferenceForm key={session.id} sessionId={session.id} />
            </details>
            {references.length ? (
              <ul className="bp-references">
                {references.map((reference, index) => (
                  <li key={`${reference.chunk_id}-${index}`}>
                    <span className="eyebrow">PASSAGE {index + 1}</span>
                    <blockquote>{reference.quote}</blockquote>
                    <details>
                      <summary>Source identifiers</summary>
                      <p>Document ID: {reference.document_id}</p>
                      <p>Chunk ID: {reference.chunk_id}</p>
                    </details>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">
                No reference material was cited in this blueprint.
              </p>
            )}
          </section>
          {brief && (
            <section className="bp-card bp-risks">
              <details open>
                <summary>Risks &amp; assumptions</summary>
                <ul>
                  {brief.risks.map((risk, index) => (
                    <li key={index}>{risk}</li>
                  ))}
                </ul>
              </details>
            </section>
          )}
        </aside>
      </div>
    </section>
  );
}
