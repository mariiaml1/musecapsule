import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import UUID

from musecapsule.state import SessionState


class SessionStore:
    """Store session snapshots in a local SQLite database."""

    def __init__(self, database_path: Path) -> None:
        """Create the database directory and snapshot table."""
        self.database_path = database_path.expanduser().resolve()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.execute("""
                    CREATE TABLE IF NOT EXISTS session_snapshots (
                        session_id TEXT NOT NULL,
                        revision INTEGER NOT NULL,
                        payload TEXT NOT NULL,
                        PRIMARY KEY (session_id, revision)
                    )
                    """)

    def save(self, session: SessionState) -> None:
        """Save a new snapshot without overwriting an existing revision.

        Raises:
            ValueError: If this session revision is already stored.
        """
        try:
            with closing(sqlite3.connect(self.database_path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO session_snapshots (
                            session_id, revision, payload
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            str(session.id),
                            session.revision,
                            session.model_dump_json(),
                        ),
                    )
        except sqlite3.IntegrityError as error:
            raise ValueError("Session revision is already stored.") from error

    def load(self, session_id: UUID) -> SessionState | None:
        """Restore the latest stored revision, or return None if absent."""
        with closing(sqlite3.connect(self.database_path)) as connection:
            row = connection.execute(
                """
                SELECT payload
                FROM session_snapshots
                WHERE session_id = ?
                ORDER BY revision DESC
                LIMIT 1
                """,
                (str(session_id),),
            ).fetchone()

        if row is None:
            return None

        return SessionState.model_validate_json(row[0])
