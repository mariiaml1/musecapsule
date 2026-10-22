# MuseCapsule AI

Turn intent, constraints, and imagination into traceable product ideas.

MuseCapsule explores user-provided metaphors through an adaptive dialogue.
Product ideas remain connected to the original goal and the images that
inspired them.

## Implemented

- Validated intent and message models.
- Evidence references to exact fragments of user messages.
- Session state with revision tracking.
- Message updates that preserve the previous state.
- Duplicate message detection.
- Unit tests for models, evidence, and state updates.

## Planned

- Structured metaphor extraction using an LLM.
- Adaptive dialogue and hypothesis revision.
- Idea generation with evidence references.
- Similar-product search and MVP briefs.
- Session persistence and a minimal web interface.

## Local development

Requires Python 3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
