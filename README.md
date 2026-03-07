# DD Platform — Company Due Diligence Agent Platform

AI-powered platform for building, updating, and chatting with company due diligence profiles. Uses **GraphRAG** retrieval over **SurrealDB**, **LangGraph** orchestration, and **Azure OpenAI** to produce evidence-backed, schema-structured supply-chain risk profiles.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)

---

## Overview

Given a company URL, the platform automatically:

1. **Resolves** the company's canonical identity (URL normalization, domain extraction)
2. **Checks** SurrealDB for existing profile data
3. **Evaluates freshness** — only researches sections whose data exceeds their TTL
4. **Researches** via Tavily, SerpAPI, and Apify web tools
5. **Extracts claims** using Azure OpenAI (structured, schema-mapped facts)
6. **Synthesizes** a full profile under the active schema
7. **Persists** everything as a knowledge graph in SurrealDB
8. **Enables chat** — evidence-backed Q&A with citations and contradiction detection

### Key Principles

| Principle | Description |
|-----------|-------------|
| **Evidence-First** | Every profile field traces back to source documents → evidence → claims |
| **Incremental Refresh** | Only fetch what's stale or missing — re-builds are cheap |
| **Configurable Schema** | Profile structure is defined in YAML and swappable at runtime |
| **GraphRAG** | Retrieval walks SurrealDB graph edges for provenance-aware context |
| **Pluggable Retrieval** | Multiple retrieval profiles (keyword, graph, hybrid, contradiction-aware) |

---

## Architecture

```
                          ┌─────────────┐
                          │   FastAPI    │
                          │   /api/v1    │
                          └──────┬──────┘
                                 │
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
        ProfileService     ChatService     ContinuationService
              │                  │                   │
              ▼                  │                   │
     ┌─────────────────┐        │                   │
     │    LangGraph     │        │                   │
     │   9-Node Graph   │        │                   │
     └────────┬────────┘        │                   │
              │                  │                   │
    ┌─────────┼─────────┐       │                   │
    ▼         ▼         ▼       ▼                   │
SurrealDB  Web Tools  Azure  Hybrid              (reuses
 (graph)   (Tavily,   OpenAI Retriever          ProfileService)
           SerpAPI,    LLM   (Keyword +
           Apify)            Graph)
```

### Profile Build Workflow (LangGraph)

```
normalize_company → load_local_context → assess_freshness → plan_research
                                                                │
                                                    ┌── [all fresh?] ──┐
                                                    ▼                  ▼
                                          retrieve_external     synthesize_profile
                                          _evidence                    ▲
                                                    │                  │
                                                    ▼                  │
                                              extract_claims ──────────┘
                                                                       │
                                                                       ▼
                                                              persist_snapshot
                                                                       │
                                                                       ▼
                                                                 finalize_run → END
```

### SurrealDB Knowledge Graph

```
company ──has_source──▶ source_document ──has_evidence──▶ evidence
                                                              │
                                                    supports_claim
                                                              ▼
company ◀──belongs_to── claim ──related_to──▶ claim
    │
    └──has_profile_snapshot──▶ profile_snapshot
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- Docker (for SurrealDB)

### 1. Clone and install

```bash
git clone <repo-url>
cd London_Hackathon
make install
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys:
#   AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
#   TAVILY_API_KEY
#   SERPAPI_API_KEY (optional)
#   APIFY_TOKEN (optional)
```

### 3. Start SurrealDB

```bash
make db-up
```

### 4. Start the API

```bash
make api
```

The server starts at `http://localhost:8080`. Interactive docs at `http://localhost:8080/docs`.

### 5. Build your first profile

```bash
curl -X POST http://localhost:8080/api/v1/profiles/build \
  -H "Content-Type: application/json" \
  -d '{"company_url": "https://www.siemens.com", "force_refresh": true}'
```

### 6. Chat with the profile

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "company:www_siemens_com",
    "message": "What is their sanctions exposure?"
  }'
