# Development Progress

Updated: 2026-11-04. Reviewed against master source, including RAG/frontend checkpoint `01d014ef71bc6bf7e41ce5fd4662f8ebbdeb6114`.
See [ARCHITECTURE.md](ARCHITECTURE.md). This is a documentation-only source review: tests were inspected, not executed, and no current pass count is claimed.

## Current checkpoint

The implemented local vertical scenario spans React, FastAPI, LangGraph and SQLite:
explicit intent → metaphor dialogue → revisable hypotheses → grounded ideas →
explicit selection → engineering blueprint → save and restore.

The frontend now uses contextual Intention, Imagination, Ideas and Blueprint views,
with collapsible Agent Activity, rather than a permanent three-column dashboard.
Optional local RAG now extends the blueprint stage with session-scoped reference
material and validated citations. References support engineering decisions;
they do not replace narrative evidence, user intent or the selected metaphor.

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
- Explicit idea revision with previous_idea_id, preserved history and unchanged selection.
- Preflight blocking of new blueprints with missing/inactive foundations; saved output remains reviewable.
- Optional FastEmbed/ONNX MiniLM embeddings, reused within one application instance.
- Exact character chunks, pre-inference token checks and saved 384-dimensional embeddings.
- Atomic SQLite document/index persistence, scoped by session and embedding model.
- Cosine retrieval over saved vectors; only the query is embedded at search time.
- Reference ingestion/search API and optional retrieval inside the existing blueprint node.
- Blueprint citations validated against supplied document/chunk IDs and exact quotes.
- Frontend pasted-reference form with pending/success/error states and draft preservation.
- Blueprint citation display with source identifiers, including empty/legacy reference handling.
- GitHub Actions backend/frontend checks and installed-wheel resource verification.
- Public v0.1.0 walkthrough video linked from README.

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
- RAG: chunk/source validation, vector checks, session/model isolation, token limits,
  index persistence and rollback, reference API behavior and supplied-context citations.
- RAG blueprint integration: real graph/API/SQLite with substituted embeddings and
  generation; JSON and SSE paths, one generation/final snapshot, preserved origins
  and persisted citations.

Frontend:
- Node tests cover SSE parsing, chunk boundaries, streaming API contracts and observed transitions.
- Vitest/React Testing Library tests cover contextual navigation, creation/restoration,
  explicit selection, no forced question answer, draft preservation, interruptions,
  conflicts and confirmed persistence despite a failed follow-up read.
- Reference API client tests cover request payloads and HTTP error preservation.
- Reference UI tests cover successful ingestion, draft retention on error, citation
  rendering, empty/legacy references and access before selecting an idea.
- UI tests mock API calls and graph rendering; they do not establish live LLM quality.

The author reports passing checks and CI at the recent implementation milestones.
This documentation update does not claim a fresh execution or an exact pass count.
Base CI installs .[dev]; optional-tokenizer checks may be skipped when the RAG
extra is absent. It does not validate real model downloads or ONNX inference.

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

## RAG evaluation checkpoint

The author supplied a local run of evals/retrieval_baseline.py:
three synthetic chunks and four relevant queries produced lexical Recall@1=0.50
and semantic Recall@1=1.00. Three unrelated queries returned no matches at
min_score=0.30. The examples informed the threshold, so these are development
observations, not held-out measurements or general retrieval-quality claims.

A manual saved-index check retrieved the Bounded retries source for a paraphrased
retry query and rejected an unrelated bread query. A subsequent blueprint run
included an exact quotation from synthetic contextual-learner-support notes,
preserved three image references and one proposed hypothesis, and retained
user_confirmed=false. The author confirmed save/restore and frontend citation
display, then successfully ingested another short reference via the UI.

These observations do not prove factual correctness or educational effectiveness.
The support notes were synthetic test material, not external validation.
The earlier generic generation failure was followed by a successful run after
a server restart; its exact cause was not established.

## Next small iteration

1. Review and sync the refreshed README, architecture and progress documentation.
2. Add a dedicated RAG manual-evaluation report if a durable evidence record is
   needed; distinguish synthetic sources from validated external material.
3. Expand retrieval evaluation with unseen relevant and irrelevant queries before
   changing the threshold or making broader quality claims.
4. Assess token-aware chunking and bounded query construction from actual
   over-limit examples; the current implementation explicitly rejects them.
5. Consider an optional CI job for the RAG dependencies and tokenizer contract.
   Keep live downloads/inference separate from deterministic unit tests.
6. Review the reference-form presentation and any need for a saved-document
   browser before expanding ingestion to files.
7. Review the remaining runtime/dev httpx2 pin discrepancy separately.

CI, wheel resource checks and the release walkthrough are implemented, not
pending initial setup. Earlier manual evaluation checklists retain their own
recorded status; later smoke tests do not retroactively complete them.
Keep implementation steps small and remind commit/push after logical milestones.

## Known limitations and deferred work

- Local setup; no hosted deployment, production auth, billing or collaboration.
- Prompted JSON validated in Python; no provider-enforced output schema.
- Routing is deterministic; model content is adaptive, not an autonomous supervisor.
- Later turns revise existing hypotheses instead of always proposing more;
  Idea Evolution can add hypotheses.
- Historical image descriptions coexist. The UI warns about inactive foundations;
  new generation is blocked, but historical briefs are not rewritten.
- No explicit meaning-confirmation operation, selected_meaning_ids or external_checks collection.
- No persisted execution history, graph checkpointer or guaranteed backend cancellation.
- Optimistic writes prevent overwrite, not duplicate concurrent generation cost.
  CLI saves omit expected_revision; no-op responses can be stale.
- No total run/session budgets, usage dashboard, comprehensive quality dataset,
  schema-migration policy or exhaustive cross-platform packaging validation.
- RAG uses character chunking, a fixed experimental threshold and linear scanning;
  no reranking, token-aware splitting, file upload or saved-document browser.
- Citation substring validation does not prove that a claim follows from its quote.
- Embedding model names are stored, but model revisions and migration policy are not pinned.
- Reference session isolation is not an authentication/authorization system.
- Retrieved passages are sent to ChatGPT; local embeddings do not make generation offline.
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
For RAG, install .[dev,rag] and start the server with MUSECAPSULE_RAG_ENABLED=1;
see README for the full setup. The first RAG startup may download the local model.
Default database: data/musecapsule.db; never commit local databases or credentials.

External DevKit pin: 0a36fefeb913055c8c7a1a29b63d82b96b2e841a.
This SHA belongs to the DevKit, not MuseCapsule. Live calls consume account allowance.
Follow README.md for its setup; tests require no live ChatGPT authorization.
