from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, status

from musecapsule.models import Intent
from musecapsule.state import SessionState
from musecapsule.storage import SessionStore


def create_app(
    database_path: Path = Path("data/musecapsule.db"),
) -> FastAPI:
    """Create the local API with an explicitly configurable database."""
    store = SessionStore(database_path)
    app = FastAPI(
        title="MuseCapsule AI",
        version="0.1.0",
    )

    @app.post(
        "/sessions",
        response_model=SessionState,
        status_code=status.HTTP_201_CREATED,
    )
    def create_session(intent: Intent) -> SessionState:
        """Create and persist a session with the user's explicit intent."""
        session = SessionState(intent=intent)
        store.save(session)
        return session

    @app.get(
        "/sessions/{session_id}",
        response_model=SessionState,
    )
    def get_session(session_id: UUID) -> SessionState:
        """Return the latest saved revision of an existing session."""
        session = store.load(session_id)

        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )

        return session

    return app