```

---

## API Reference

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/ready` | Readiness check |

### Profiles

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/profiles/build` | Build a due diligence profile |
| GET | `/api/v1/profiles/{company_id}` | Get latest profile snapshot |
| GET | `/api/v1/profiles/{company_id}/evidence` | Get evidence with filters |

#### POST `/api/v1/profiles/build`

```json
{
  "company_url": "https://www.example.com",
  "force_refresh": false,
  "schema_id": null,
  "publish_snapshot": true,
  "research_scope": ["all"],
  "retrieval_profile": "graph_hybrid_expanded",
  "experiment_tags": []
}
```

**Response:**

```json
{
  "company_id": "company:www_example_com",
  "run_id": "run:20260307120000_a1b2c3d4",
  "profile": {
    "sections": {
      "company_identity": {
        "legal_name": { "value": "Example Corp Ltd.", "confidence": 0.9 }
      }
    }
  },
  "snapshot_id": "snapshot:abc123",
  "schema_id": "due_diligence_v1",
  "schema_version": 1,
  "retrieval_profile": "graph_hybrid_expanded",
  "freshness": [],
  "metrics": {},
  "status": "completed",
  "errors": []
}
```

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Evidence-backed Q&A |

```json
{
  "company_id": "company:www_example_com",
  "message": "What industries do they operate in?",
  "conversation_id": null,
  "retrieval_profile": "schema_aware_graph_hybrid"
}
```

**Response includes:** answer, citations (claim IDs, evidence IDs, source URLs), contradiction flags, follow-up research suggestions.

### Continuation Research

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/research/continue` | Targeted follow-up research |

```json
{
  "company_id": "company:www_example_com",
  "instruction": "Investigate recent sanctions and compliance issues in more detail",
  "target_sections": ["compliance_and_risk"],
  "retrieval_profile": "graph_hybrid_expanded"
}
```

### Retrieval Search

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/retrieval/search` | Direct knowledge graph search |

```json
{
  "company_id": "company:www_example_com",
  "query": "sanctions exposure",
  "retrieval_profile": "hybrid_basic",
  "section_ids": ["compliance_and_risk"],
  "top_k": 20
}
```

### Schema Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/schemas/` | List available schemas |
| GET | `/api/v1/schemas/active` | Get active schema |
| POST | `/api/v1/schemas/activate/{schema_id}` | Activate a schema |

---

## Configuration

### Environment Variables

See [`.env.example`](.env.example) for the full list. Key groups:

