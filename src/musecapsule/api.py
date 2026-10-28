from collections.abc import Callable
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, ValidationError, field_validator

from musecapsule.models import Intent, Message
from musecapsule.state import SessionState
from musecapsule.storage import SessionConflictError, SessionStore


class CreateMessageRequest(BaseModel):
    """User narrative submitted for exploration."""

    text: str = Field(
        min_length=1,
        examples=["A little bunny jumps across a field of glowing grass."],
    )

    @field_validator("text")
    @classmethod
    def reject_blank_text(cls, value: str) -> str:
        """Preserve the original narrative while rejecting blank input."""
        if not value.strip():
            raise ValueError("Message text must not be blank.")
        return value


def create_app(
    database_path: Path = Path("data/musecapsule.db"),
    *,
    process_message: Callable[[SessionState, Message], SessionState] | None = None,
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

    @app.post("/sessions/{session_id}/messages", response_model=SessionState)
    def create_message(
        session_id: UUID,
        request: CreateMessageRequest,
    ) -> SessionState:
        """Explore a user message and persist the completed result."""
        session = store.load(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        if process_message is None:
            raise HTTPException(
                status_code=503,
                detail="Message processing is not configured.",
            )

        message = Message(role="user", text=request.text)

        try:
            updated = process_message(session, message)
        except ValidationError as error:
            raise HTTPException(
                status_code=502,
                detail="The model response failed validation.",
            ) from error
        except ValueError as error:
            raise HTTPException(
                status_code=502,
                detail="The generated result contains invalid references.",
            ) from error
        except RuntimeError as error:
            raise HTTPException(
                status_code=502,
                detail="Generation could not be completed.",
            ) from error

        try:
            store.save(
                updated,
                expected_revision=session.revision,
            )
        except SessionConflictError as error:
            raise HTTPException(
                status_code=409,
                detail="Session changed during processing. Reload it before retrying.",
            ) from error

        return updated

    return app
