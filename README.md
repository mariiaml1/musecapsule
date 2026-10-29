# MuseCapsule AI — The AI Imagination Engine

Turn spontaneous metaphors into traceable product ideas and engineering
blueprints, guided by an explicit user goal and constraints.

## Current MVP

- Explore narrative images through open-ended dialogue.
- Extract images with exact source quotes.
- Propose and revise meaning hypotheses while preserving revision history.
- Generate product ideas linked to images and hypotheses.
- Select an idea and generate an engineering blueprint.
- Save and restore sessions with SQLite.
- Observe real LangGraph node lifecycle events through SSE.

AI interpretations are proposals, not established user facts or
automatically confirmed meanings.

## Requirements

- Python 3.13
- Node.js 24
- npm
- macOS for the currently tested live ChatGPT connection
- An eligible ChatGPT account with ChatGPT plan usage enabled for live generation

Automated checks do not require ChatGPT authorization or live generation.

## Install and Check

From the repository root:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

In a separate terminal:

```bash
cd frontend
npm ci
npm run test:all
npm run build
npm run lint
```

## Set Up Live Generation

From the directory containing the MuseCapsule checkout:

```bash
git clone https://github.com/openai/sign-in-with-chatgpt-devkit.git
cd sign-in-with-chatgpt-devkit
git checkout --detach 0a36fefeb913055c8c7a1a29b63d82b96b2e841a
npm ci
npm run build -w @siwc/local
```

Only the local SDK is required; the Paste Perfect desktop application
does not need to be built.

From the MuseCapsule repository root, with the Python environment activated:

```bash
export MUSECAPSULE_DEVKIT_DIR="../sign-in-with-chatgpt-devkit"
export MUSECAPSULE_MODEL="gpt-6.1-sol"
python -m uvicorn musecapsule.server:create_local_app --factory --reload
```

In a separate terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://127.0.0.1:5173.
Backend API documentation is available at http://127.0.0.1:8000/docs.

On the first live generation request, the bridge may open a browser for
ChatGPT authorization. Credentials are stored outside the repository
using Electron safeStorage.

Live generation consumes the connected account's ChatGPT plan allowance
or available credits. Automated tests use controlled substitutes.

## Try the Main Scenario

1. Create a session with your goal and constraints.
2. Describe an imagined scene and optionally continue the dialogue.
3. Generate ideas without having to answer every question.
4. Select an idea and explicitly request its blueprint.
5. Copy the session ID to restore the saved session later.

The default database is `data/musecapsule.db`.
Do not commit local databases, credentials, or personal narratives.

## Architecture and Evaluation

- [Architecture](ARCHITECTURE.md)
- [Development progress](PROGRESS.md)
- [Frontend documentation](frontend/README.md)
- [Manual evaluation scenarios and reports](evals/README.md)

Automated tests verify deterministic contracts and state behavior.
Manual evaluations assess relevance, metaphor grounding, diversity,
and feasibility. Individual successful runs do not establish reliability
across all inputs.

## Limitations

- Local development setup; no production authentication or hosted deployment.
- Model JSON is validated by the application, not constrained by a provider schema.
- Generation quality and latency vary.
- Hypothesis status semantics require further evaluation.
- Agent activity displays the current run rather than persisted execution history.
- External research is optional; the Tavily adapter is separate from the main workflow.
- No automated novelty or market-demand validation.
