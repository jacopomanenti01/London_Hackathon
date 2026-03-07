"""Application settings loaded from environment variables and config files."""

from __future__ import annotations

import os

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureLLMSettings(BaseSettings):
    """Azure OpenAI LLM provider settings."""

    model_config = SettingsConfigDict(env_prefix="AZURE_OPENAI_", extra="ignore")

    endpoint: str = Field(default="", description="Azure OpenAI endpoint URL")
    api_key: str = Field(default="", description="Azure OpenAI API key")
    api_version: str = Field(default="2024-10-21", description="Azure API version")
    deployment_name: str = Field(default="gpt-5.4-pro", description="Default deployment name")
    embedding_deployment: str = Field(
        default="text-embedding-3-small", description="Embedding deployment name"
    )
    max_retries: int = Field(default=3, description="Max retries for LLM calls")
    timeout_seconds: int = Field(default=60, description="Request timeout in seconds")


class SurrealDBSettings(BaseSettings):
    """SurrealDB connection settings."""

    model_config = SettingsConfigDict(env_prefix="SURREAL_", extra="ignore")

    url: str = Field(default="ws://localhost:8000/rpc", description="SurrealDB WebSocket URL")
    username: str = Field(default="root", description="SurrealDB username")
    password: str = Field(default="root", description="SurrealDB password")
    namespace: str = Field(default="dd_platform", description="SurrealDB namespace")
    database: str = Field(default="due_diligence", description="SurrealDB database")


class TavilySettings(BaseSettings):
    """Tavily search API settings."""

    model_config = SettingsConfigDict(env_prefix="TAVILY_", extra="ignore")

    api_key: str = Field(default="", description="Tavily API key")
    max_results: int = Field(default=10, description="Max results per search")
    timeout_seconds: int = Field(default=30, description="Request timeout")


class SerpAPISettings(BaseSettings):
    """SerpAPI search settings."""

    model_config = SettingsConfigDict(env_prefix="SERPAPI_", extra="ignore")

    api_key: str = Field(default="", description="SerpAPI key")
    max_results: int = Field(default=10, description="Max results per search")
    timeout_seconds: int = Field(default=30, description="Request timeout")


class ApifySettings(BaseSettings):
    """Apify actor settings."""

    model_config = SettingsConfigDict(env_prefix="APIFY_", extra="ignore")

    token: str = Field(default="", description="Apify API token")
    web_scraper_actor_id: str = Field(
        default="apify/web-scraper", description="Default web scraper actor"
    )
    timeout_seconds: int = Field(default=120, description="Actor run timeout")


class FeatureFlags(BaseSettings):
    """Runtime feature flags."""

    model_config = SettingsConfigDict(env_prefix="FF_", extra="ignore")

    enable_embeddings: bool = Field(default=False, description="Enable vector embeddings")
    enable_graph_expansion: bool = Field(default=True, description="Enable graph expansion")
    enable_contradiction_detection: bool = Field(
        default=True, description="Enable contradiction detection"
    )
    default_retrieval_profile: str = Field(
        default="graph_hybrid_expanded", description="Default retrieval profile for builds"
    )
    default_chat_retrieval_profile: str = Field(
        default="schema_aware_graph_hybrid", description="Default retrieval profile for chat"
    )


class Settings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="DD Platform", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Log level")
    host: str = Field(default="0.0.0.0", description="API host")
    port: int = Field(default=8080, description="API port")

    # Schema
    active_schema_id: str = Field(
        default="due_diligence_v1", description="Active profile schema ID"
    )
    schemas_dir: str = Field(default="configs/schemas", description="Path to schema configs")
    prompts_dir: str = Field(default="configs/prompts", description="Path to prompt templates")
    retrieval_profiles_dir: str = Field(
        default="configs/retrieval_profiles", description="Path to retrieval profile configs"
    )

    # Sub-settings
    azure_llm: AzureLLMSettings = Field(default_factory=AzureLLMSettings)
    surrealdb: SurrealDBSettings = Field(default_factory=SurrealDBSettings)
    tavily: TavilySettings = Field(default_factory=TavilySettings)
    serpapi: SerpAPISettings = Field(default_factory=SerpAPISettings)
    apify: ApifySettings = Field(default_factory=ApifySettings)
    features: FeatureFlags = Field(default_factory=FeatureFlags)


def get_settings() -> Settings:
    """Load and return application settings."""
    settings = Settings()
    # Ensure nested provider settings also read from the same .env file.
    settings.azure_llm = AzureLLMSettings(_env_file=".env", _env_file_encoding="utf-8")
    settings.surrealdb = SurrealDBSettings(_env_file=".env", _env_file_encoding="utf-8")
    settings.tavily = TavilySettings(_env_file=".env", _env_file_encoding="utf-8")
    settings.serpapi = SerpAPISettings(_env_file=".env", _env_file_encoding="utf-8")
    settings.apify = ApifySettings(_env_file=".env", _env_file_encoding="utf-8")
    settings.features = FeatureFlags(_env_file=".env", _env_file_encoding="utf-8")

    # Backward-compatible aliases used in some existing scripts/configs.
    if not settings.azure_llm.api_key:
        settings.azure_llm.api_key = os.getenv("API_KEY", "")
    if not settings.azure_llm.endpoint:
        settings.azure_llm.endpoint = os.getenv("AZURE_ENDPOINT", "")
    if not settings.azure_llm.deployment_name:
        settings.azure_llm.deployment_name = os.getenv("LLM_MODEL", "gpt-5.4-pro")
    if not settings.azure_llm.api_version:
        settings.azure_llm.api_version = os.getenv("API_VERSION", "2024-10-21")

    return settings
