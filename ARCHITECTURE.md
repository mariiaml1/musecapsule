# Architecture

Snapshot: 2026-10-25. Repository baseline inspected: `ee5d2b8809c0ec9ef0981003a4f7e5fbd4985f88` (master).
Repository code is distinguished below from newer code shared in the development conversation. The author's local working tree was not inspected.

## Product and boundaries

MuseCapsule combines an explicit user goal and constraints with freely narrated images to develop traceable product ideas and an MVP brief. It does not discover hidden desires or assign objective psychological meanings to symbols.

Target flow: intent and constraints → narrative → adaptive exploration → 2–3 grounded ideas → selected idea → MVP brief. Dream Mode explores without premature critique; Reality Mode considers usefulness, constraints and similar solutions. The user can request ideas at any time. Ask one open, non-leading question per turn.

ChaosCat is a separate project. Its scheduled-feeder story is a possible revision/evaluation scenario, not a hardcoded output.

## Implemented repository components

Paths below are relative to `src/musecapsule/`, except the bridge.

| Component | Responsibility |
| --- | --- |
| `models.py` | Pydantic domain contracts; application-generated entity IDs |
| `evidence.py` | Validate message ID, user role and exact source substring |
| `state.py` | SessionState and explicit append/revision operations |
| `agents/metaphor_explorer.py` | Image response contracts, parsing and injectable generation |
| `prompts/metaphor_explorer.md` | Image extraction instructions |
| `llm.py` | Synchronous subprocess transport; return raw text or raise an error |
| `bridge/chatgpt.cjs` | Electron authorization, encrypted credentials and SDK inference |
| `demo.py` | Single-message CLI image extraction and state JSON output |
| `tests/` | Deterministic pytest checks, including mocked transport failures |

The demo currently calls transport and `parse_image_extraction` directly; `extract_images` exists but is not yet used by the committed demo.

## Data contracts

| Model | Main fields and meaning |
| --- | --- |
| Intent | goal, constraints; explicit user direction |
| Message | UUID, user/assistant role, original text |
| EvidenceRef | message_id, exact quote; no inferred meaning |
| ImageFragment | UUID, label, nonempty evidence; extracted narrative content |
| Hypothesis | UUID, statement, status, nonempty image_ids and evidence; tentative interpretation |
| HypothesisRevision | deep-copied previous hypothesis, new_status, reason, new evidence, session_revision |
| SessionState | UUID, intent, messages, images, hypotheses, hypothesis_history, revision |

Message text and source quotes preserve whitespace. Nonblank labels/statements are validated separately. Pydantic shape validation does not itself establish referential integrity.

Hypothesis statuses: proposed, supported, unsupported, superseded. New hypotheses are appended only as proposed. The implemented revision operation accepts supported/unsupported, rejects unchanged or superseded inputs, appends evidence, and records the previous version. No superseding operation exists yet. Supported means supported within the narrative, not externally established fact.

State functions return a new SessionState and increment revision per operation, not per dialogue turn. They preserve the incoming state during the operation, but shared nested objects are not globally immutable. Explicit constructors must carry every state field forward. See PROGRESS.md for the known image-evidence validation defect.

## Metaphor Explorer

Implemented image path:

1. `extract_images(message, *, generate)` rejects assistant input before generation.
2. `generate(message.text)` returns raw model text.
3. `parse_image_extraction(raw_response, message)` parses ImageExtractionResponse.
4. Each ExtractedImage supplies label and quote; Python validates the quote and assigns IDs and message references.
5. The caller applies returned ImageFragments through state operations.

ExtractedImage and ImageExtractionResponse forbid extra fields. Empty image lists are valid. Images are not merged by label.

### Newer conversation work, absent from the inspected commit

- User shared `parse_hypothesis_proposals(raw_response, *, images, messages)`: validates every proposed image ID and evidence reference before returning Hypothesis objects. IDs and proposed status come from Python.
- Latest shared parser still revalidated all input image evidence; removing that redundant loop was requested but not confirmed.
- ProposedHypothesis / HypothesisProposalResponse were supplied as contracts: statement, image_ids, evidence, wrapped in hypotheses. Their actual local definitions were not inspected.
- `build_hypothesis_context` was supplied: serialize intent, user messages and images with existing IDs.
- `propose_hypotheses(..., generate)`, an empty-image shortcut, `prompts/hypothesis_proposals.md`, and a maximum of three proposals were assigned most recently; implementation/test completion was not confirmed.

Intended proposal flow: validated session context → model proposal → reference/quote validation → explicit state update. Source objects come from the session, never from the model's claimed references.

## Integration decisions

- Keep domain rules, LLM decisions, transport and persistence separate so each can be tested independently.
- Inject `Callable[[str], str]` for generation. Prompts and connection configuration are composed by the caller.
- Use one local ChatGPT connection for this prototype, not a universal provider framework.
- The bridge receives JSON text/instructions/model via stdin; stdout contains the response, stderr diagnostics. Credentials are encrypted through Electron safeStorage outside the repository.
- The CLI requests an explicit model (default gpt-6.1-sol); bridge checks account availability. README's first-model statement is stale.
- Prompted JSON plus Pydantic validation is implemented; schema-constrained provider generation is not.
- Timeouts: model listing 30s, inference 60s, Python subprocess 120s. Automatic retries and workflow budgets are not implemented.
- Evidence proves source attribution, not semantic correctness of an interpretation. Semantic quality needs separate evaluation.

## Planned orchestration and components

LangGraph is a selected direction, not an installed dependency or implemented graph. Four AI roles remain the target:

| Role | Planned responsibility | Current status |
| --- | --- | --- |
| Imagination Guide | One open question; adaptive exploration | Not implemented |
| Metaphor Explorer | Extract images; propose/revise grounded hypotheses | Partial, as detailed above |
| Idea Evolution | 2–3 diverse ideas linked to intent and images | Not implemented |
| Reality Check | Limited search, feasibility and MVP brief | Not implemented |

A role may use multiple graph nodes. Graph nodes will call existing domain functions; graph routing controls order and allowed next actions. Model-selected questions/actions and bounded tool decisions supply agentic behavior; validation and persistence remain deterministic.

Discussed, not finalized: graph state wrapping SessionState plus a user command, next action and response; sequential processing of one user turn; atomic changes and duplicate-turn protection. Hypothesis history is product data and does not replace graph checkpoints.

Still planned: relation/action extraction, model-driven hypothesis revision, adaptive dialogue, idea/brief/tool-result contracts, search with sources and an explicit unavailable status, SQLite persistence, FastAPI, minimal React/TypeScript UI, observability, evaluation, Docker and CI.

Exclude from the first MVP: application generation, GitHub edits/PR automation as product features, fine-tuning, unnecessary RAG/vector databases, billing/full authentication/collaboration, complex 3D and graph editors.
