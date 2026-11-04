import os
from collections.abc import Callable, Iterator
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI

from musecapsule.agent_events import stream_graph_run
from musecapsule.api import (
    ReferenceIngestionHandler,
    ReferenceSearchHandler,
    create_app,
)
from musecapsule.embeddings import (
    EMBEDDING_MODEL_NAME,
    create_local_embedder,
)
from musecapsule.knowledge import ReferenceChunk, ReferenceDocument
from musecapsule.knowledge_service import ingest_reference_document
from musecapsule.knowledge_storage import KnowledgeStore
from musecapsule.llm import request_generation
from musecapsule.models import Message, ProductIdea
from musecapsule.retrieval import SemanticMatch, search_index
from musecapsule.state import SessionState
from musecapsule.workflow import build_exploration_graph


def create_local_app() -> FastAPI:
    """Configure the local API with the real exploration workflow."""
    configured_dir = os.environ.get("MUSECAPSULE_DEVKIT_DIR")
    if not configured_dir or not configured_dir.strip():
        raise RuntimeError("MUSECAPSULE_DEVKIT_DIR must be configured.")

    devkit_dir = Path(configured_dir).expanduser().resolve()
    if not devkit_dir.is_dir():
        raise RuntimeError("The configured DevKit directory does not exist.")

    model = os.environ.get("MUSECAPSULE_MODEL", "gpt-6.1-sol")
    database_path = Path(
        os.environ.get("MUSECAPSULE_DATABASE", "data/musecapsule.db")
    )
    prompts_dir = Path(__file__).resolve().parent / "prompts"

    def create_generator(prompt_name: str) -> Callable[[str], str]:
        """Bind task instructions to the configured local connection."""
        instructions = (prompts_dir / prompt_name).read_text(
            encoding="utf-8",
        )

        def generate(text: str) -> str:
            return request_generation(
                text=text,
                devkit_dir=devkit_dir,
                instructions=instructions,
                model=model,
            )

        return generate

    def process_message(
        session: SessionState,
        message: Message,
    ) -> SessionState:
        """Process one user turn through the compiled graph."""
        result = graph.invoke(
            {
                "session": session,
                "command": "explore",
                "incoming_message": message,
            }
        )
        return result["session"]

    def process_ideas(session: SessionState) -> SessionState:
        """Generate ideas from the existing narrative context."""
        result = graph.invoke(
            {
                "session": session,
                "command": "generate_ideas",
            }
        )
        return result["session"]

    def process_idea_revision(
        session: SessionState,
        idea_id: UUID,
    ) -> SessionState:
        """Revise one idea through the existing graph without changing selection."""
        result = graph.invoke(
            {
                "session": session,
                "command": "revise_idea",
                "idea_id": idea_id,
            }
        )
        return result["session"]

    def process_blueprint(session: SessionState) -> SessionState:
        """Build a blueprint without performing external research."""
        result = graph.invoke(
            {
                "session": session,
                "command": "build_blueprint",
            }
        )
        return result["session"]

    def stream_message(
        session: SessionState,
        text: str,
        save_result: Callable[[SessionState], None],
    ) -> Iterator[str]:
        """Stream one exploration run and persist its final session."""
        return stream_graph_run(
            graph,
            {
                "session": session,
                "command": "explore",
                "incoming_message": Message(
                    role="user",
                    text=text,
                ),
            },
            save_result,
        )

    def stream_ideas(
        session: SessionState,
        save_result: Callable[[SessionState], None],
    ) -> Iterator[str]:
        """Stream idea generation through the existing compiled graph."""
        return stream_graph_run(
            graph,
            {
                "session": session,
                "command": "generate_ideas",
            },
            save_result,
        )

    def stream_blueprint(
        session: SessionState,
        save_result: Callable[[SessionState], None],
    ) -> Iterator[str]:
        """Stream blueprint generation through the existing graph."""
        return stream_graph_run(
            graph,
            {
                "session": session,
                "command": "build_blueprint",
            },
            save_result,
        )

    reference_handler: ReferenceIngestionHandler | None = None

    reference_search_handler: ReferenceSearchHandler | None = None
    blueprint_retriever: Callable[[UUID, ProductIdea], list[ReferenceChunk]] | None = (
        None
    )

    if os.environ.get("MUSECAPSULE_RAG_ENABLED", "0") == "1":
        embed = create_local_embedder()
        knowledge_store = KnowledgeStore(database_path)

        def process_reference(
            session_id: UUID,
            title: str,
            text: str,
        ) -> ReferenceDocument:
            """Index reference material using the shared local embedder."""
            return ingest_reference_document(
                session_id=session_id,
                title=title,
                text=text,
                store=knowledge_store,
                model_name=EMBEDDING_MODEL_NAME,
                embed=embed,
            )

        reference_handler = process_reference

        def search_reference_material(
            session_id: UUID,
            query: str,
            limit: int,
            min_score: float,
        ) -> list[SemanticMatch]:
            """Search saved embeddings using the shared local embedder."""
            indexed = knowledge_store.load_index(
                session_id=session_id,
                model_name=EMBEDDING_MODEL_NAME,
            )

            return search_index(
                query,
                indexed,
                session_id=session_id,
                model_name=EMBEDDING_MODEL_NAME,
                embed=embed,
                limit=limit,
                min_score=min_score,
            )

        reference_search_handler = search_reference_material

        def retrieve_blueprint_references(
            session_id: UUID,
            idea: ProductIdea,
        ) -> list[ReferenceChunk]:
            """Retrieve supporting material for the selected idea."""
            query = f"{idea.title}\n{idea.description}"

            matches = search_reference_material(
                session_id,
                query,
                3,
                0.30,
            )

            return [match.chunk for match in matches]

        blueprint_retriever = retrieve_blueprint_references

    graph = build_exploration_graph(
        generate_images=create_generator("metaphor_explorer.md"),
        generate_hypotheses=create_generator("hypothesis_proposals.md"),
        generate_revisions=create_generator("hypothesis_revisions.md"),
        generate_question=create_generator("imagination_guide.md"),
        generate_ideas=create_generator("idea_evolution.md"),
        generate_architecture=create_generator("idea_architect.md"),
        generate_idea_revision=create_generator("idea_revision.md"),
        retrieve_references=blueprint_retriever,
    )

    return create_app(
        database_path,
        process_message=process_message,
        process_ideas=process_ideas,
        process_blueprint=process_blueprint,
        stream_message=stream_message,
        stream_ideas=stream_ideas,
        stream_blueprint=stream_blueprint,
        process_idea_revision=process_idea_revision,
        process_reference=reference_handler,
        search_references=reference_search_handler,
    )
