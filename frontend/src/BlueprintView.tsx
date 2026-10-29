import type { Session } from "./types";
import { IdeaOrigin } from "./IdeaOrigin";
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
    (i) => i.id === session.selected_idea_id,
  );
  const selectedBrief = session.briefs
    .filter((b) => b.idea_id === session.selected_idea_id)
    .at(-1);
  return (
    <section className="panel blueprint-panel">
      <span className="eyebrow">FROM IDEA TO IMPLEMENTATION</span>
      <h2>Engineering Blueprint</h2>
      {!selectedIdea ? (
        <div className="empty-state">
          <p>Choose an idea to develop into an engineering plan.</p>
          <button onClick={onIdeas}>Explore ideas</button>
        </div>
      ) : (
        <>
          <h3>{selectedIdea.title}</h3>
          <p>{selectedIdea.description}</p>
          <button onClick={onBuild} disabled={loading}>
            {selectedBrief ? "Generate another blueprint" : "Build my idea ✦"}
          </button>
          <details>
            <summary>Selected idea provenance</summary>
            <IdeaOrigin idea={selectedIdea} session={session} />
          </details>
          {selectedBrief && (
            <div className="blueprint-content">
              <p className="muted">
                AI-proposed implementation plan. Technical choices and
                assumptions require review before implementation.
              </p>

              <h3>{selectedIdea.title}</h3>
              <p>{selectedBrief.idea_summary}</p>

              <h4>Problem</h4>
              <p>{selectedBrief.problem}</p>

              <h4>Intended Audience</h4>
              <p>{selectedBrief.audience}</p>

              <details>
                <summary>Blueprint source images &amp; hypotheses</summary>
                <IdeaOrigin
                  idea={{ ...selectedIdea, ...selectedBrief.metaphor_origin }}
                  session={session}
                />
              </details>
              <h4>Metaphor Origin</h4>
              <p>{selectedBrief.metaphor_origin.meaning_basis}</p>

              <h4>How the metaphor becomes a product</h4>
              <p>{selectedBrief.metaphor_origin.mechanic_mapping}</p>

              <h4>Core User Flow</h4>
              <p>{selectedBrief.core_scenario}</p>

              <h4>MVP Features</h4>
              <ul>
                {selectedBrief.features.map((feature, index) => (
                  <li key={index}>{feature}</li>
                ))}
              </ul>

              <h4>Suggested Architecture</h4>
              {selectedBrief.suggested_architecture.length ? (
                selectedBrief.suggested_architecture.map((component, index) => (
                  <div className="architecture-item" key={index}>
                    <strong>{component.name}</strong>
                    <p>{component.responsibility}</p>
                    {component.suggested_technology && (
                      <span className="muted">
                        {component.suggested_technology}
                      </span>
                    )}
                  </div>
                ))
              ) : (
                <p className="muted">No additional components proposed.</p>
              )}
              <h4>User Constraints</h4>
              {selectedBrief.constraints.length > 0 ? (
                <ul>
                  {selectedBrief.constraints.map((constraint, index) => (
                    <li key={index}>{constraint}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No explicit constraints were provided.</p>
              )}

              <h4>Risks</h4>
              <ul>
                {selectedBrief.risks.map((risk, index) => (
                  <li key={index}>{risk}</li>
                ))}
              </ul>
              <h4>Definition of Done</h4>
              <ul>
                {selectedBrief.acceptance_criteria.map((criterion, index) => (
                  <li key={index}>{criterion}</li>
                ))}
              </ul>

              <p className="muted">
                {selectedBrief.metaphor_origin.user_confirmed
                  ? "Meaning confirmed by the user."
                  : "Meaning proposed by AI — not yet confirmed by the user."}
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
