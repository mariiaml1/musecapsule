from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError, field_validator

from musecapsule.models import Intent, Message
from musecapsule.state import SessionState, select_product_idea
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


class SelectIdeaRequest(BaseModel):
    """The user's explicit selection of an existing product idea."""

    idea_id: UUID

MessageStreamHandler = Callable[
    [SessionState, str, Callable[[SessionState], None]],
    Iterator[str],
]


def create_app(
    database_path: Path = Path("data/musecapsule.db"),
    *,
    process_message: Callable[[SessionState, Message], SessionState] | None = None,
    process_ideas: Callable[[SessionState], SessionState] | None = None,
    process_blueprint: Callable[[SessionState], SessionState] | None = None,
    stream_message: MessageStreamHandler | None = None,
) -> FastAPI:
    """Create the local API with an explicitly configurable database."""
    store = SessionStore(database_path)
    app = FastAPI(
        title="MuseCapsule AI",
        version="0.1.0",
    )

    def process_and_save(
        session: SessionState,
        operation: Callable[[SessionState], SessionState],
    ) -> SessionState:
        """Run an operation and persist a changed session with revision checking."""
        try:
            updated = operation(session)
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

        if updated.revision == session.revision:
            return updated

        try:
            store.save(
                updated,
                expected_revision=session.revision,
            )
        except SessionConflictError as error:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Session changed during processing. " "Reload it before retrying."
                ),
            ) from error

        return updated

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

        handler = process_message

        if handler is None:
            raise HTTPException(
                status_code=503,
                detail="Message processing is not configured.",
            )

        message = Message(role="user", text=request.text)

        def operation(current: SessionState) -> SessionState:
            return handler(current, message)

        return process_and_save(session, operation)

    @app.post("/sessions/{session_id}/messages/stream")
    def stream_session_message(
        session_id: UUID,
        request: CreateMessageRequest,
    ):
        """Stream narrative exploration events over SSE."""
        if stream_message is None:
            raise HTTPException(
                status_code=501,
                detail="Agent streaming is not configured.",
            )

        session = store.load(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        def save_result(updated: SessionState) -> None:
            store.save(
                updated,
                expected_revision=session.revision,
            )

        events = stream_message(
            session,
            request.text,
            save_result,
        )

        return StreamingResponse(
            events,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post(
        "/sessions/{session_id}/ideas",
        response_model=SessionState,
    )
    def create_ideas(session_id: UUID) -> SessionState:
        """Generate and persist an idea batch without another question."""
        session = store.load(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        if not session.images:
            raise HTTPException(
                status_code=409,
                detail="Explore at least one image before requesting ideas.",
            )

        if process_ideas is None:
            raise HTTPException(
                status_code=503,
                detail="Idea generation is not configured.",
            )

        return process_and_save(session, process_ideas)

    @app.post(
        "/sessions/{session_id}/selection",
        response_model=SessionState,
    )
    def select_idea(
        session_id: UUID,
        request: SelectIdeaRequest,
    ) -> SessionState:
        """Select an existing idea without invoking generation."""
        session = store.load(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        if not any(idea.id == request.idea_id for idea in session.ideas):
            raise HTTPException(
                status_code=404,
                detail="Idea not found in this session.",
            )

        def operation(current: SessionState) -> SessionState:
            return select_product_idea(current, request.idea_id)

        return process_and_save(session, operation)

    @app.post(
        "/sessions/{session_id}/briefs",
        response_model=SessionState,
    )
    def create_blueprint(session_id: UUID) -> SessionState:
        """Generate and persist a new blueprint for the selected idea."""
        session = store.load(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found.",
            )

        if session.selected_idea_id is None:
            raise HTTPException(
                status_code=409,
                detail="Select an idea before requesting a blueprint.",
            )

        if not any(idea.id == session.selected_idea_id for idea in session.ideas):
            raise HTTPException(
                status_code=409,
                detail="The selected idea is missing from this session.",
            )

        if process_blueprint is None:
            raise HTTPException(
                status_code=503,
                detail="Blueprint generation is not configured.",
            )

        return process_and_save(session, process_blueprint)

    return app
