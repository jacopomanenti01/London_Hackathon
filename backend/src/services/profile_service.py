from typing import Any

from ..db.models import Profile
from ..db.repositories.profile_repo import ProfileRepository
from ..schemas.profile import ProfileSchema, load_schema, load_schema_from_dict


class ProfileService:
    def __init__(self, db: Any):
        self.profile_repo = ProfileRepository(db)
        self._schema: ProfileSchema | None = None

    @property
    def schema(self) -> ProfileSchema:
        if self._schema is None:
            self._schema = load_schema()
        return self._schema

    def set_schema(self, schema_dict: dict) -> ProfileSchema:
        self._schema = load_schema_from_dict(schema_dict)
        return self._schema

    async def store_profile(self, company_url: str, sections: dict) -> dict:
        profile = Profile(
            company_url=company_url,
            schema_version=self.schema.version,
            sections=sections,
        )
        return await self.profile_repo.store_profile(profile)

    async def get_profile(self, company_url: str) -> dict | None:
        return await self.profile_repo.get_profile(company_url)

    async def update_section(self, company_url: str, section_name: str, data: dict) -> dict:
        return await self.profile_repo.update_section(company_url, section_name, data)
