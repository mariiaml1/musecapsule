from uuid import uuid4

from musecapsule.knowledge import (
    ReferenceDocument,
    chunk_document,
    retrieve_chunks,
)

from musecapsule.embeddings import create_local_embedder
from musecapsule.retrieval import retrieve_semantic_chunks

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

    # Load the embedding model once for the entire evaluation.
    embed = create_local_embedder()

    unrelated_queries = [
        "How do I bake sourdough bread?",
        "What causes lunar eclipses?",
        "How should I water an orchid?",
    ]

    totals = {
        "lexical": {1: 0, 3: 0},
        "semantic": {1: 0, 3: 0},
    }

    for query, expected_title in cases:
        lexical = retrieve_chunks(
            query,
            chunks,
            session_id=session_id,
            limit=3,
        )
        semantic = retrieve_semantic_chunks(
            query,
            chunks,
            session_id=session_id,
            embed=embed,
            limit=3,
            min_score=0.30,
        )

        print(f"\nQuery: {query}")
        print(f"Expected: {expected_title}")

        for strategy, results in [
            ("lexical", lexical),
            ("semantic", semantic),
        ]:
            retrieved_titles = [titles[result.chunk.document_id] for result in results]

            for k in (1, 3):
                totals[strategy][k] += int(expected_title in retrieved_titles[:k])

            print(f"  {strategy}:")
            for result in results:
                title = titles[result.chunk.document_id]
                print(f"    {result.score:.3f} | {title}")

            if not results:
                print("    No matches")

    print(f"\nQueries: {len(cases)}")

    for strategy, scores in totals.items():
        print(f"\n{strategy}:")
        for k in (1, 3):
            recall = scores[k] / len(cases)
            print(f"  Recall@{k}: {recall:.2f}")

    print("\nQueries without relevant sources:")

    for query in unrelated_queries:
        results = retrieve_semantic_chunks(
            query,
            chunks,
            session_id=session_id,
            embed=embed,
            limit=1,
            min_score=0.30,
        )

        print(f"\nQuery: {query}")

        if results:
            best = results[0]
            print(
                f"Nearest: {titles[best.chunk.document_id]} "
                f"| cosine={best.score:.3f}"
            )
            print("Expected: no relevant source")
        else:
            print("No matches")

if __name__ == "__main__":
    main()
