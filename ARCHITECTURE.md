# Architecture

Updated: 2026-11-04. Reviewed against master source, including the RAG/frontend checkpoint at `01d014ef71bc6bf7e41ce5fd4662f8ebbdeb6114`. Documentation-only review; no fresh test execution.

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
| agent_events.py | Sanitized SSE lifecycle events and final-save coordination |
| workflow.py | LangGraph nodes and deterministic command routing |
| llm.py | request_generation: synchronous transport, raw response and error handling |
| bridge/chatgpt.cjs (inside the Python package) | Electron/ChatGPT connection and encrypted credentials |
| search.py | Standalone bounded Tavily adapter |
| storage.py | SQLite JSON snapshots and optional optimistic revision checks |
| knowledge.py | Reference documents, exact character chunks and lexical baseline |
| embeddings.py | Optional shared local FastEmbed adapter and pre-inference token checks |
| retrieval.py | Validated vectors, cosine scoring and search of saved embeddings |
| knowledge_storage.py | Session/model-scoped reference storage and atomic document/index writes |
| knowledge_service.py | Chunk, embed and persist reference material |
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
| ProductIdea | UUID, title, description, goal_alignment, image_ids, hypothesis_ids and optional previous_idea_id for revisions |
| MetaphorOrigin | Source IDs, meaning_basis, mechanic_mapping, user_confirmed |
| MVPBrief | idea_id, idea_summary, metaphor_origin, problem, audience, core_scenario, up to five features, constraints, risks, acceptance_criteria, optional suggested_architecture (up to six components) and references (default empty) |
| ReferenceDocument / ReferenceChunk | Session-scoped source text and exact character fragments with document IDs and offsets |
| ReferenceCitation | Document ID, chunk ID and an exact quote from supplied reference context |
| EmbeddedChunk / SemanticMatch | Source fragment with stored vector/model identity, or a cosine-scored retrieval result |
| SimilarSolution / ExternalCheck | Provider result title/URL/snippet and not_run/completed/unavailable outcome |

Supported means supported by the narrative, not user-selected for implementation or externally proven. There is no explicit meaning-confirmation feature. Idea Architect assigns user_confirmed=False; selecting an idea does not confirm its interpretation.

SessionState stores ID, intent, messages, revision, images, hypotheses, hypothesis_history, ideas, selected_idea_id and briefs. Briefs are appended as versions; there are no per-version IDs, timestamps or source revision metadata yet. No external_checks or selected_meaning_ids fields exist.

Operations return new states, with revision per accepted operation rather than per dialogue turn. Same-idea selection is a no-op. Nested objects are not globally immutable; explicit constructors must preserve every field.

## Four-role flow

Metaphor Explorer validates extraction quotes and assigns application IDs. Hypothesis proposals validate source IDs and quotes. Revision proposals cite the incoming clarification, reject duplicate targets and invalid transitions, and preserve prior hypotheses in history.

Imagination Guide receives dialogue, images and hypotheses, including corrections. The schema enforces one nonblank question string; openness, lack of leading options and semantic correctness require evaluation.

Idea Evolution receives intent, dialogue, images and proposed/supported hypotheses. Every generated idea needs an existing or new meaning hypothesis. New proposals contain statement, image IDs and exact evidence; application code assigns IDs/statuses. IdeaGenerationResult returns ideas and new_hypotheses as one validated batch. Existing hypotheses contribute all their image references to the idea. One hypothesis can combine multiple images; multiple hypotheses can support one idea. ProductIdea still permits empty hypothesis_ids for legacy/direct construction. The workflow appends new hypotheses before their ideas and returns only the completed node result.

Idea Architect receives the selected idea, linked images/hypotheses, full dialogue and intent. Related inactive hypotheses remain contextual warnings but cannot be cited as foundations. The parser requires origins to exist and belong to the selected idea. Application code assigns idea_id, copies constraints from Intent and sets user_confirmed=False. The model cannot assign these fields in BlueprintResponse. A brief can be generated without external research. The parser requires exact set equality between the idea's image/hypothesis IDs and the returned origin, and rejects inactive foundations. Legacy ideas with no hypotheses remain compatible. suggested_architecture is an optional list of component names, responsibilities and provisional technology recommendations, not separate required services.

Idea revision is an explicit user-triggered operation. It appends a new idea linked by previous_idea_id, preserving the original and its saved briefs; it does not change selection or automatically build a blueprint. Missing/inactive foundations block new blueprint generation before retrieval or LLM inference. Previously saved ideas and briefs remain available with UI warnings.

Exact provenance checks do not prove semantic entailment, novelty, demand or feasibility. A later narrative event is not necessarily a correction of an earlier fact; semantic interpretation of that distinction still requires evaluation.

## LangGraph workflow