| Group | Variables | Purpose |
|-------|-----------|---------|
| **Azure OpenAI** | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` | LLM for claim extraction and synthesis |
| **SurrealDB** | `SURREAL_URL`, `SURREAL_USERNAME`, `SURREAL_PASSWORD` | Graph database connection |
| **Tavily** | `TAVILY_API_KEY` | Primary web search tool |
| **SerpAPI** | `SERPAPI_API_KEY` | Secondary web search (Google) |
| **Apify** | `APIFY_TOKEN` | Web crawling / scraping |
| **Feature Flags** | `FF_ENABLE_GRAPH_EXPANSION`, `FF_ENABLE_CONTRADICTION_DETECTION` | Toggle features at runtime |

### Profile Schema (`configs/schemas/`)

The profile structure is defined in YAML. The default schema (`due_diligence_v1`) includes 7 sections:

| Section | TTL | Description |
|---------|-----|-------------|
| `company_identity` | 180 days | Legal name, HQ, country, employees |
| `ownership_and_structure` | 180 days | Parent company, subsidiaries, public/private |
| `operations_and_supply_chain` | 90 days | Industry, products, countries, manufacturing |
| `compliance_and_risk` | 30 days | Sanctions, adverse media, litigation, corruption |
| `esg_and_certifications` | 90 days | Sustainability, certifications, human rights |
| `financial_health` | 90 days | Revenue, funding status, insolvency signals |
| `profile_meta` | 1 day | Confidence summary, coverage score, open questions |

Each field has its own TTL, confidence threshold, and contradiction policy.

### Retrieval Profiles (`configs/retrieval_profiles/`)

Control how evidence is retrieved from the knowledge graph:

| Profile | Use Case | Strategy |
|---------|----------|----------|
| `keyword_only` | Baseline / evaluation | Text search only |
| `hybrid_basic` | Quick lookups | Keyword + 1-hop graph |
| `graph_hybrid_expanded` | Profile builds (default) | Keyword + 2-hop graph + reranking |
| `schema_aware_graph_hybrid` | Chat Q&A (default) | Schema-guided graph + keyword |
| `contradiction_aware_graph_hybrid` | Compliance / risk | Boosts conflicting evidence |

### Prompt Templates (`configs/prompts/`)

Jinja2 templates for LLM interactions:

| Template | Purpose |
|----------|---------|
| `extract_claims.jinja2` | Evidence → structured claims |
| `synthesize_section.jinja2` | Claims → profile section |
| `chat_grounded_answer.jinja2` | Evidence-backed chat responses |
| `continuation_plan.jinja2` | Research planning from instructions |

---

## Project Structure

```
src/dd_platform/
├── main.py                    # FastAPI app entry point
├── settings.py                # Pydantic Settings (env vars)
├── logging.py                 # Structured logging (structlog)
│
├── domain/                    # Pydantic domain models
│   ├── company.py             # Company, CompanyRef, DomainAlias
│   ├── evidence.py            # SourceDocument, Evidence, FreshnessStatus
│   ├── claim.py               # Claim, ClaimContradiction
│   ├── profile.py             # ProfileSnapshot, ProfileSection, RiskSignal
│   ├── schema.py              # ProfileSchema, SectionDefinition, FieldDefinition
│   ├── conversation.py        # Conversation, Message, Citation
│   ├── run.py                 # AgentRun, RunType, RunStatus
│   ├── retrieval.py           # RetrievalResult, RetrievalContext
│   └── evaluation.py          # EvaluationResult, RetrievalExperiment
│
├── providers/                 # External service integrations
│   ├── llm/
│   │   ├── base.py            # LLMAdapter ABC
│   │   ├── models.py          # LLMRequest, LLMResponse, LLMMessage
│   │   └── azure_openai.py    # Azure OpenAI implementation
│   └── search/
│       ├── base.py            # ResearchTool ABC, SearchResult, ToolInput
│       ├── tavily.py          # Tavily search tool
│       ├── serpapi.py         # SerpAPI search tool
│       ├── apify.py           # Apify web crawler
│       └── aggregator.py      # Multi-tool aggregator
│
├── persistence/surreal/       # SurrealDB layer
│   ├── client.py              # Connection management
│   ├── migrations.py          # Schema + index definitions
│   ├── repositories/          # CRUD per entity type
│   │   ├── company_repo.py
│   │   ├── evidence_repo.py
│   │   ├── claim_repo.py
│   │   ├── profile_repo.py
│   │   ├── conversation_repo.py
│   │   └── run_repo.py
│   └── queries/               # Complex graph queries
│       ├── graph_neighbors.py
│       ├── freshness.py
│       └── evidence_search.py
│
├── retrieval/                 # Retrieval layer (GraphRAG)
│   ├── interfaces.py          # Retriever ABC, RetrievalQuery
│   ├── keyword_retriever.py   # Text-based search
│   ├── graph_retriever.py     # Graph traversal retrieval
│   ├── hybrid_retriever.py    # Combines keyword + graph
│   └── assembler.py           # Context assembly for LLM
│
├── orchestration/             # LangGraph workflows
│   ├── state.py               # BuildProfileState (typed workflow state)
│   ├── graph.py               # StateGraph definition + conditional edges
│   └── nodes/                 # Individual workflow steps
│       ├── normalize_company.py
│       ├── load_local_context.py
│       ├── assess_freshness.py
│       ├── plan_research.py
│       ├── retrieve_external_evidence.py
│       ├── extract_claims.py
│       ├── synthesize_profile.py
│       ├── persist_snapshot.py
│       └── finalize_run.py
│
├── application/services/      # Business logic layer
│   ├── profile_service.py     # Orchestrates profile builds
│   ├── chat_service.py        # Evidence-backed chat
│   ├── continuation_service.py # Targeted follow-up research
│   ├── retrieval_service.py   # Direct retrieval search
│   └── schema_service.py      # Schema loading + activation
│
├── api/                       # FastAPI HTTP layer
│   ├── deps.py                # Dependency injection container
│   ├── errors.py              # Typed error handling
│   ├── router.py              # Route assembly
│   └── routes/
│       ├── health.py
│       ├── profile.py
│       ├── chat.py
│       ├── continuation.py
│       ├── retrieval.py
│       └── schemas.py
│
└── utils/                     # Shared utilities
    ├── url_normalization.py   # Canonical company ID resolution
    ├── hashing.py             # SHA-256 content hashing
    ├── ids.py                 # UUID / run ID generation
    └── time.py                # UTC timestamps + freshness checks

