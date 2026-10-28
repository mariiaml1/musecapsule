# Development Progress

Updated: 2026-10-28. Code baseline reviewed: `3ad26c9934f8c3887c2b670ba45f7a5cfdae7b41` (`feat: build metaphor-grounded MVP briefs with Idea Architect`).
See [ARCHITECTURE.md](ARCHITECTURE.md). This documentation update changes no code/tests. Tests were inspected, not rerun here; no pass count is claimed.

## Current checkpoint

The first CLI vertical slice across four AI roles is implemented:
narrative → grounded images → hypotheses → clarification/revision → ideas → explicit user selection → metaphor-grounded MVP brief.

The author supplied successful live output selecting Hidden Melody. Its brief preserved the opaque-capsule correction through a conceal-then-reveal learning mechanic, linked the selected idea and source images, copied user constraints and kept user_confirmed=False. Revision 14 was consistent with that particular run. This is one observed example, not proof of general quality.

The CLI still uses scripted narrative and clarification text. It is not yet a complete free-form application, and sessions do not survive process exit.

## Implemented

- Python 3.13 project with Pydantic, pytest, Ruff and LangGraph dependencies.
- Original-text/evidence preservation and exact quote validation.
- Image extraction, grounded hypotheses and model-proposed revisions with historical snapshots.
- Imagination Guide, product idea generation, deterministic idea selection.
- Idea Architect response contracts, origin validation and generation without search.
- MetaphorOrigin separates proposed meaning from mechanics and user confirmation.
- MVPBrief stores functional scope and observable readiness criteria; constraints may be empty.
- SessionState.briefs retains prior generated versions.
- LangGraph commands: explore, generate_ideas, select_idea, build_blueprint.
- Injected generation and generic request_generation transport through the local Electron bridge.
- Independent Tavily adapter, explicit search outcomes and standalone search demo.
- Author verified a real Tavily search after installing Python's macOS certificates.

## Tests present

Paths: `src/musecapsule/tests/`. External generation/network calls are substituted in automated tests.

| File | Coverage |
| --- | --- |
| test_models.py | Intent/message/evidence/image/hypothesis validation; brief list items; external-check outcomes; default unconfirmed meaning |
| test_state.py | Append operations, source checks, previous-state preservation, hypothesis revision history; idea batches; idea selection/no-op; blueprint version preservation |
| test_metaphor_explorer.py | Grounded extraction/proposals, fabricated quotes, unknown image, context, role validation and revision parsing |
| test_imagination_guide.py | Blank question rejection |
| test_idea_evolution.py | Idea count, grounded parsing, inactive hypothesis rejection, missing-image generation guard |
| test_idea_architect.py | Reject model-assigned confirmation; reject unrelated origin; preserve intent/origin; pass clarification context |
| test_workflow.py | Initial step order; revision turn; ideas without exploration; selection without generation; brief for selected idea |
| test_search.py | Missing key without network; results with sources and request limits; HTTP failure without retry |
| test_llm.py | Mocked bridge timeout and process failure |

These tests do not establish creative quality. Manual rubric: goal relevance, diversity, metaphor linkage and feasibility. Additional checks: one open non-leading question, chronology respected, no invented user preferences or external verification.

The proposed different-idea blueprint rejection test was not found in the inspected test_state.py. Do not describe it as implemented.

## Accepted direction

The fourth role is **Idea Architect**, replacing Reality Check as the product-level description. It helps implement the user's chosen idea rather than replacing it with an internet result.

- Build My Idea is the primary path and needs no Tavily call.
- Explore Existing Solutions will be optional, explicitly requested and bounded.
- Metaphors can shape mechanics rather than visual decoration.
- Narrative support status is separate from user confirmation.
- Ideas with no hypothesis references remain valid; their proposed meaning is unconfirmed.
- Do not require selected_meaning_ids before creating a draft. That earlier proposal was not implemented.
- Keep the existing search adapter. Do not create artificial tool calls merely to label the system agentic.

## Remaining limitations

- No suggested_architecture contract yet: the output is a functional MVP brief, not a detailed technical architecture.
- No explicit meaning confirmation, edited-brief command, persistent sessions, checkpointer, API or UI.
- No graph research command, stored external checks or research block in briefs.
- Historical image descriptions coexist; no entity merging or current-image status. Later messages must override earlier properties in prompts.
- Existing hypotheses route subsequent exploration to revision, not additional hypothesis generation.
- append_blueprint checks selection and constraints; detailed origin integrity is enforced by the parser, not all direct state-operation calls.
- References and exact quotes cannot validate semantic reasoning.
- Numeric acceptance thresholds generated by the model are provisional recommendations, not proven requirements. Explicit labeling was discussed but not implemented.
- Versions lack timestamps/source revisions; stored briefs are not automatically marked stale after later corrections.
- No retry/idempotency/turn-atomicity policy or token/latency telemetry. Source-checkout prompt/bridge packaging remains a limitation.
- workflow.py registers build_blueprint → END twice; redundant, not two executions. No explicit ask_question → END edge is present. Review graph structure separately; this documentation task does not alter it.
- Earlier append_image_fragment evidence-loop indentation defect is fixed in the inspected code.

## Next concrete iteration

**Add optional high-level architecture components to MVPBrief and BlueprintResponse.**

1. Define a small component contract: name, responsibility, optional technology recommendation.
2. Allow an empty architecture list when a technical decomposition is not useful.
3. Pass validated components through parse_blueprint_response.
4. Update the Architect prompt: preserve the selected mechanics; keep technology suggestions provisional; do not invent verified versions or user constraints.
5. Add targeted parser/contract tests and run the suite. A new live call is useful only to assess the added output.
6. Review and commit the completed change.

Then prioritize SQLite save/reopen and a real input loop/API before expanding the product. Optional research remains a separate later feature, not a prerequisite for blueprints.

## Working agreement and commands

Communicate in Russian; code, comments and docs in English. Masha implements small steps; explain purpose, review changes and commit completed milestones. Inspect actual code before assuming suggested snippets exist. No full repository generation.

Use imports from musecapsule, never src.musecapsule. Keep tests under src/musecapsule/tests.

From the project root, in the activated environment:

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m musecapsule.demo --devkit-dir ../sign-in-with-chatgpt-devkit --model gpt-6.1-sol
python -m musecapsule.search_demo
```

The main demo consumes model allowance and asks for an idea number. The search demo uses TAVILY_API_KEY from the current terminal; never print or commit the key.

The DevKit pin `0a36fefeb913055c8c7a1a29b63d82b96b2e841a` belongs to the external DevKit, not MuseCapsule. macOS python.org installations may require /Applications/Python 3.13/Install Certificates.command for HTTPS. Keep TLS verification enabled.

Update these two documents after significant milestones so a new Work chat can resume from the actual code.