ExplorationState wraps SessionState and optional command, idea_id and incoming_message. Each invocation handles one command; the caller passes the returned session to subsequent invocations. SQLite persists completed domain snapshots outside LangGraph; no graph checkpointer is configured.

| Command | Route |
| --- | --- |
| explore (default) | Extract/add message and images; if no hypotheses, propose them; if any non-superseded hypotheses, revise them; otherwise skip to Guide |
| generate_ideas | Generate and append an idea batch; no Guide question |
| select_idea | Validate and record the user's selection; no generation |
| build_blueprint | Validate selection/foundation, optionally retrieve session references, generate and validate brief, append version |
| revise_idea | Generate and append a linked revised idea; retain selection and prior versions |

Exploration routes end after the Guide. Nodes may represent multiple tasks of one AI role; they are not separate autonomous agents. Existing hypotheses currently prevent generating additional hypotheses from later images on that turn.

## Search and operating limits

**Build My Idea** is the primary behavior: blueprint generation without mandatory web search. Optional local retrieval supplies supporting reference material when configured; it does not generate or replace the creative idea.
**Explore Existing Solutions** is planned as an explicit optional command. It may compare products, approaches or libraries; similar solutions must not automatically veto or replace the idea.

The existing Tavily adapter makes one basic HTTP search, requests at most three results, disables generated answers/raw content, uses a 20s timeout and no automatic retry. Missing keys and transport/provider/validation failures yield unavailable. Search snippets are attributed external text, not independently verified facts. Search is not wired to the graph or SessionState.

The local ChatGPT bridge uses explicit model selection and a separate DevKit checkout. Prompted JSON plus Pydantic validation is implemented; provider-enforced schemas are not. Inference/subprocess timeouts are 60/120s. The bridge no longer lists models before every request; the provider validates the explicitly configured model. Safe timing records cover connection stages, generation and total subprocess time. Credentials stay outside Git; TAVILY_API_KEY is read from the environment by the search demo.

## Optional reference retrieval

RAG is enabled only by MUSECAPSULE_RAG_ENABLED=1 in server.create_local_app.
FastEmbed 0.9.1 and tokenizers 0.23.3 are optional dependencies. Imports are
deferred until an embedding adapter is created, so the API can load without
these packages when RAG is disabled.

One MiniLM embedding model is loaded per application factory instance and
shared by ingestion, explicit search and blueprint retrieval. The adapter
returns 384-dimensional vectors and checks complete input token counts before
inference. It clones the tokenizer without truncation/padding and preserves
inference settings. The input budget is at most 256 tokens including special
tokens, or the tokenizer's smaller configured limit.

Ingestion preserves the original text and uses 1,000-character windows with
150-character overlap. These are character offsets, not token counts.
Chunks are embedded before entering the SQLite transaction. KnowledgeStore
atomically inserts the document and its validated embeddings, checking
ownership, model identity, vector dimensions/norms and exact source slices.
Failure rolls back the complete write. Reference data is stored in separate
tables in the session database, not in SessionState snapshots; ingestion does
not increment the session revision.

Search loads the current session/model's saved embeddings and embeds only the
query. Ranking is an in-memory linear cosine scan, not a vector database or
approximate nearest-neighbor index. The lexical baseline remains available
for evaluation; it is not a hybrid retrieval stage.

Within the existing build_blueprint node, an injected callback queries the
selected idea's title plus description with limit=3 and min_score=0.30.
Foundation validation runs before retrieval, and foreign-session chunks are
rejected before generation. Retrieval does not add another agent or run the
graph twice. No match is valid and permits generation without reference context.

Idea Architect receives retrieved chunk/document IDs and text alongside the
original metaphor, hypotheses, dialogue and intent. The prompt treats reference
text as untrusted data. Each returned citation must refer to a supplied chunk,
match its document ID, and quote an exact substring. Citations default to an
empty list for compatibility. Prompt instructions and structural validation
do not establish resistance to every prompt injection or semantic entailment.

The frontend accepts pasted title/text, reports saving/indexing, clears fields
after success and preserves the draft on failure. Saved briefs display quoted
reference text and expandable source identifiers separately from narrative
provenance. Ingestion does not automatically regenerate a brief.

Limitations: character chunking may exceed the token budget; long idea queries
can also fail instead of being automatically shortened. There is no token-aware
splitting, reranking, hybrid fusion, file upload, saved-document browser,
embedding-model revision pin or index migration policy. The 0.30 threshold was
explored on a tiny synthetic corpus, not independently calibrated. Session
scoping is not production authorization. Retrieved text reaches the ChatGPT
provider during blueprint generation even though embeddings are local.

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
| POST /sessions/{id}/briefs | New brief version; optional local reference retrieval |
| POST /sessions/{id}/ideas/{idea_id}/revisions | Append a revised idea while retaining the original and selection |
| POST /sessions/{id}/references | Body: title/text; atomically store document and embeddings; 201 |
| POST /sessions/{id}/references/search | Body: query, limit, min_score; session-scoped chunks and cosine scores |

