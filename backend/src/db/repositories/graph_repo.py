from typing import Any

from .base import BaseRepository
from ...utils.url import url_to_id


class GraphRepository(BaseRepository):
    def __init__(self, db: Any):
        super().__init__(db, "entity")

    async def create_relation(
        self,
        from_table: str,
        from_id: str,
        relation: str,
        to_table: str,
        to_id: str,
        data: dict[str, Any] | None = None,
    ) -> Any:
        set_clause = ""
        if data:
            pairs = ", ".join(f"{k} = ${k}" for k in data)
            set_clause = f" SET {pairs}"
        surql = (
            f"RELATE {from_table}:{from_id}->{relation}->{to_table}:{to_id}"
            f"{set_clause}"
        )
        return await self.query(surql, data)

    async def traverse(
        self,
        from_table: str,
        from_id: str,
        relation: str,
        depth: int = 1,
    ) -> Any:
        arrows = "".join(f"->{relation}->?" for _ in range(depth))
        surql = f"SELECT {arrows} FROM {from_table}:{from_id}"
        return await self.query(surql)

    async def get_subgraph(self, company_url: str) -> Any:
        record_id = url_to_id(company_url)
        surql = (
            f"SELECT *, "
            f"->works_at->person.* AS people, "
            f"->has_risk->risk.* AS risks, "
            f"->has_certification->certification.* AS certifications, "
            f"->supplies_to->company.* AS suppliers, "
            f"->subsidiary_of->company.* AS subsidiaries "
            f"FROM company:{record_id}"
        )
        return await self.query(surql)
