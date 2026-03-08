from typing import Any

from surrealdb.connections.async_template import AsyncTemplate


class BaseRepository:
    def __init__(self, db: AsyncTemplate, table: str):
        self.db = db
        self.table = table

    async def create(self, record_id: str, data: dict[str, Any]) -> Any:
        return await self.db.create(f"{self.table}:{record_id}", data)

    async def get(self, record_id: str) -> Any:
        result = await self.db.select(f"{self.table}:{record_id}")
        if result is None or isinstance(result, str):
            return None
        if isinstance(result, list):
            return result[0] if result else None
        return result

    async def get_all(self) -> Any:
        return await self.db.select(self.table)

    async def update(self, record_id: str, data: dict[str, Any]) -> Any:
        return await self.db.update(f"{self.table}:{record_id}", data)

    async def upsert(self, record_id: str, data: dict[str, Any]) -> Any:
        return await self.db.upsert(f"{self.table}:{record_id}", data)

    async def merge(self, record_id: str, data: dict[str, Any]) -> Any:
        return await self.db.merge(f"{self.table}:{record_id}", data)

    async def delete(self, record_id: str) -> Any:
        return await self.db.delete(f"{self.table}:{record_id}")

    async def query(self, surql: str, vars: dict[str, Any] | None = None) -> Any:
        return await self.db.query(surql, vars)