configs/
├── schemas/
│   └── due_diligence_v1.yaml  # Default profile schema
├── prompts/
│   ├── extract_claims.jinja2
│   ├── synthesize_section.jinja2
│   ├── chat_grounded_answer.jinja2
│   └── continuation_plan.jinja2
└── retrieval_profiles/
    ├── keyword_only.yaml
    ├── hybrid_basic.yaml
    ├── graph_hybrid_expanded.yaml
    ├── schema_aware_graph_hybrid.yaml
    └── contradiction_aware_graph_hybrid.yaml

tests/
├── conftest.py                # Shared fixtures
├── unit/                      # Fast, no external deps
│   ├── domain/                # Domain model tests
│   ├── utils/                 # Utility function tests
│   ├── retrieval/             # Assembler tests
│   └── services/              # Schema service tests
├── contract/                  # Config + schema validation
└── integration/               # Requires running SurrealDB
```

---

## Development

### Makefile Commands

```bash
make install          # Install all dependencies
make api              # Start API server with hot-reload
make db-up            # Start SurrealDB via Docker
make db-down          # Stop SurrealDB
make db-migrate       # Run database migrations
make format           # Format code (ruff)
make lint             # Lint code (ruff)
make typecheck        # Type check (mypy)
make test             # Run unit + contract tests
make test-unit        # Run unit tests only
make test-integration # Run integration tests (requires DB)
make smoke-profile    # Quick end-to-end smoke test
```

### Adding a New Schema Section

1. Edit `configs/schemas/due_diligence_v1.yaml` — add a new section with fields, TTLs, and retrieval hints
2. Run `make api` — the schema service auto-loads YAML on startup
3. Build a profile — the new section will be included automatically

### Adding a New Research Tool

1. Create `src/dd_platform/providers/search/your_tool.py` implementing the `ResearchTool` ABC
2. Register it in `api/deps.py` inside `AppDependencies.__init__`
3. Reference it in schema retrieval hints or retrieval profiles

---

## Testing

```bash
# Run all fast tests (unit + contract)
make test

# Run with verbose output
uv run pytest tests/unit tests/contract -v

# Run a specific test file
uv run pytest tests/unit/utils/test_url_normalization.py -v

# Run integration tests (requires `make db-up` first)
make test-integration

# Coverage report
uv run pytest tests/unit tests/contract --cov=dd_platform --cov-report=term-missing
```

### Test Tiers

| Tier | Count | Speed | External Deps | What it validates |
|------|-------|-------|---------------|-------------------|
| **Unit** | ~100 | <1s | None | Domain models, utilities, assembler, schema service |
| **Contract** | ~47 | <1s | None | YAML configs, serialization shapes, required keys |
| **Integration** | — | Varies | SurrealDB | DB connectivity, migrations, repository CRUD |

---

## License

Hackathon project — London 2026.
