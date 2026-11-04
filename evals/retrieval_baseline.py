from uuid import uuid4

from musecapsule.knowledge import (
    ReferenceDocument,
    chunk_document,
    retrieve_chunks,
)


def main() -> None:
    """Evaluate lexical retrieval on a small synthetic reference corpus."""
    session_id = uuid4()

    documents = [
        ReferenceDocument(
            session_id=session_id,
            title="Request reliability",
            text=(
                "Use bounded retries and explicit timeouts "
                "for failed requests."
            ),
        ),
        ReferenceDocument(
            session_id=session_id,
            title="Session persistence",
            text=(
                "SQLite stores session snapshots "
                "with revision checks."
            ),
        ),
        ReferenceDocument(
            session_id=session_id,
            title="Source attribution",
            text=(
                "Keep exact source quotes and document "
                "identifiers for citations."
            ),
        ),
    ]

    chunks = [
        chunk
        for document in documents
        for chunk in chunk_document(document)
    ]
    titles = {document.id: document.title for document in documents}

    cases = [
        ("retries timeouts", "Request reliability"),
        ("SQLite session snapshots", "Session persistence"),
        ("repeat an unsuccessful call", "Request reliability"),
        ("save conversation history", "Session persistence"),
    ]

    hits_at_1 = 0
    hits_at_3 = 0

    for query, expected_title in cases:
        results = retrieve_chunks(
            query,
            chunks,
            session_id=session_id,
            limit=3,
        )
        retrieved_titles = [
            titles[result.chunk.document_id]
            for result in results
        ]

        found_at_1 = expected_title in retrieved_titles[:1]
        found_at_3 = expected_title in retrieved_titles[:3]

        hits_at_1 += int(found_at_1)
        hits_at_3 += int(found_at_3)

        print(f"\nQuery: {query}")
        print(f"Expected: {expected_title}")
        print(f"Retrieved: {retrieved_titles}")
        print(f"Hit@1: {found_at_1}; Hit@3: {found_at_3}")

    print(f"\nQueries: {len(cases)}")
    print(f"Recall@1: {hits_at_1 / len(cases):.2f}")
    print(f"Recall@3: {hits_at_3 / len(cases):.2f}")


if __name__ == "__main__":
    main()
