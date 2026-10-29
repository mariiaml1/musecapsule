# MuseCapsule AI — Frontend

React + TypeScript interface for **MuseCapsule AI — The AI Imagination Engine**.

MuseCapsule transforms spontaneous human metaphors into structured product ideas and engineering blueprints, guided by the user's explicit goals and constraints.

## Tech Stack

- React
- TypeScript
- Vite
- CSS
- FastAPI backend
- LangGraph orchestration (backend)
- React Flow (@xyflow/react)

## Features

- Inspect the selected idea's source images and exact narrative quotes
- Review linked AI hypotheses and their current statuses
- Read the complete engineering blueprint, including constraints and risks
- Create a session with a goal and constraints
- Restore an existing session by ID
- Explore metaphors through an interactive dialogue
- Generate product ideas grounded in narrative images and meaning hypotheses
- Select an idea to develop
- Generate and view an Engineering Blueprint
- Restore saved session data
- Visualize the exploration workflow with React Flow
- Display real node start and completion statuses
- Highlight observed transitions in the sequential workflow

## Local Development

### 1. Start the backend

From the repository root, with the Python environment activated:

```bash
export MUSECAPSULE_DEVKIT_DIR="../sign-in-with-chatgpt-devkit"
python -m uvicorn musecapsule.server:create_local_app --factory --reload
```

The backend runs at `http://127.0.0.1:8000`.

### 2. Start the frontend

From the `frontend` directory:

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

The Vite development proxy forwards `/api` requests to the local FastAPI backend.

## Quality Checks

```bash
npm run test:all
npm run build
npm run lint
```

## Creative Journey

Navigation changes only the current view, never session data or backend execution.

- **Intention** — enter a goal and constraints before creating a session. After
  creation, a compact goal summary replaces the form. Session restoration remains
  available from the header.
- **Imagination** — explore through dialogue, with extracted images, exact quotes,
  and AI-proposed hypotheses alongside it. Generate ideas once saved images exist;
  answering every clarification question is optional. Unsent text is excluded.
- **Ideas** — readable cards with image labels and expandable metaphor provenance.
  Selecting an idea saves the choice, then opens Blueprint without generating it.
- **Blueprint** — explicitly generate an engineering plan for the saved selection.
  The selected idea and the blueprint each expose their own source references.
- **Under the hood / Agent Activity** — collapsible, available from every view.
  Node activity comes from SSE events. Only terminal session completion confirms
  persistence; a failed follow-up read does not undo that confirmation.

Creation opens Imagination. Restoration opens Blueprint when an idea is selected,
Ideas when saved ideas exist, and otherwise Imagination. Navigation remains
available during a request; mutating actions stay disabled while it runs.
Draft text survives stage navigation and is cleared when opening another session.

## Frontend Structure

`App.tsx` retains session state and command handlers. `JourneyViews.tsx` contains
navigation, intention, dialogue, and exploration sources. `IdeasView.tsx` and
`BlueprintView.tsx` render saved products. `IdeaOrigin.tsx` resolves provenance.
`AgentActivity.tsx` contains the existing graph and lifecycle presentation.
`api.ts`, `agent-events.ts`, and `flow-path.ts` retain their existing contracts.
No backend changes are required.

## Tests

`npm test` runs the existing SSE parser, stream contract, and observed-transition
tests. `npm run test:ui` runs Vitest and React Testing Library in jsdom. These UI
tests use mocked API functions and graph rendering, so no LLM account or running
backend is required. `npm run test:all` runs both suites. Browser visual QA and a
live backend smoke test remain separate checks.

## Current Limitations

- Live execution events cover narrative exploration, idea generation,
  and engineering blueprint generation.
- Each command runs separately and persists its final session once.
- Idea selection is deterministic and does not invoke an LLM.
- Agent Flow displays the latest request; execution history is not persisted.
- Disconnected diagram nodes represent separate user-triggered commands.
- Execution events are shown for the current browser interaction and are
  not persisted as run history.
- Interrupted streams require reloading the session before retrying;
  requests are not automatically repeated.
- The interface is intended for local development.
- Generated meanings are AI proposals, not automatically confirmed user interpretations.
- External research is not required to generate ideas or blueprints.
- The diagram currently covers narrative exploration only.
- Diagram topology is maintained in the frontend to match the backend workflow.
- Observed transitions are derived from sequential node events;
  parallel execution is not supported by this visualization.