api.create_app accepts a database path and optional processing callables for testing. server.create_local_app binds the actual graph. Missing processors yield 503. Preconditions such as missing selection yield 409; unknown resources yield 404; invalid request bodies yield 422. Generated-data/provider failures map to sanitized 502 responses. Storage failures are not comprehensively mapped yet. Reference handlers return 503 when RAG is not configured, oversized embedding inputs map to 422, and an empty search returns 200 with an empty list.

SQLite persistence is a completed-command checkpoint, not resumption within an interrupted model call. Repeated blueprint generation is a fresh proposal and can change technical details; it is not targeted editing of a previous brief.

## Streaming and frontend

POST /sessions/{id}/messages/stream, /ideas/stream and /briefs/stream coexist with the JSON endpoints. Preconditions are checked before starting the stream. server.py binds all three to the same compiled graph used by non-streaming handlers.

stream_graph_run executes graph.stream once with custom and updates modes. Node wrappers emit node_started before execution; updates produce node_completed. Public lifecycle payloads contain node names, not prompts or full state. After graph completion the API-owned callback saves the final session once with expected_revision. Only then does session_completed expose session_id and revision. run_failed distinguishes session_conflict from execution_failed. HTTP 200, node completion and stream EOF do not establish successful persistence. collect_agent_events remains a separate completion-only helper, not the HTTP streaming implementation.

React uses fetch POST streaming, UTF-8 decoding and an SSE frame buffer. It validates terminal events, handles interruption without automatic generation retries, and reloads the saved session after confirmed completion or a conflict. A failed follow-up read does not undo confirmed persistence.

The contextual journey is Intention, Imagination, Ideas and Blueprint; navigation does not run agents. Users can request ideas once saved images exist without answering every question. Selection is saved explicitly; blueprint generation remains a separate action. Source panels expose image quotes, hypotheses/statuses and proposed metaphor mechanics.

| Frontend file | Responsibility |
| --- | --- |
| App.tsx | Session state, API commands and request lifecycle |
| JourneyViews.tsx / journey.ts | Contextual navigation, intention and exploration views |
| IdeasView.tsx / BlueprintView.tsx | Saved ideas, selection and latest selected-idea brief |
| ReferenceForm.tsx | Pasted reference ingestion, pending/success/error state and draft preservation |
| IdeaOrigin.tsx | Source resolution, evidence and interpretation warnings |
| AgentActivity.tsx / AgentFlow.tsx | Collapsible real node activity and read-only React Flow diagram |
| api.ts / agent-events.ts | HTTP transport, POST stream consumption and event validation |
| flow-path.ts | Observed sequential transitions from lifecycle order |

Diagram topology is maintained manually to match backend nodes. Disconnected nodes represent separate commands. Events describe the current interaction; execution history is not persisted. Sequential transitions are inferred from observed order; parallel execution is not supported by this visualization.

## Connection and usage boundaries

Live application wiring in server.py and demo.py injects request_generation for extraction, hypothesis proposal/revision, questions, ideas and blueprints. Idea Architect and blueprint generation are the same task. The local SDK uses the connected ChatGPT profile's OAuth permission; there is no configured Platform API-key fallback. Credentials are encrypted outside the repository.

The inspected external DevKit version returns only text from streamResponse. MuseCapsule stores no token counts, remaining allowance or rate-limit metadata. Python currently collapses bridge errors into a generic RuntimeError, so subscription-limit codes do not reach the frontend. Timing logs are not usage/billing records. Exact account allowance must be checked in ChatGPT settings; do not infer it from call counts or latency.

## Planned, not implemented

GitHub Actions now runs backend tests, builds a wheel and checks installed prompt/bridge resources outside the checkout. Frontend CI runs Node/Vitest tests, TypeScript/Vite build and ESLint. Base backend CI installs .[dev], not .[rag]; it does not run live embedding inference. The published v0.1.0 demo is linked from README. These checks do not establish production readiness or live model quality.

Discussed, not committed scope: explicit meaning confirmation, targeted brief editing, optional research orchestration/storage, usage monitoring, total operation budgets, replay/idempotency protection and Docker. Do not build these automatically before the portfolio checkpoint. Optional local RAG is implemented as described above; no vector database is used. Fine-tuning, billing and an application-generation platform are outside the current MVP.

Historical image descriptions coexist; semantic correction is prompt-based. Origin validation protects references, not creative correctness. Brief versions have no timestamps/source revisions and are not automatically marked stale after later dialogue.
