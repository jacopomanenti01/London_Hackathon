from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class ResearchState(TypedDict, total=False):
    company_url: str
    profile_schema: dict
    research_plan: dict[str, str]
    raw_research: dict[str, list[dict]]
    extracted_entities: list[dict]
    current_profile: dict[str, Any]
    research_gaps: list[str]
    iteration: int
    max_iterations: int
    messages: list[BaseMessage]
    error: str | None


class ChatState(TypedDict, total=False):
    current_profile: dict[str, Any]
    graph_context: str
    messages: list[BaseMessage]
