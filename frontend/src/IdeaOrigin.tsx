import type { ProductIdea, Session } from "./types";

interface IdeaOriginProps {
    idea: ProductIdea;
    session: Session;
}

/** Show an idea's narrative sources separately from AI interpretations. */
export function IdeaOrigin({ idea, session }: IdeaOriginProps) {
    return (
        <div className="idea-origin">
            <h4>Inspired by</h4>

            {idea.image_ids.map((imageId) => {
                const image = session.images.find(
                    (item) => item.id === imageId,
                );

                if (!image) {
                    return (
                        <p className="error" key={imageId}>
                            A linked image is unavailable.
                        </p>
                    );
                }

                return (
                    <div key={image.id}>
                        <strong>{image.label}</strong>

                        {image.evidence.map((source, index) => {
                            const message = session.messages.find(
                                (item) => item.id === source.message_id,
                            );

                            return (
                                <div key={`${source.message_id}-${index}`}>
                                    <blockquote className="origin-quote">
                                        {source.quote}
                                    </blockquote>

                                    <details>
                                        <summary>Original narrative</summary>
                                        <p className="origin-quote">
                                            {message?.text ?? "Source message unavailable."}
                                        </p>
                                    </details>
                                </div>
                            );
                        })}
                    </div>
                );
            })}

            <h4>AI meaning hypotheses</h4>
            <p className="muted">
                These interpretations are AI proposals, not user-confirmed meanings.
                Statuses reflect the current narrative evidence.
            </p>

            {idea.hypothesis_ids.length === 0 && (
                <p className="muted">
                    No meaning hypotheses are linked to this saved idea.
                </p>
            )}

            {idea.hypothesis_ids.map((hypothesisId) => {
                const hypothesis = session.hypotheses.find(
                    (item) => item.id === hypothesisId,
                );

                if (!hypothesis) {
                    return (
                        <p className="error" key={hypothesisId}>
                            A linked hypothesis is unavailable.
                        </p>
                    );
                }

                const inactive =
                    hypothesis.status === "unsupported" ||
                    hypothesis.status === "superseded";

                return (
                    <div key={hypothesis.id}>
                        <p>{hypothesis.statement}</p>
                        <p className="muted">
                            Current status: {hypothesis.status}
                        </p>

                        {inactive && (
                            <p className="error">
                                This interpretation is no longer an active foundation.
                                Review the idea before building on it.
                            </p>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
