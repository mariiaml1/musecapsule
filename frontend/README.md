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

## Features

- Create a session with a goal and constraints
- Restore an existing session by ID
- Explore metaphors through an interactive dialogue
- Generate product ideas grounded in narrative images and meaning hypotheses
- Select an idea to develop
- Generate and view an Engineering Blueprint
- Restore saved session data

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
npm run build
npm run lint
```

## Application Areas

**Imagination Workspace** — set goals, enter metaphors, explore interpretations through dialogue.

**Agent Flow** — reserved for visualizing the LangGraph execution process.

**Idea Studio** — review generated ideas, select one and inspect its Engineering Blueprint.

## Current Limitations

- Agent Flow does not yet display live execution events.
- The interface is intended for local development.
- Generated meanings are AI proposals, not automatically confirmed user interpretations.
- External research is not required to generate ideas or blueprints.

## Next Steps

- Live LangGraph execution visualization
- Agent status and transition events
- Interactive links between images, hypotheses, ideas and blueprints
- UI refinements and responsive design improvements
