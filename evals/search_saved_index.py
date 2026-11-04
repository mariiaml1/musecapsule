import os
from pathlib import Path
from uuid import UUID

from musecapsule.embeddings import (
    EMBEDDING_MODEL_NAME,
    create_local_embedder,
)
from musecapsule.knowledge_storage import KnowledgeStore
from musecapsule.retrieval import search_index


def main() -> None:
    """Search a persisted index and verify returned source fragments."""
    session_id = UUID("d98260dc-2c2c-4c16-bc13-686b1b8fe3c4")
    database_path = Path(
        os.environ.get("MUSECAPSULE_DATABASE", "data/musecapsule.db")
    )
    store = KnowledgeStore(database_path)

    indexed = store.load_index(
        session_id=session_id,
        model_name=EMBEDDING_MODEL_NAME,
    )

    print("Database:", store.database_path)
    print("Loaded chunks:", len(indexed))

    if not indexed:
        raise SystemExit("No saved index found. Check the database path.")

    embed = create_local_embedder()

    queries = [
        "How can I retry failed requests without running forever?",
        "How do I bake sourdough bread?",
    ]

    for query in queries:
        print(f"\nQuery: {query}")

        results = search_index(
            query,
            indexed,
            session_id=session_id,
            model_name=EMBEDDING_MODEL_NAME,
            embed=embed,
            limit=3,
            min_score=0.30,
        )

        if not results:
            print("No matches")

        for result in results:
            chunk = result.chunk
            document = store.load_document(
                chunk.document_id,
                session_id=session_id,
            )

            assert document is not None
            assert chunk.text == document.text[chunk.start:chunk.end]

            print(f"Score: {result.score:.3f}")
            print("Document:", document.title)
            print("Document ID:", document.id)
            print("Source:", chunk.text)


if __name__ == "__main__":
    main()
