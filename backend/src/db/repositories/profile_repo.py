from typing import Any
from datetime import datetime, timezone

from .base import BaseRepository
from ..models import Profile
from ...utils.url import url_to_id


class ProfileRepository(BaseRepository):
    def __init__(self, db: Any):
        super().__init__(db, "profile")

    async def store_profile(self, profile: Profile) -> Any:
        record_id = url_to_id(profile.company_url)
        data = profile.model_dump()
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        return await self.upsert(record_id, data)

    async def get_profile(self, company_url: str) -> Any:
        record_id = url_to_id(company_url)
        result = await self.get(record_id)
        if result is None:
            return None
        # Convert RecordID and other non-serializable types to strings
        return {k: (str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v)
                for k, v in result.items()}

    async def update_section(self, company_url: str, section_name: str, section_data: dict) -> Any:
        record_id = url_to_id(company_url)
        return await self.merge(record_id, {
            f"sections.{section_name}": section_data,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        })
