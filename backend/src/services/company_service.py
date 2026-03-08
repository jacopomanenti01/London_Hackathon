from typing import Any

from ..db.models import Company
from ..db.repositories.company_repo import CompanyRepository
from ..db.repositories.graph_repo import GraphRepository
from ..utils.url import normalize_url


class CompanyService:
    def __init__(self, db: Any):
        self.company_repo = CompanyRepository(db)
        self.graph_repo = GraphRepository(db)

    async def get_or_create_company(self, url: str) -> dict:
        url = normalize_url(url)
        existing = await self.company_repo.get_by_url(url)
        if existing:
            return existing
        company = Company(url=url)
        return await self.company_repo.upsert_company(company)

    async def update_company(self, url: str, data: dict) -> dict:
        url = normalize_url(url)
        company = Company(url=url, **data)
        return await self.company_repo.upsert_company(company)

    async def get_subgraph(self, url: str) -> dict:
        url = normalize_url(url)
        return await self.graph_repo.get_subgraph(url)
