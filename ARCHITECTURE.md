# Architecture

Updated: 2026-10-29. Code inspected at `7cbfad7d122ab6fd60cf9d589634e5e56550f596` on master. This is a source review, not a fresh test run.

## Product principles

MuseCapsule is an AI Imagination Engine:
user goal + constraints + spontaneous metaphors → image exploration → meaning hypotheses → product ideas → engineering blueprint.

The user supplies a conscious goal. Interpretations are creative proposals, not hidden desires or objective psychological meanings. A metaphor may become product behavior rather than literal visual styling. Preserve the selected idea instead of replacing it with a conventional SaaS concept or an internet result.

ChaosCat is a separate project and a useful evaluation example: scheduled feeding should undermine a broken-feeder assumption. Its output is not hardcoded.

## Components and boundaries

All Python paths below are relative to `src/musecapsule/`.

| Component | Responsibility |
| --- | --- |
| models.py | Pydantic domain models and validation |
| evidence.py | User-message identity, role and exact quote checks |
| state.py | Validated append, revision and selection operations |
| agents/metaphor_explorer.py | Extract images; propose hypotheses and status revisions |
| agents/imagination_guide.py | Generate one exploration question |
| agents/idea_evolution.py | Generate 2–3 ideas and validate sources |
| agents/idea_architect.py | Generate and validate a metaphor-grounded MVP brief |
| prompts/ | Separate task instructions |
| workflow.py | LangGraph nodes and deterministic command routing |
| llm.py | request_generation: synchronous transport, raw response and error handling |
| bridge/chatgpt.cjs (repository root) | Electron/ChatGPT connection and encrypted credentials |
| search.py | Standalone bounded Tavily adapter |
| storage.py | SQLite JSON snapshots and optional optimistic revision checks |
| api.py | HTTP contracts, injected processing, error mapping and persistence |
| server.py | Configure the real graph and local connection from environment |
| demo.py | Scripted demo, custom goals, restored-session CLI actions |
| search_demo.py | Independent manual search check |
| tests/ | Unit and workflow integration tests using substituted external generation |

Each AI function accepts a generation callable. Providers do not mutate domain state. Parsers validate model proposals; state operations apply accepted changes. LangGraph controls execution. Model decisions include hypotheses, their revisions and question content; command routing is currently deterministic, not a model-based supervisor.

## Domain contracts

| Model | Meaning |
| --- | --- |
| Intent | Explicit goal and optional user constraints |
| Message | UUID, role, original text |
| EvidenceRef | Message UUID and exact source substring |
| ImageFragment | Application UUID, label, nonempty evidence |
| Hypothesis | Interpretation, image/evidence references, proposed/supported/unsupported/superseded status |
| HypothesisRevision | Previous snapshot, new status, reason, evidence and session revision |
| ProductIdea | UUID, title, description, goal_alignment, image_ids and optional hypothesis_ids |
| MetaphorOrigin | Source IDs, meaning_basis, mechanic_mapping, user_confirmed |
| MVPBrief | idea_id, idea_summary, metaphor_origin, problem, audience, core_scenario, up to five features, constraints, risks, acceptance_criteria, optional suggested_architecture (up to six components) |
| SimilarSolution / ExternalCheck | Provider result title/URL/snippet and not_run/completed/unavailable outcome |

Supported means supported by the narrative, not user-selected for implementation or externally proven. There is no explicit meaning-confirmation feature. Idea Architect assigns user_confirmed=False; selecting an idea does not confirm its interpretation.

SessionState stores ID, intent, messages, revision, images, hypotheses, hypothesis_history, ideas, selected_idea_id and briefs. Briefs are appended as versions; there are no per-version IDs, timestamps or source revision metadata yet. No external_checks or selected_meaning_ids fields exist.

Operations return new states, with revision per accepted operation rather than per dialogue turn. Same-idea selection is a no-op. Nested objects are not globally immutable; explicit constructors must preserve every field.

## Four-role flow

Metaphor Explorer validates extraction quotes and assigns application IDs. Hypothesis proposals validate source IDs and quotes. Revision proposals cite the incoming clarification, reject duplicate targets and invalid transitions, and preserve prior hypotheses in history.

Imagination Guide receives dialogue, images and hypotheses, including corrections. The schema enforces one nonblank question string; openness, lack of leading options and semantic correctness require evaluation.

Idea Evolution receives intent, dialogue, images and proposed/supported hypotheses. Every generated idea needs an existing or new meaning hypothesis. New proposals contain statement, image IDs and exact evidence; application code assigns IDs/statuses. IdeaGenerationResult returns ideas and new_hypotheses as one validated batch. Existing hypotheses contribute all their image references to the idea. One hypothesis can combine multiple images; multiple hypotheses can support one idea. ProductIdea still permits empty hypothesis_ids for legacy/direct construction. The workflow appends new hypotheses before their ideas and returns only the completed node result.

