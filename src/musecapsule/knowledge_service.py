from collections.abc import Callable
from uuid import UUID

from musecapsule.knowledge import ReferenceDocument, chunk_document
from musecapsule.knowledge_storage import KnowledgeStore
from musecapsule.retrieval import index_chunks


def ingest_reference_document(
    *,
    session_id: UUID,
    title: str,
    text: str,
    store: KnowledgeStore,
    model_name: str,
    embed: Callable[[list[str]], list[list[float]]],
    chunk_size: int = 1000,
    overlap: int = 150,
) -> ReferenceDocument:
    """Prepare and atomically persist one reference document and its index.

    Complete validation, chunking, and embedding before starting the write.
    Return the document only after persistence succeeds.
    """
    document = ReferenceDocument(
        session_id=session_id,
        title=title,
        text=text,
    )

    chunks = chunk_document(
        document,
        chunk_size=chunk_size,
        overlap=overlap,
    )

    indexed = index_chunks(
        chunks,
        session_id=session_id,
        model_name=model_name,
        embed=embed,
    )

    store.save_document_with_index(
        document,
        indexed,
        model_name=model_name,
    )

    return document
