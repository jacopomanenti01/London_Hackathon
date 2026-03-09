"""SurrealDB client wrapper with connection management."""

from __future__ import annotations

from typing import Any

from surrealdb import AsyncSurreal as Surreal

from ...logging import get_logger
from ...settings import SurrealDBSettings

logger = get_logger(__name__)


class SurrealClient:
    """Managed SurrealDB client with async connection lifecycle.

    Wraps the surrealdb-py client with connection pooling awareness,
    namespace/database selection, and structured logging.
    """

    def __init__(self, settings: SurrealDBSettings) -> None:
        self._settings = settings
        self._db: Surreal | None = None

    async def connect(self) -> None:
        """Establish connection to SurrealDB."""
        self._db = Surreal(self._settings.url)
        await self._db.connect()
        await self._db.signin({
            "username": self._settings.username,
            "password": self._settings.password,
        })
        await self._db.use(self._settings.namespace, self._settings.database)
        logger.info(
            "surrealdb_connected",
            namespace=self._settings.namespace,
            database=self._settings.database,
        )

    async def disconnect(self) -> None:
        """Close the SurrealDB connection."""
        if self._db:
            await self._db.close()
            self._db = None
            logger.info("surrealdb_disconnected")

    @property
    def db(self) -> Surreal:
        """Get the active SurrealDB connection."""
        if self._db is None:
            raise RuntimeError("SurrealDB client not connected. Call connect() first.")
        return self._db

    async def execute(self, query: str, params: dict | None = None) -> list:
        """Execute a SurrealQL query.

        Args:
            query: SurrealQL query string.
            params: Optional query parameters.

        Returns:
            Query result list.
        """
        try:
            result = await self.db.query(query, params or {})
            return result
        except Exception as e:
            logger.error("surrealdb_query_error", error=str(e), query=query[:200])
            raise

    async def create(self, table: str, data: dict[str, Any]) -> dict[str, Any]:
        """Create a record in the specified table.

        Args:
            table: Table name (e.g., 'company', 'evidence').
            data: Record data.

        Returns:
            Created record.
        """
        result = await self.db.create(table, data)

        # surrealdb-py may return either a dict or a single-item list.
        # Normalize to one record dict for repository callers.
        if isinstance(result, list):
            if not result:
                return {}
            first = result[0]
            return first if isinstance(first, dict) else {}

        return result if isinstance(result, dict) else {}

    async def select(self, thing: str) -> list | dict:
        """Select record(s) by table or record ID.

        Args:
            thing: Table name or record ID (e.g., 'company' or 'company:abc').

        Returns:
            Record(s) matching the selector.
        """
        result = await self.db.select(thing)
        return result

    async def update(self, thing: str, data: dict) -> dict:
        """Update a record.

        Args:
            thing: Record ID (e.g., 'company:abc').
            data: Fields to update.

        Returns:
            Updated record.
        """
        result = await self.db.update(thing, data)
        return result

    async def delete(self, thing: str) -> None:
        """Delete a record.

        Args:
            thing: Record ID to delete.
        """
        await self.db.delete(thing)
