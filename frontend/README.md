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
npm test
npm run build
npm run lint
```

## Application Areas

**Imagination Workspace** — set goals, enter metaphors, explore interpretations through dialogue.

**Agent Flow** — displays completed LangGraph nodes during narrative
exploration through a POST SSE stream. Each step shows its agent role
and operation. Session persistence is confirmed separately.

**Idea Studio** — review generated ideas, select one and inspect its Engineering Blueprint.

## Current Limitations
- Live events currently cover narrative exploration only.
- Agent Flow displays real node start and completion events during exploration.
- The current workflow executes nodes sequentially.
- If a stream is interrupted, the last active node remains unconfirmed.
- Execution events are not persisted as run history.
- Execution events are shown for the current browser interaction and are
  not persisted as run history.
- Idea generation and blueprint creation still use regular JSON endpoints.
- Interrupted streams require reloading the session before retrying;
  requests are not automatically repeated.
- The interface is intended for local development.
- Generated meanings are AI proposals, not automatically confirmed user interpretations.
- External research is not required to generate ideas or blueprints.
- The diagram currently covers narrative exploration only.
- Diagram topology is maintained in the frontend to match the backend workflow.
- Observed transitions are derived from sequential node events;
  parallel execution is not supported by this visualization.

## Next Steps

- Live LangGraph execution visualization
- Agent status and transition events
- Interactive links between images, hypotheses, ideas and blueprints
- UI refinements and responsive design improvements