Idea Architect receives the selected idea, linked images/hypotheses, full dialogue and intent. Related inactive hypotheses remain contextual warnings but cannot be cited as foundations. The parser requires origins to exist and belong to the selected idea. Application code assigns idea_id, copies constraints from Intent and sets user_confirmed=False. The model cannot assign these fields in BlueprintResponse. A brief can be generated without external research. The parser requires exact set equality between the idea's image/hypothesis IDs and the returned origin, and rejects inactive foundations. Legacy ideas with no hypotheses remain compatible. suggested_architecture is an optional list of component names, responsibilities and provisional technology recommendations, not separate required services.

Exact provenance checks do not prove semantic entailment, novelty, demand or feasibility.

## LangGraph workflow

ExplorationState wraps SessionState and optional command, idea_id and incoming_message. Each invocation handles one command; the caller passes the returned session to subsequent invocations. SQLite persists completed domain snapshots outside LangGraph; no graph checkpointer is configured.

| Command | Route |
| --- | --- |
| explore (default) | Extract/add message and images; if no hypotheses, propose them; if any non-superseded hypotheses, revise them; otherwise skip to Guide |
| generate_ideas | Generate and append an idea batch; no Guide question |
| select_idea | Validate and record the user's selection; no generation |
| build_blueprint | Validate selection, generate brief, append version; no search |

Exploration routes end after the Guide. Nodes may represent multiple tasks of one AI role; they are not separate autonomous agents. Existing hypotheses currently prevent generating additional hypotheses from later images on that turn.

## Search and operating limits

**Build My Idea** is the implemented primary behavior: blueprint generation without search.
**Explore Existing Solutions** is planned as an explicit optional command. It may compare products, approaches or libraries; similar solutions must not automatically veto or replace the idea.

The existing Tavily adapter makes one basic HTTP search, requests at most three results, disables generated answers/raw content, uses a 20s timeout and no automatic retry. Missing keys and transport/provider/validation failures yield unavailable. Search snippets are attributed external text, not independently verified facts. Search is not wired to the graph or SessionState.

The local ChatGPT bridge uses explicit model selection and a separate DevKit checkout. Prompted JSON plus Pydantic validation is implemented; provider-enforced schemas are not. Listing/inference/subprocess timeouts are 30/60/120s. Credentials stay outside Git; TAVILY_API_KEY is read from the environment by the search demo.

## Persistence and HTTP API

SessionStore stores full Pydantic JSON snapshots keyed by (session_id, revision). load returns the highest revision and revalidates it. save never overwrites an existing revision. Optional expected_revision is checked against the latest stored value in the same BEGIN IMMEDIATE transaction as insertion; the lock does not span LLM generation.

The API uses this optimistic check after processing. Concurrent stale results return 409 rather than overwriting newer data; duplicate parallel LLM work is still possible. A no-op skips storage and may return a stale loaded snapshot. CLI saves currently omit expected_revision.

| HTTP operation | Result |
| --- | --- |
| POST /sessions | Create from Intent, persist revision 0; 201 |
| GET /sessions/{id} | Latest saved session; 200 or 404 |
| POST /sessions/{id}/messages | Body: text; graph exploration and save |
| POST /sessions/{id}/ideas | New idea batch; no body or Guide question |
| POST /sessions/{id}/selection | Body: idea_id; deterministic selection |
| POST /sessions/{id}/briefs | New brief version for selected idea; no search |

api.create_app accepts a database path and optional processing callables for testing. server.create_local_app binds the actual graph. Missing processors yield 503. Preconditions such as missing selection yield 409; unknown resources yield 404; invalid request bodies yield 422. Generated-data/provider failures map to sanitized 502 responses. Storage failures are not comprehensively mapped yet.

SQLite persistence is a completed-command checkpoint, not resumption within an interrupted model call. Repeated blueprint generation is a fresh proposal and can change technical details; it is not targeted editing of a previous brief.

## Planned, not implemented

Next: minimal React/TypeScript UI consuming the existing API, including explicit loading/error states, no automatic retries for generating POST requests, and a reload path after 409.

Also pending: explicit meaning confirmation, user-directed brief editing, optional research command/storage/source attribution, broader evaluation, token/latency telemetry and total operation budgets, replay/idempotency protection, packaging, Docker and CI. No fine-tuning, unnecessary RAG/vector database, billing or application-generation platform is planned for this MVP.

Historical image descriptions coexist; semantic correction is prompt-based. Origin validation protects references, not creative correctness. Brief versions have no timestamps/source revisions and are not automatically marked stale after later dialogue.
