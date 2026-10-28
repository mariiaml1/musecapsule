# Development Progress

Updated: 2026-10-29. Source baseline: `7cbfad7d122ab6fd60cf9d589634e5e56550f596` (master).
See [ARCHITECTURE.md](ARCHITECTURE.md). This update changes documentation only. Sources were inspected; no fresh tests were executed or pass count claimed.

## Current checkpoint

The local backend vertical scenario works through CLI and HTTP:
explicit goal/constraints → narrative exploration → revisable hypotheses → 2–3 ideas → user selection → metaphor-grounded blueprint with architecture recommendations → SQLite save/reopen.

The author reported passing tests and successful Swagger HTTP statuses. Supplied output showed new ideas appended, repeated selection remaining a no-op, and a second brief preserved alongside the first. The bunny example demonstrated two source images and two hypotheses retained through selection and brief. These are observed examples, not general quality guarantees.

## Completed

- Four AI roles: Metaphor Explorer, Imagination Guide, Idea Evolution, Idea Architect.
- Grounded extraction and hypothesis proposals/revisions with prior-version history.
- New hypotheses can be proposed with ideas; IDs/statuses are application-assigned.
- Existing hypotheses contribute their complete image sources; blueprint parsing preserves all linked image/hypothesis sets.
- Suggested architecture: optional component responsibility/technology proposals, up to six; features remain capped at five.
- Generic local ChatGPT bridge and injected generation functions.
- LangGraph commands: explore, generate_ideas, select_idea, build_blueprint.
- SQLite snapshots, latest-revision restoration and optional optimistic concurrency.
- Custom-goal CLI, session restoration, message continuation, ideas, selection and brief actions.
- FastAPI creation/read/message/idea/selection/brief routes; real graph wiring in server.py.
- Sanitized model/provider API errors and HTTP 409 for stale writes.
- Independent Tavily adapter and manual search demo; not a prerequisite or graph/API feature.

## Test coverage

Tests live in src/musecapsule/tests; external generation/network calls are substituted.

- Models/evidence/state: validation, exact quotes, prior-state preservation, revisions, batches, selection and brief versions.
- AI functions: response contracts, source IDs/quotes, inactive hypotheses, context/clarification transfer, proposed confirmation rejection and architecture transfer.
- Workflow: first turn, continuation of a restored session, command isolation and combined origin from Evolution through Architect.
- Storage: reopen, highest revision independent of insertion order, unknown ID, duplicate revision and stale update rejection.
- API: creation/read across app recreation, 404, invalid goal, message persistence/failure, competing update 409, idea preconditions/persistence, selection/no-op, brief precondition and two preserved versions.
- CLI: expected selection error and suppression of generation error details.
- Search/bridge: source mapping, missing-key guard, provider failure without retry, bridge timeout/process failure.

Automated provenance checks do not measure semantic quality. Manual rubric: goal relevance, diversity, metaphor linkage and feasibility; also evaluate one open non-leading question, correction handling and no invented user confirmation or external verification.

## Boundaries to preserve

Idea Architect helps realize the user's idea. Metaphors may shape mechanics rather than UI decoration. Build My Idea works without research. Explore Existing Solutions remains optional and explicitly requested; preserve the Tavily adapter.

supported is narrative support, not user confirmation. No selected_meaning_ids or confirmation operation exists; generated origins use user_confirmed=False. No external_checks collection is stored in SessionState.

Do not hardcode bunny, capsule or ChaosCat outputs. The scheduled-feeder example is an evaluation case, not another component to implement.

## Remaining limitations

- No frontend, auth, session-list API, graph checkpointer, streaming, background jobs or cancellation.
- Concurrent LLM requests can both run; API optimistic concurrency rejects stale saves, not duplicate cost. CLI does not yet supply expected_revision.
- No-op responses can be stale; idempotency/retries and uniform storage error mapping remain incomplete.
- SQLite snapshots restore completed operations only. No schema-migration/version compatibility policy yet.
- Explicit meaning confirmation and targeted brief editing are absent. Regeneration may change provisional engineering rules.
- Existing hypotheses route later exploration to revision instead of additional proposal generation on that turn; Evolution can introduce new hypotheses.
- Historical images are not merged or assigned current/obsolete status. Stored briefs are not automatically marked stale.
- Direct domain construction/state updates are less restrictive than LLM parsers in some source-validation paths.
- No comprehensive evaluation dataset, usage/latency telemetry, total session budgets, packaging, Docker or CI yet.
- Actual search-backed tool orchestration is still pending; do not claim it is demonstrated by the standalone adapter.

## Next concrete iteration

Build a minimal React + TypeScript client in frontend/:

1. Inspect current official Vite setup and Node requirements before installing.
2. Configure a development proxy to the local API.
3. Implement session creation and restore by ID, then dialogue.
4. Add ideas, explicit selection, and brief display filtered by selected idea.
5. Show source links/interpretations and version history without claiming confirmed meanings.
6. Disable overlapping UI mutations, handle loading/errors and reload after 409. Never silently retry model-generating requests.
7. Verify the existing backend tests and a small end-to-end user scenario.

No graph editor, 3D capsule, billing or collaboration in this iteration.

## Run and resume

Communicate in Russian; code, comments and docs in English. Masha implements small reviewable steps. Read actual files, review her work and remind commits at completed milestones. Imports use musecapsule, never src.musecapsule.

```bash
python -m pip install -e ".[dev]"
python -m pytest
export MUSECAPSULE_DEVKIT_DIR="../sign-in-with-chatgpt-devkit"
python -m uvicorn musecapsule.server:create_local_app --factory --reload
```

Swagger: http://127.0.0.1:8000/docs. Other optional server settings: MUSECAPSULE_MODEL and MUSECAPSULE_DATABASE. Default database: data/musecapsule.db; keep data/ ignored.

CLI: python -m musecapsule.demo --devkit-dir ../sign-in-with-chatgpt-devkit.
Use --goal and repeated --constraint for a custom session. Restored sessions use --session-id with one of --message, --generate-ideas, --select-idea or --build-blueprint; no action prints the saved state.

Search demo: python -m musecapsule.search_demo; TAVILY_API_KEY comes from the current environment. Never print/commit secrets. Live model calls consume account allowance.

The DevKit pin 0a36fefeb913055c8c7a1a29b63d82b96b2e841a belongs to the external DevKit. Python.org macOS installations may require Install Certificates.command; keep TLS verification enabled.

Update these documents after the next milestone. New chats should start from this checkpoint and actual repository code, not older architectural proposals.
