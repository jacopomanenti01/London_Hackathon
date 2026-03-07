"""FastAPI dependency injection — wires up all services and repositories."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from ..application.services.chat_service import ChatService
from ..application.services.continuation_service import ContinuationService
from ..application.services.profile_service import ProfileService
from ..application.services.retrieval_service import RetrievalService
from ..application.services.schema_service import SchemaService
from ..logging import get_logger
from ..persistence.surreal.client import SurrealClient
from ..persistence.surreal.queries.evidence_search import EvidenceSearchQueries
from ..persistence.surreal.queries.freshness import FreshnessQueries
from ..persistence.surreal.queries.graph_neighbors import GraphNeighborQueries
from ..persistence.surreal.repositories.claim_repo import ClaimRepository
from ..persistence.surreal.repositories.company_repo import CompanyRepository
from ..persistence.surreal.repositories.conversation_repo import ConversationRepository
from ..persistence.surreal.repositories.evidence_repo import EvidenceRepository
from ..persistence.surreal.repositories.profile_repo import ProfileRepository
from ..persistence.surreal.repositories.run_repo import RunRepository
from ..providers.llm.azure_openai import AzureOpenAIAdapter
from ..providers.search.aggregator import SearchAggregator
from ..providers.search.apify import ApifyTool
from ..providers.search.serpapi import SerpAPITool
from ..providers.search.tavily import TavilyTool
from ..retrieval.assembler import ContextAssembler
from ..retrieval.graph_retriever import GraphRetriever
from ..retrieval.hybrid_retriever import HybridRetriever
from ..retrieval.keyword_retriever import KeywordRetriever
from ..settings import Settings

logger = get_logger(__name__)


def _is_configured_secret(value: str | None) -> bool:
    """Return True only for non-placeholder credential values."""
    if not value:
        return False
    v = value.strip()
    if not v:
        return False
    lowered = v.lower()
    placeholders = (
        "your-",
        "changeme",
        "replace-me",
        "example",
        "test",
        "dummy",
        "placeholder",
    )
    return not any(token in lowered for token in placeholders)


class AppDependencies:
    """Central dependency container for the application.

    Initializes and holds all service instances, repositories,
    and tool integrations. Manages lifecycle (connect/disconnect).
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Database
        self.surreal_client = SurrealClient(settings.surrealdb)

        # Repositories
        self.company_repo = CompanyRepository(self.surreal_client)
        self.evidence_repo = EvidenceRepository(self.surreal_client)
        self.claim_repo = ClaimRepository(self.surreal_client)
        self.profile_repo = ProfileRepository(self.surreal_client)
        self.conversation_repo = ConversationRepository(self.surreal_client)
        self.run_repo = RunRepository(self.surreal_client)

        # Query helpers
        self.freshness_queries = FreshnessQueries(self.surreal_client)
        self.graph_queries = GraphNeighborQueries(self.surreal_client)
        self.evidence_search = EvidenceSearchQueries(self.surreal_client)

        # LLM adapter
        self.llm = AzureOpenAIAdapter(settings.azure_llm)

        # Research tools
        tools = []
        if _is_configured_secret(settings.tavily.api_key):
            tools.append(TavilyTool(settings.tavily))
        if _is_configured_secret(settings.serpapi.api_key):
            tools.append(SerpAPITool(settings.serpapi))
        if _is_configured_secret(settings.apify.token):
            tools.append(ApifyTool(settings.apify))
        self.search_aggregator = SearchAggregator(tools)
        logger.info("search_tools_initialized", enabled_tools=self.search_aggregator.available_tools)

        # Schema service
        self.schema_service = SchemaService(settings.schemas_dir)
        self.schema_service.load_all()

        # Retrievers
        keyword_retriever = KeywordRetriever(self.evidence_search)
        graph_retriever = GraphRetriever(self.graph_queries)
        self.hybrid_retriever = HybridRetriever(
            [keyword_retriever, graph_retriever],
            weights={"keyword": 0.4, "graph": 0.6},
        )
        self.context_assembler = ContextAssembler()

        # Application services
        service_deps = self._build_service_deps()

        self.profile_service = ProfileService(service_deps)
        self.chat_service = ChatService(
            llm=self.llm,
            retriever=self.hybrid_retriever,
            context_assembler=self.context_assembler,
            conversation_repo=self.conversation_repo,
            profile_repo=self.profile_repo,
        )
        self.continuation_service = ContinuationService(
            {**service_deps, "profile_service": self.profile_service}
        )
        self.retrieval_service = RetrievalService(
            retriever=self.hybrid_retriever,
            context_assembler=self.context_assembler,
        )

    def _build_service_deps(self) -> dict[str, Any]:
        """Build the shared dependency dict for services."""
        return {
            "llm": self.llm,
            "search_aggregator": self.search_aggregator,
            "company_repo": self.company_repo,
            "profile_repo": self.profile_repo,
            "evidence_repo": self.evidence_repo,
            "claim_repo": self.claim_repo,
            "run_repo": self.run_repo,
            "conversation_repo": self.conversation_repo,
            "freshness_queries": self.freshness_queries,
            "graph_queries": self.graph_queries,
            "schema_service": self.schema_service,
        }

    async def startup(self) -> None:
        """Initialize connections on app startup."""
        await self.surreal_client.connect()

        # Run migrations
        from ..persistence.surreal.migrations import run_migrations
        await run_migrations(self.surreal_client)

    async def shutdown(self) -> None:
        """Clean up connections on app shutdown."""
        await self.surreal_client.disconnect()
        await self.llm.close()
