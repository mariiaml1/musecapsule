# Development Progress

Updated: 2026-10-25. Companion document: [ARCHITECTURE.md](ARCHITECTURE.md).

## Evidence and current checkpoint

Inspected GitHub repository: `mariiaml1/musecapsule`, master at `ee5d2b8809c0ec9ef0981003a4f7e5fbd4985f88` (`feat: track hypothesis status revisions with evidence`).
This documentation update changes no application code or tests. Tests were read, not executed during this documentation task.

The repository is behind the latest conversation. Do not assume chat examples have been committed or that the latest tests passed. The local Mac working tree was not accessible.

Current milestone: finish the Metaphor Explorer hypothesis proposal path, then demonstrate live image extraction followed by grounded hypotheses. There is no LangGraph workflow yet.

## Implemented in the inspected repository

- Python/Pydantic src-layout project with pytest and Ruff configuration.
- Intent, Message, EvidenceRef, ImageFragment, Hypothesis and HypothesisRevision.
- SessionState; message/image/hypothesis append operations; explicit status revision with previous-version history.
- Exact user-source validation.
- Image extraction response parsing and injectable `extract_images`.
- Local Electron/ChatGPT bridge, configurable model, raw response transport and error handling.
- CLI demo for one narrative, validated images and JSON state output.
- README setup instructions with a pinned external DevKit revision.

The author previously supplied successful live image-extraction output. Image boundaries varied (one combined image versus two objects); this is not a quality guarantee.

## Tests present in the repository

All test paths are under `src/musecapsule/tests/`.

| File | Coverage observed |
| --- | --- |
| test_models.py | Goal/constraint validation; message whitespace preservation and blank rejection; evidence quotes, IDs and user role; image labels/evidence; hypothesis default status, blank statement and required sources |
| test_state.py | Preserve previous state and increment revisions; reject duplicate messages/images/hypotheses; invalid/missing image evidence; missing hypothesis images and invalid quotes; reject non-proposed hypotheses; revision history and clarification evidence; invalid revision data and unchanged status |
| test_metaphor_explorer.py | Grounded image extraction, unique IDs, fabricated quote rejection, empty images, generation input, assistant rejection before generation |
| test_llm.py | Mocked subprocess timeout and nonzero process exit |

Evidence tests are in test_models.py; no separate test_evidence.py was found at the inspected path. These are deterministic tests, not LLM quality evaluations. No new test-pass count is claimed.

## Newer local work from the conversation

**User-shared code, absent from inspected master:**
- `parse_hypothesis_proposals` validates each image reference and each source quote, and creates application-owned Hypothesis IDs/statuses.
- Three proposal tests were shared: grounded result, fabricated quote, unknown image.
- Review corrections requested: keep the existing image valid in the fabricated-quote test; use one valid plus one unknown image ID to catch an incorrect any() check.
- The final shared parser still included redundant validation of existing image evidence; removal was requested.

**Assigned examples, completion not confirmed:**
- ProposedHypothesis and HypothesisProposalResponse contracts.
- `build_hypothesis_context` and its goal/source preservation test.
- `propose_hypotheses`, injected generation, empty-image shortcut and its test.
- `prompts/hypothesis_proposals.md`.
- `Field(max_length=3)` on the proposal response list.

Inspect the local files before adding or rewriting any of these.

## Known issues and verification gaps

1. **Committed defect:** in `append_image_fragment`, missing-message checking and `validate_evidence` are outside the evidence loop, so only the final reference is checked. Existing negative tests put invalid evidence last and do not expose an invalid-first/valid-last case. Fix separately; do not mark resolved without inspecting the local version.
2. README says the SDK's first model is used, but the committed bridge selects request.model. Correct documentation later.
3. Exact quotes and existing IDs do not prove that a hypothesis follows from its sources.
4. No persistence, complete dialogue loop, model-driven revision, search, graph, API or UI.
5. No retry policy, turn idempotency, atomic persistence or token/latency telemetry. Repeated LLM calls can create new IDs for equivalent results.
6. Source-checkout paths are assumed for prompts and bridge; packaged distribution is not established.

## Next concrete step

First reconcile the author's local changes with this baseline and resolve/verify the image-evidence loop defect with an invalid-first/valid-last regression test.

Then resume exactly at the paused feature: **wire hypothesis proposals into demo.py after image extraction**.

1. Confirm the proposal parser, context builder, wrapper and prompt exist locally and their tests pass.
2. Keep image and hypothesis prompts separate. Configure a hypothesis generation callable using the existing transport's instructions/model arguments.
3. Pass state.intent, state.images and state.messages to `propose_hypotheses`.
4. Apply returned hypotheses with `append_hypothesis`; print the resulting state.
5. Run deterministic tests, then one live demo. Check existing image/message IDs, exact quotes and proposed statuses. An empty hypothesis list is valid.
6. Review changes and commit the completed milestone; update these documents to remove uncertainty.

The extraction-specific transport name may be renamed when reused for proposals; this is a small naming change to discuss, not an already implemented adapter.

## Remaining MVP milestones

1. Complete and evaluate live hypothesis proposals and model-driven revisions.
2. Add Imagination Guide and a bounded LangGraph flow for an adaptive user turn.
3. Add Idea Evolution, selection and traceable idea contracts.
4. Add Reality Check with one bounded search tool, citations and honest unavailable handling; produce MVP brief.
5. Persist/reopen sessions in SQLite; expose FastAPI and minimal React/TypeScript UI.
6. Add error/step/tool budgets, safe observability, targeted integration tests and LLM evaluation.
7. Reproducible setup, Docker and GitHub Actions after the core scenario works.

MVP acceptance: create an intent/constraint session, explore images through one-question turns, revise interpretations after clarification, request 2–3 traceable ideas at any time, select one, produce a brief, save and resume. Search facts require sources; failed/unavailable search must be explicit.

Manual creative-quality rubric: goal relevance, diversity, metaphor linkage and feasibility. Use examples such as the scheduled feeder to evaluate revision; never hardcode their outcomes. Do not score objective genius or claim novelty/demand without evidence.

## Resume instructions for a new Work chat

- Communicate in Russian; code, comments and project documentation in English.
- Masha implements small iterations; explain the engineering reason, review her code, and avoid generating the entire project.
- Preserve the four-role LangGraph learning goal. No need to turn every LLM call into a separate agent.
- Read actual local/remote code before assuming that an assigned snippet is implemented.
- Keep tests in `src/musecapsule/tests/`; import `musecapsule`, never `src.musecapsule`.
- Follow README for installation. From the project root:
  `python -m pytest`
  and, separately, the live command
  `python -m musecapsule.demo --devkit-dir ../sign-in-with-chatgpt-devkit --model gpt-6.1-sol`.
- Live calls require the author's configured local connection and consume account allowance.
- The SHA `0a36fefeb913055c8c7a1a29b63d82b96b2e841a` pins the external DevKit, not MuseCapsule.
- Keep secrets/private stories out of Git; remind the author to commit completed milestones.
