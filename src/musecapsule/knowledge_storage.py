import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

from math import hypot, isfinite

from musecapsule.knowledge import ReferenceDocument, validate_chunk_source
from musecapsule.retrieval import EmbeddedChunk


class KnowledgeStore:
    """Store session-scoped reference documents in SQLite."""

    def _insert_index(
        self,
        connection: sqlite3.Connection,
        indexed: list[EmbeddedChunk],
        *,
        session_id: UUID,
        model_name: str,
    ) -> None:
        """Insert an index using the caller's transaction."""
        if not indexed:
            return

        dimension = len(indexed[0].vector)

        existing = connection.execute(
            """
            SELECT dimension
            FROM reference_embeddings
            WHERE session_id = ? AND model_name = ?
            LIMIT 1
            """,
            (str(session_id), model_name),
        ).fetchone()

        if existing is not None and existing[0] != dimension:
            raise ValueError("Index dimensions are inconsistent.")

        for item in indexed:
            self._validate_index_item(
                item, session_id, model_name, dimension,
            )

            row = connection.execute(
                """
                SELECT payload
                FROM reference_documents
                WHERE document_id = ? AND session_id = ?
                """,
                (str(item.chunk.document_id), str(session_id)),
            ).fetchone()

            if row is None:
                raise ValueError("Index source document is missing.")

            document = ReferenceDocument.model_validate_json(row[0])
            validate_chunk_source(item.chunk, document)

            connection.execute(
                """
                INSERT INTO reference_embeddings (
                    chunk_id, session_id, model_name,
                    dimension, payload
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    str(item.chunk.id),
                    str(session_id),
                    model_name,
                    dimension,
                    item.model_dump_json(),
                ),
            )

    def save_index(
        self,
        indexed: list[EmbeddedChunk],
        *,
        session_id: UUID,
        model_name: str,
    ) -> None:
        """Atomically save embeddings for existing source documents."""
        model_name = model_name.strip()

        if not model_name:
            raise ValueError("Embedding model name must not be blank.")

        if not indexed:
            return

        try:
            with closing(sqlite3.connect(self.database_path)) as connection:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")
                    self._insert_index(
                        connection,
                        indexed,
                        session_id=session_id,
                        model_name=model_name,
                    )
        except sqlite3.IntegrityError as error:
            raise ValueError("Chunk embedding is already stored.") from error

    def save_document_with_index(
        self,
        document: ReferenceDocument,
        indexed: list[EmbeddedChunk],
        *,
        model_name: str,
    ) -> None:
        """Atomically insert a new document and its validated embeddings.

        Require at least one fragment belonging to this document.
        Roll back all writes if validation or insertion fails.
        """
        model_name = model_name.strip()

        if not model_name:
            raise ValueError("Embedding model name must not be blank.")

        if not indexed:
            raise ValueError("Document index must not be empty.")

        if any(item.chunk.document_id != document.id for item in indexed):
            raise ValueError("Index references a different document.")

        try:
            with closing(sqlite3.connect(self.database_path)) as connection:
                with connection:
                    connection.execute("BEGIN IMMEDIATE")

                    connection.execute(
                        """
                        INSERT INTO reference_documents (
                            document_id, session_id, payload
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            str(document.id),
                            str(document.session_id),
                            document.model_dump_json(),
                        ),
                    )

                    self._insert_index(
                        connection,
                        indexed,
                        session_id=document.session_id,
                        model_name=model_name,
                    )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "Reference document or chunk embedding is already stored."
            ) from error
        
    def load_index(
        self,
        *,
        session_id: UUID,
        model_name: str,
    ) -> list[EmbeddedChunk]:
        """Restore embeddings for exactly one session and model."""
        model_name = model_name.strip()
        if not model_name:
            raise ValueError("Embedding model name must not be blank.")

        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                """
                SELECT dimension, payload
                FROM reference_embeddings
                WHERE session_id = ? AND model_name = ?
                ORDER BY rowid
                """,
                (str(session_id), model_name),
            ).fetchall()

        indexed: list[EmbeddedChunk] = []
        dimension = rows[0][0] if rows else 0

        for stored_dimension, payload in rows:
            if stored_dimension != dimension:
                raise ValueError("Index dimensions are inconsistent.")

            item = EmbeddedChunk.model_validate_json(payload)
            self._validate_index_item(
                item, session_id, model_name, dimension,
            )
            indexed.append(item)

        return indexed

    @staticmethod
    def _validate_index_item(
        item: EmbeddedChunk,
        session_id: UUID,
        model_name: str,
        dimension: int,
    ) -> None:
        """Check ownership, model identity, and vector consistency."""
        if item.chunk.session_id != session_id:
            raise ValueError("Index item belongs to a different session.")

        if item.model_name != model_name:
            raise ValueError("Index item uses a different embedding model.")

        if dimension <= 0 or len(item.vector) != dimension:
            raise ValueError("Index dimensions are inconsistent.")

        if any(not isfinite(value) for value in item.vector):
            raise ValueError("Index vector contains nonfinite values.")

        norm = hypot(*item.vector)
        if norm == 0 or not isfinite(norm):
            raise ValueError("Index vector norm must be finite and positive.")

    def __init__(self, database_path: Path) -> None:
        """Create the database directory and reference document table."""
        self.database_path = database_path.expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS reference_documents (
                        document_id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        payload TEXT NOT NULL
                    )
                """)
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS reference_embeddings (
                        chunk_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        model_name TEXT NOT NULL,
                        dimension INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY (chunk_id, model_name)
                    )
                """)

    def save_document(self, document: ReferenceDocument) -> None:
        """Insert a document without overwriting an existing source.

        Raises:
            ValueError: If the document ID is already stored.
        """
        try:
            with closing(sqlite3.connect(self.database_path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO reference_documents (
                            document_id, session_id, payload
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            str(document.id),
                            str(document.session_id),
                            document.model_dump_json(),
                        ),
                    )
        except sqlite3.IntegrityError as error:
            raise ValueError(
                "Reference document already exists."
            ) from error

    def load_document(
        self,
        document_id: UUID,
        *,
        session_id: UUID,
    ) -> ReferenceDocument | None:
        """Load a document only within the requested session."""
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT payload
                FROM reference_documents
                WHERE document_id = ? AND session_id = ?
                """,
                (str(document_id), str(session_id)),
            ).fetchone()

        if row is None:
            return None

        document = ReferenceDocument.model_validate_json(row[0])

        if document.id != document_id or document.session_id != session_id:
            raise ValueError("Stored reference identity does not match lookup.")

        return document
