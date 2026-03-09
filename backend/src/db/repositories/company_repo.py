from typing import Any
from datetime import datetime, timezone

from .base import BaseRepository
from ..models import Company
from ...utils.url import url_to_id


class CompanyRepository(BaseRepository):
    def __init__(self, db: Any):
        super().__init__(db, "company")

    async def upsert_company(self, company: Company) -> Any:
        record_id = url_to_id(company.url)
        data = company.model_dump()
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        return await self.upsert(record_id, data)

    async def get_by_url(self, url: str) -> Any:
        record_id = url_to_id(url)
        return await self.get(record_id)

    async def get_related_entities(self, url: str) -> Any:
        record_id = url_to_id(url)
        result = await self.query(
            "SELECT *, ->works_at->person.* AS people, "
            "->has_risk->risk.* AS risks, "
            "->has_certification->certification.* AS certifications "
            f"FROM company:{record_id}"
        )
        return result
