# Development Progress

Updated: 2026-10-29. Reviewed against master repository tree `013409ed6150ace9ec1b511bf67e73ff45b79785`.
See [ARCHITECTURE.md](ARCHITECTURE.md). This is a documentation-only source review: tests were inspected, not executed, and no current pass count is claimed.

## Current checkpoint

The implemented local vertical scenario spans React, FastAPI, LangGraph and SQLite:
explicit intent → metaphor dialogue → revisable hypotheses → grounded ideas →
explicit selection → engineering blueprint → save and restore.

The frontend now uses contextual Intention, Imagination, Ideas and Blueprint views,
with collapsible Agent Activity, rather than a permanent three-column dashboard.
The next work is reproducibility and release preparation, not rebuilding the UI.

## Implemented

- Four roles: Metaphor Explorer, Imagination Guide, Idea Evolution and Idea Architect.
- Exact user-quote validation, application-assigned IDs and hypothesis revision history.
- Idea batches with existing/new hypotheses; meaningful multi-image foundations.
- Blueprint parsing preserves the selected idea's complete image/hypothesis ID sets,
  copies user constraints and assigns user_confirmed=false.
- Optional high-level architecture recommendations; at most five MVP features.
- LangGraph commands explore, generate_ideas, select_idea and build_blueprint.
- SQLite completed-session snapshots and optimistic API write checks.
- CLI custom goals, continuation, idea selection and blueprint actions.
- JSON API and real POST SSE endpoints for exploration, ideas and blueprints.
- One graph execution per streamed command; one final save; sanitized failures.
- React restoration, dialogue, idea cards, provenance and full blueprint display.
- Real node_started/node_completed visualization and observed sequential transitions.
- A separate bounded Tavily search adapter/demo; not integrated into the main workflow.
- Safe bridge timing logs and removal of repeated model discovery.

All live generators currently use the local ChatGPT sharing bridge. There is no
configured separately billed Platform API-key fallback. The SDK result and bridge
currently expose text only, not remaining quota or token usage.

## Automated checks present

Backend tests live in src/musecapsule/tests and substitute external generation/network:
- Models, evidence and state: invalid fields/references/quotes, prior-state preservation,
  hypothesis history, idea batches, selection/no-op and brief versions.
- AI functions: response validation, context transfer, inactive foundations,
  new hypotheses, multiple source preservation and application-controlled confirmation.
- Workflow: initial/restored exploration, separate commands, combined origin from
  Evolution through Architect, node start ordering and actual graph stream modes.
- Storage: reopen/latest revision, duplicate snapshots and optimistic conflicts.
- API: JSON behavior and SSE integration with SQLite; final-only persistence,
  no partial save on failure, stale-write protection, ideas and blueprint origins.
- Bridge/search/CLI: controlled failure paths, timeouts and bounded search behavior.

Frontend:
- Node tests cover SSE parsing, chunk boundaries, streaming API contracts and observed transitions.
- Vitest/React Testing Library tests cover contextual navigation, creation/restoration,
  explicit selection, no forced question answer, draft preservation, interruptions,
  conflicts and confirmed persistence despite a failed follow-up read.
- UI tests mock API calls and graph rendering; they do not establish live LLM quality.

The author previously reported successful checks; rerun them at the current commit
before claiming a release-ready result.

## Manual evaluations and performance observations

Committed reports:
- evals/feeder-clarification-2026-10-29.md: reported PASS for incorporating scheduled
  feeding, preserving history and avoiding a malfunction claim downstream.
  Follow-up: unsupported may conflate contradiction with resolved uncertainty.
- evals/multi-image-origin-2026-10-29.md: reported PASS for Failure Capsule,
  preserving three image and three hypothesis references and proposed mechanics.
  Its Session Restoration checklist is still blank; do not claim that manual check passed.

Both reports identify model gpt-6.1-sol and application commit
592ea94b418084fa4d085359dfd4663009550d76. They document inspected sessions,
not reliability across repeated generations. Rubric: goal relevance, diversity,
metaphor linkage and feasibility; reference validity alone cannot score creative quality.

Two author-supplied exploration timing runs totaled approximately 20.8s before
and 16.3s after removing repeated listModels calls. This is an observation, not a
benchmark. Three sequential generations remain the main measured delay.

## Next small iteration

1. Complete the existing manual restoration checklist with actual observations.
2. Follow the updated root README in a clean environment and run the checks below.
3. Inspect prompt inclusion and bridge path assumptions for installation outside an
   editable source checkout. Packaging is not yet verified.
4. Review why httpx2 is unpinned in runtime and pinned in dev; resolve from actual imports.
5. Add GitHub Actions using verified backend/frontend commands. No workflow is currently present.
6. Refresh stale frontend README statements and prepare a short portfolio walkthrough.

Keep iterations small. Fix actual failures before adding features. Remind commit/push
after completed milestones. A recorded demo or fixture-based preview is a release
option to assess, not an implemented feature.

## Known limitations and deferred work

- Local setup; no hosted deployment, production auth, billing or collaboration.
- Prompted JSON validated in Python; no provider-enforced output schema.
- Routing is deterministic; model content is adaptive, not an autonomous supervisor.
- Later turns revise existing hypotheses instead of always proposing more;
  Idea Evolution can add hypotheses.
- Historical image descriptions coexist; briefs are not automatically marked stale.
- No explicit meaning-confirmation operation, selected_meaning_ids or external_checks collection.
- No persisted execution history, graph checkpointer or guaranteed backend cancellation.
- Optimistic writes prevent overwrite, not duplicate concurrent generation cost.
  CLI saves omit expected_revision; no-op responses can be stale.
- No total run/session budgets, usage dashboard, comprehensive quality dataset,
  schema-migration policy or fully verified distribution packaging.
- SDK/provider usage-limit codes are currently hidden by generic bridge errors.
- Optional research command, targeted brief editing and Docker remain discussed work.
  Preserve the creative concept; do not expand scope automatically.

## Run and resume

Communicate in Russian; code, comments and documentation in English.
Read actual repository files first. Masha implements small reviewable steps.
Imports use musecapsule, never src.musecapsule. Do not claim execution on her Mac.

From the root, with Python 3.13 activated:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
export MUSECAPSULE_DEVKIT_DIR="../sign-in-with-chatgpt-devkit"
python -m uvicorn musecapsule.server:create_local_app --factory --reload
```

From frontend in another terminal (Node.js 24):

```bash
npm ci
npm run test:all
npm run build
npm run lint
npm run dev
```

Backend docs: http://127.0.0.1:8000/docs. Frontend: http://127.0.0.1:5173.
Optional settings: MUSECAPSULE_MODEL (default gpt-6.1-sol), MUSECAPSULE_DATABASE.
Default database: data/musecapsule.db; never commit local databases or credentials.

External DevKit pin: 0a36fefeb913055c8c7a1a29b63d82b96b2e841a.
This SHA belongs to the DevKit, not MuseCapsule. Live calls consume account allowance.
Follow README.md for its setup; tests require no live ChatGPT authorization.
