# design.md — Technical Design for the Company Due Diligence Agent Platform

## 1. Purpose

This document translates `prd.md` into an implementation-facing technical design for coding agents. It is intended to be execution-ready and opinionated enough that autonomous or semi-autonomous coding agents can implement the platform in phases without needing to infer the architecture from scratch.

This is a design for a **working exploratory platform**, not a throwaway prototype. The platform must support:

- operational company profiling for supply-chain due diligence
- persistent storage and graph-native retrieval in SurrealDB
- runtime-configurable profile schemas
- stateful orchestration with LangGraph
- evidence-backed chat against the profile and graph
- continuation research directed by an analyst
- experimentation to measure the impact of GraphRAG on profiling performance

The canonical company identifier is the normalized company main URL host.

Example:

- input URL: `https://www.company.com/`
- canonical company ID: `company:www.company.com`

---

## 2. Design Goals

### 2.1 Functional goals

1. Accept a company URL and produce a due diligence profile.
2. Check SurrealDB first and reuse knowledge when possible.
3. Refresh stale or missing evidence selectively.
4. Materialize profile output under a runtime-selected schema.
5. Persist runs, evidence, claims, graph relationships, snapshots, and conversations.
6. Provide chat and continuation-research APIs backed by GraphRAG retrieval.
7. Enable rapid experimentation with retrieval modes, prompt variants, and graph traversal settings.

### 2.2 Engineering goals

1. Strong module boundaries so coding agents can work in parallel.
2. Deterministic contracts at module boundaries.
3. Type-safe Python code with runtime validation for external inputs.
4. Testable components with minimal hidden side effects.
5. Durable orchestration with resumable state.
6. Observable runs with structured logs, traces, and evaluation metadata.
7. CI validation strict enough to prevent drift and fragile behavior.

### 2.3 Research goals

1. Make GraphRAG strategies configurable at runtime.
2. Persist retrieval decisions and experiment metadata.
3. Compare baseline retrieval with graph-enhanced retrieval on the same company/profile tasks.
4. Measure coverage, groundedness, contradiction handling, latency, and cost.

---

## 3. Recommended Technology Baseline

This document assumes the following baseline unless later architecture decisions replace them intentionally.

- **Language:** Python 3.12+
- **API framework:** FastAPI
- **Validation:** Pydantic v2
- **Workflow engine:** LangGraph
- **LLM access:** Azure OpenAI-compatible endpoint through a provider adapter
- **Database:** SurrealDB
- **Async HTTP:** httpx
- **Task serialization / retry helpers:** tenacity, orq-style internal retry helpers if needed
- **Testing:** pytest, pytest-asyncio, hypothesis, pytest-cov
- **Linting / formatting:** ruff
- **Static typing:** mypy or pyright; prefer mypy initially for Python-native workflows
- **Docs:** MkDocs or docs/ markdown set with generated OpenAPI docs
- **Packaging:** uv or poetry; prefer `uv` for speed and reproducibility if the team accepts it
- **Containerization:** Docker and docker compose for local platform bootstrap

---

## 4. High-Level Architecture

The platform is organized into six primary layers.

### 4.1 API layer

Handles external requests and response contracts.

Responsibilities:

- profile build/update endpoint
- profile retrieval endpoint
- retrieval/debug endpoint
- chat endpoint
- continuation research endpoint
- experiment/evaluation endpoints
- health/metrics endpoints

### 4.2 Orchestration layer

Implemented using LangGraph.

Responsibilities:

- determine whether local data is sufficient
- plan research steps from active profile schema
- call retrieval and web tools
- extract evidence and claims
- synthesize profile fields
- validate profile completeness
- persist artifacts and run state
- support resumable and stateful execution

### 4.3 Retrieval layer

Provides retrieval strategies and context assembly.

Responsibilities:

- keyword retrieval
- graph traversal retrieval
- hybrid retrieval
- section-aware retrieval
- contradiction-aware retrieval
- provenance path ranking
- experiment profile selection

### 4.4 Data layer

Implemented over SurrealDB.

Responsibilities:

- canonical entity persistence
- evidence and claim persistence
- graph edges
- profile snapshots
- materialized current profile view
- conversations and turns
- run metadata, stage outputs, and evaluation records

### 4.5 Tool layer

Uniform abstraction over external research tools.

Responsibilities:

- Tavily search wrapper
- SerpAPI search wrapper
- Apify actor wrapper
- optional internal site crawl wrapper
- normalization into a common evidence envelope

### 4.6 Configuration and experiment layer

Responsibilities:

- active schema resolution
- retrieval profile resolution
- prompt policy selection
- freshness thresholds
- section priorities
- experiment flags and run annotations

---

## 5. End-to-End Runtime Flow

### 5.1 Profile build flow

1. Receive company URL and request options.
2. Normalize URL into canonical company ID.
3. Load active schema and retrieval profile.
4. Query SurrealDB for:
   - company node
   - most recent profile snapshot
   - evidence freshness by section
   - prior runs
   - open contradictions
5. Produce a research plan by schema section.
6. Decide which sections are reusable, stale, or missing.
7. For stale or missing sections, execute web retrieval and extraction.
8. Persist raw evidence and normalized evidence chunks.
9. Extract candidate claims from evidence.
10. Link claims to evidence and company graph nodes.
11. Retrieve additional graph neighborhood where GraphRAG mode requires expansion.
12. Synthesize section outputs under active schema.
13. Validate profile completeness and groundedness.
14. Persist immutable profile snapshot and update current materialized profile view.
15. Store run metrics, costs, retrieval decisions, and evaluation metadata.
16. Return profile summary and run identifiers.

### 5.2 Chat flow

1. Receive profile chat question.
2. Resolve target company and active profile snapshot.
3. Select retrieval profile for chat.
4. Retrieve relevant profile fields, claims, evidence, and graph neighborhood.
5. Assemble grounded context with provenance paths.
6. Generate answer with citations to claim/evidence IDs.
7. Persist conversation turn and referenced artifacts.
8. Optionally derive continuation tasks if requested.

### 5.3 Continuation research flow

1. Receive analyst instruction such as “investigate sanctions exposure further.”
2. Resolve company, active profile, and prior conversation context.
3. Generate research sub-plan targeted to selected schema sections or ad hoc goals.
4. Execute retrieval and extraction only for targeted areas.
5. Persist new evidence, claims, and delta snapshot.
6. Return changes and unresolved questions.

### 5.4 Evaluation flow

1. Select company set, schema, and retrieval profiles to compare.
2. Re-run profiling with different retrieval modes.
3. Persist per-run metrics and evaluation judgments.
4. Compare coverage, groundedness, latency, and cost.
5. Produce experiment report artifacts.

---

## 6. Core Design Decisions

### 6.1 Canonical identity

Use normalized main URL host as the stable company key.

Rules:

- lowercase hostname
- strip protocol, default ports, query, fragment, and trailing slash
- preserve `www` if it is the published primary host, but also store root domain
- store aliases for redirects and alternate hosts
- record normalization provenance in metadata

Primary records:

- `company:{host}` for canonical company entity
- `domain:{host}` for domain/host node if graph separation is useful

### 6.2 Immutable snapshots + mutable current view

Persist two forms:

- **immutable profile snapshots** for reproducibility
- **current materialized profile view** for latest consumption

Why:

- reproducible experiments require immutable snapshots
- operational APIs benefit from a current “best known” view

### 6.3 Evidence-first storage

No material claim should exist without linked evidence unless explicitly marked as inferred, unresolved, or analyst-entered.

### 6.4 Schema-driven orchestration

The system must derive planning, extraction prompts, synthesis steps, and validation from the active profile schema instead of hardcoding section logic.

### 6.5 Retrieval profile abstraction

GraphRAG must be a runtime-selectable behavior, not hardwired into one path.

Example retrieval profiles:

- `baseline_keyword`
- `baseline_hybrid`
- `graph_local`
- `graph_expanded`
- `graph_contradiction_aware`
- `graph_profile_section_focused`

### 6.6 Stateful orchestration

LangGraph state must be serializable and restorable.

The persisted run state should be sufficient to:

- inspect progress
- resume failed runs
- compare execution paths
- analyze cost and performance by stage

---

## 7. Repository Structure

Use a monorepo-style single Python project first. Avoid microservices until there is operational evidence they are necessary.

```text
repo/
├─ pyproject.toml
├─ README.md
├─ Makefile
├─ .env.example
├─ docker-compose.yml
├─ Dockerfile
├─ ruff.toml
├─ mypy.ini
├─ .github/
│  └─ workflows/
│     ├─ ci.yml
│     ├─ docs.yml
│     └─ release.yml
├─ scripts/
│  ├─ bootstrap_local.sh
│  ├─ seed_demo_data.py
│  ├─ run_eval_suite.py
│  ├─ export_graph_snapshot.py
│  └─ smoke_profile_build.py
├─ configs/
│  ├─ app.yaml
│  ├─ schemas/
│  │  ├─ default_due_diligence.yaml
│  │  ├─ supplier_risk_minimal.yaml
│  │  └─ extended_compliance.yaml
│  ├─ retrieval_profiles/
│  │  ├─ baseline_keyword.yaml
│  │  ├─ baseline_hybrid.yaml
│  │  ├─ graph_local.yaml
│  │  ├─ graph_expanded.yaml
│  │  └─ graph_contradiction_aware.yaml
│  ├─ prompts/
│  │  ├─ extract_claims.jinja2
│  │  ├─ synthesize_section.jinja2
│  │  ├─ chat_grounded_answer.jinja2
│  │  └─ continuation_plan.jinja2
│  └─ experiments/
│     └─ default_eval_matrix.yaml
├─ docs/
│  ├─ architecture.md
│  ├─ data-model.md
│  ├─ orchestration.md
│  ├─ retrieval.md
│  ├─ api.md
│  ├─ operations.md
│  ├─ testing.md
│  ├─ adr/
│  │  ├─ 0001-canonical-company-id.md
│  │  ├─ 0002-snapshot-strategy.md
│  │  └─ 0003-retrieval-profile-abstraction.md
│  └─ runbooks/
│     ├─ local-dev.md
│     ├─ failed-run-recovery.md
│     └─ surrealdb-maintenance.md
├─ src/
│  └─ dd_platform/
│     ├─ __init__.py
│     ├─ main.py
│     ├─ settings.py
│     ├─ logging.py
│     ├─ telemetry.py
│     ├─ api/
│     │  ├─ __init__.py
│     │  ├─ deps.py
│     │  ├─ errors.py
│     │  ├─ router.py
│     │  └─ routes/
│     │     ├─ health.py
│     │     ├─ profile.py
│     │     ├─ retrieval.py
│     │     ├─ chat.py
│     │     ├─ continuation.py
│     │     ├─ experiments.py
│     │     └─ admin.py
│     ├─ domain/
│     │  ├─ __init__.py
│     │  ├─ company.py
│     │  ├─ schema.py
│     │  ├─ evidence.py
│     │  ├─ claim.py
│     │  ├─ profile.py
│     │  ├─ conversation.py
│     │  ├─ run.py
│     │  ├─ retrieval.py
│     │  └─ evaluation.py
│     ├─ application/
│     │  ├─ __init__.py
│     │  ├─ services/
│     │  │  ├─ profile_service.py
│     │  │  ├─ chat_service.py
│     │  │  ├─ continuation_service.py
│     │  │  ├─ retrieval_service.py
│     │  │  ├─ evaluation_service.py
│     │  │  └─ schema_service.py
│     │  ├─ planners/
│     │  │  ├─ research_planner.py
│     │  │  ├─ refresh_planner.py
│     │  │  └─ continuation_planner.py
│     │  ├─ assemblers/
│     │  │  ├─ context_assembler.py
│     │  │  └─ profile_assembler.py
│     │  └─ validators/
│     │     ├─ groundedness.py
│     │     ├─ profile_completeness.py
│     │     └─ schema_validation.py
│     ├─ orchestration/
│     │  ├─ __init__.py
│     │  ├─ state.py
│     │  ├─ graph.py
│     │  ├─ nodes/
│     │  │  ├─ normalize_company.py
│     │  │  ├─ load_local_context.py
│     │  │  ├─ assess_freshness.py
│     │  │  ├─ plan_research.py
│     │  │  ├─ retrieve_external_evidence.py
│     │  │  ├─ persist_evidence.py
│     │  │  ├─ extract_claims.py
│     │  │  ├─ expand_graph_context.py
│     │  │  ├─ synthesize_profile.py
│     │  │  ├─ validate_profile.py
│     │  │  ├─ persist_snapshot.py
│     │  │  └─ finalize_run.py
│     │  └─ policies/
│     │     ├─ freshness_policy.py
│     │     ├─ retrieval_policy.py
│     │     └─ retry_policy.py
│     ├─ providers/
│     │  ├─ __init__.py
│     │  ├─ llm/
│     │  │  ├─ base.py
│     │  │  ├─ azure_openai.py
│     │  │  ├─ models.py
│     │  │  └─ structured_output.py
│     │  ├─ search/
│     │  │  ├─ base.py
│     │  │  ├─ tavily.py
│     │  │  ├─ serpapi.py
│     │  │  ├─ apify.py
│     │  │  ├─ aggregator.py
│     │  │  └─ normalizer.py
│     │  └─ embeddings/
│     │     ├─ base.py
│     │     └─ azure_openai_embeddings.py
│     ├─ retrieval/
│     │  ├─ __init__.py
│     │  ├─ interfaces.py
│     │  ├─ models.py
│     │  ├─ query_planner.py
│     │  ├─ keyword_retriever.py
│     │  ├─ graph_retriever.py
│     │  ├─ hybrid_retriever.py
│     │  ├─ reranker.py
│     │  ├─ provenance.py
│     │  ├─ contradiction.py
│     │  └─ section_context.py
│     ├─ persistence/
│     │  ├─ __init__.py
│     │  ├─ surreal/
│     │  │  ├─ client.py
│     │  │  ├─ schema.surql
│     │  │  ├─ migrations.py
│     │  │  ├─ repositories/
│     │  │  │  ├─ company_repo.py
│     │  │  │  ├─ evidence_repo.py
│     │  │  │  ├─ claim_repo.py
│     │  │  │  ├─ profile_repo.py
│     │  │  │  ├─ conversation_repo.py
│     │  │  │  ├─ run_repo.py
│     │  │  │  ├─ retrieval_repo.py
│     │  │  │  └─ evaluation_repo.py
│     │  │  └─ queries/
│     │  │     ├─ freshness.py
│     │  │     ├─ graph_neighbors.py
│     │  │     ├─ evidence_search.py
│     │  │     └─ profile_views.py
│     ├─ prompts/
│     │  ├─ __init__.py
│     │  ├─ loader.py
│     │  ├─ renderer.py
│     │  └─ templates.py
│     ├─ experiments/
│     │  ├─ __init__.py
│     │  ├─ models.py
│     │  ├─ runner.py
│     │  ├─ comparator.py
│     │  └─ reporting.py
│     ├─ utils/
│     │  ├─ __init__.py
│     │  ├─ url_normalization.py
│     │  ├─ hashing.py
│     │  ├─ time.py
│     │  ├─ ids.py
│     │  └─ json.py
│     └─ cli/
│        ├─ __init__.py
│        ├─ profile.py
│        ├─ eval.py
│        └─ admin.py
└─ tests/
   ├─ unit/
   │  ├─ domain/
   │  ├─ application/
   │  ├─ orchestration/
   │  ├─ retrieval/
   │  ├─ providers/
   │  └─ persistence/
   ├─ integration/
   │  ├─ api/
   │  ├─ surreal/
   │  ├─ providers/
   │  └─ orchestration/
   ├─ contract/
   │  ├─ schemas/
   │  ├─ prompts/
   │  └─ api/
   ├─ eval/
   │  ├─ datasets/
   │  ├─ golden/
   │  └─ regression/
   ├─ performance/
   │  ├─ retrieval/
   │  └─ end_to_end/
   └─ fixtures/
      ├─ companies/
      ├─ evidence/
      ├─ claims/
      ├─ api/
      └─ providers/
```

---

## 8. Module Responsibilities

### 8.1 `api/`

The API package should be thin. It must not contain business logic beyond request parsing, dependency injection, and response shaping.

Key responsibilities:

- request validation
- auth hook points for future expansion
- correlation ID handling
- mapping application exceptions to HTTP errors
- OpenAPI annotations

### 8.2 `domain/`

Pure domain types and business invariants.

Examples:

- `CompanyRef`
- `EvidenceRecord`
- `ClaimRecord`
- `ProfileSnapshot`
- `RetrievalProfile`
- `RunRecord`
- `ConversationTurn`

Keep this layer free from HTTP, database, or provider SDK details.

### 8.3 `application/`

Coordinates use cases and calls into repositories/providers.

This layer owns:

- build profile use case
- retrieve profile use case
- chat use case
- continuation research use case
- evaluation use case

### 8.4 `orchestration/`

Contains LangGraph-specific wiring and node implementations.

Node design rules:

- each node must have one primary responsibility
- node input/output must be explicit in typed state
- external I/O must be isolated to nodes or called services
- nodes should be deterministic when given identical state and mocked dependencies

### 8.5 `providers/`

All external service integrations live here.

Rules:

- provide a common interface and provider-specific implementation
- return normalized models instead of raw SDK payloads
- never leak provider-specific response shapes outside the provider package
- support tracing and request cost metadata where possible

### 8.6 `retrieval/`

This package should be one of the platform’s most explicit and well-tested areas because GraphRAG evaluation is central to the product.

Responsibilities:

- retrieval planning
- graph traversal
- result merging and scoring
- provenance path construction
- contradiction signal detection
- context packing for LLM prompts

### 8.7 `persistence/`

Only repositories and database utilities. Do not place business logic here.

Repository rules:

- repositories expose domain models
- query helpers may return raw shapes internally, but repositories translate them
- all writes should be idempotent where practical
- prefer explicit query functions instead of giant “generic repository” patterns

### 8.8 `experiments/`

Treat evaluation as a built-in platform capability, not an afterthought.

Responsibilities:

- define experiment matrices
- run repeated profiling under different retrieval profiles
- compare runs on fixed tasks
- produce reproducible reports

---

## 9. Configuration Design

All operational behavior that may change between experiments or deployments should be externalized.

### 9.1 Configuration categories

1. **app config**
   - API settings
   - default timeouts
   - concurrency limits
   - feature flags

2. **schema config**
   - profile section definitions
   - field types
   - required/optional flags
   - freshness expectations
   - section retrieval hints

3. **retrieval profile config**
   - retrievers enabled
   - graph hop limits
   - top-k values
   - reranking mode
   - contradiction handling mode
   - context packing policy

4. **prompt config**
   - prompt templates
   - model routing rules
   - output schema selectors

5. **evaluation config**
   - datasets
   - target schemas
   - retrieval profiles to compare
   - scoring heuristics

### 9.2 Configuration loading rules

- load immutable defaults from repository config files
- support environment override for deployment-specific values
- validate config with Pydantic models
- include config version in run metadata
- reject invalid schema at startup or activation time

---

## 10. Profile Schema Design

The profile schema must be runtime-configurable and used for planning, extraction, synthesis, validation, and response formatting.

### 10.1 Schema structure

Recommended schema structure:

```yaml
name: default_due_diligence
version: 1
sections:
  - key: company_identity
    title: Company Identity
    required: true
    freshness_days: 180
    retrieval_hints:
      preferred_sources: [official_site, serpapi]
      graph_entities: [company, domain]
    fields:
      - key: legal_name
        type: string
        required: true
      - key: headquarters
        type: string
        required: false
  - key: compliance_risk
    title: Compliance Risk
    required: true
    freshness_days: 30
    retrieval_hints:
      preferred_sources: [tavily, serpapi, apify]
      graph_entities: [company, sanction_signal, litigation_signal]
    fields:
      - key: sanctions_signal
        type: enum
        values: [none_found, signal_detected, unresolved]
      - key: litigation_signal
        type: enum
        values: [none_found, signal_detected, unresolved]
```

### 10.2 Schema usage points

The active schema must drive:

- section planning
- freshness policy checks
- retrieval query generation
- extraction prompt generation
- section synthesis prompt generation
- completeness validation
- chat answer formatting when a schema field is referenced

### 10.3 Schema evolution

When schema changes:

- do not mutate old snapshots to fit the new schema
- create new snapshots under the new schema version
- maintain compatibility mapping where useful
- expose which schema version each snapshot uses

---

## 11. SurrealDB Design

SurrealDB is used as a graph store and durable object store.

### 11.1 Core record types

Recommended record groups:

- `company`
- `domain`
- `source`
- `evidence`
- `claim`
- `profile_snapshot`
- `profile_current`
- `conversation`
- `conversation_turn`
- `run`
- `retrieval_event`
- `evaluation_run`
- `schema_version`

### 11.2 Suggested graph edges

Examples:

- `company -> has_domain -> domain`
- `company -> has_evidence -> evidence`
- `evidence -> supports -> claim`
- `claim -> belongs_to -> profile_snapshot`
- `profile_snapshot -> for_company -> company`
- `conversation_turn -> references_claim -> claim`
- `conversation_turn -> references_evidence -> evidence`
- `run -> executed_for -> company`
- `run -> produced -> profile_snapshot`
- `run -> used_retrieval_profile -> retrieval_profile_record`
- `claim -> contradicts -> claim`
- `claim -> mentions_entity -> company|domain|person|location|risk_signal`

### 11.3 Record design principles

- include `created_at`, `updated_at`, `source_run_id`, `schema_version`, and `provenance`
- store `confidence`, `freshness_state`, and `validation_state` where relevant
- evidence should store both raw source metadata and normalized chunk data
- claims should store canonicalized semantic content and linked field candidates

### 11.4 SurrealDB query categories

Implement query helpers for:

- fetch latest profile snapshot by company and schema
- fetch freshness by section
- fetch evidence by source type/date/company
- graph neighborhood expansion by hop and entity type
- retrieve contradiction-linked claims
- search evidence/claims by field candidate or section tag
- write immutable snapshot + update current profile atomically where possible

### 11.5 Migration strategy

- keep all SurrealDB DDL or migration scripts under version control
- migrations must be replayable in local environments
- schema changes must include backward-compatibility notes
- add a migration smoke test in CI

---

## 12. GraphRAG Design

GraphRAG is a first-class retrieval capability and one of the main subjects of experimentation.

### 12.1 GraphRAG objectives

Use graph structure to improve:

- evidence recall across related artifacts
- section-specific context assembly
- contradiction detection
- provenance quality
- analyst trust through traceable evidence paths

### 12.2 Retrieval primitives

Implement retrieval using composable primitives:

1. **keyword retrieval**
   - evidence text matching
   - source title and metadata filters

2. **vector retrieval**
   - optional if embeddings are available and cost justified
   - semantic matching for evidence and claim text

3. **graph neighborhood retrieval**
   - expand from company node through selected edge types
   - hop-limited traversal with edge weighting

4. **section-aware filtering**
   - constrain candidates by schema section tags and field mappings

5. **provenance path ranking**
   - prefer candidates with short, high-confidence support paths

6. **contradiction-aware retrieval**
   - surface conflicting claims and supporting evidence in one retrieval bundle

### 12.3 Retrieval profiles

Each profile should be a config file defining behavior such as:

- enabled retrievers
- graph expansion depth
- top-k per retriever
- merge weights
- reranking method
- max tokens per context pack
- contradiction inclusion mode

### 12.4 Query planning

For each task, the retrieval layer should transform user or orchestration intent into:

- query text
- target sections
- graph seed nodes
- required source classes
- freshness constraints
- retrieval profile settings

### 12.5 Context assembly

The context assembler must:

- deduplicate overlapping evidence
- keep provenance links intact
- include conflicting evidence when requested or when risk of contradiction is high
- build section-specific context blocks rather than one giant unstructured dump
- cap context size while preserving diversity of sources

### 12.6 Provenance format

Every retrieval bundle should include:

- source IDs
- evidence IDs
- claim IDs
- graph path summaries
- retrieval rationale metadata

### 12.7 GraphRAG experimentation requirements

For every profile build or chat run, persist:

- retrieval profile name and version
- graph expansion parameters
- candidate counts by retriever
- final included context counts
- reranking metadata
- latency by retrieval stage
- token and provider cost by stage if available

### 12.8 Baselines

The evaluation system must always support comparison against at least one non-graph baseline.

Recommended minimum comparison set:

- `baseline_keyword`
- `baseline_hybrid`
- `graph_local`
- `graph_expanded`

---

## 13. LLM Provider Design

### 13.1 Adapter interface

Create a stable interface such as:

- `generate_text()`
- `generate_structured()`
- `embed_texts()` if embeddings are used

### 13.2 Azure adapter responsibilities

- endpoint configuration
- deployment/model mapping
- retries and timeout handling
- request/response normalization
- usage and cost metadata capture
- structured output support where possible

### 13.3 Prompting rules

- prompts live in templates, not inline code
- all prompts require versioning
- use structured output for extraction and synthesis where possible
- include evidence IDs in prompts whenever grounded output is required

### 13.4 Model routing

Separate model usage by task type where beneficial:

- lower-latency model for planning/routing
- stronger model for synthesis and grounded chat
- embeddings deployment for vector retrieval if adopted

---

## 14. Search Tool Design

### 14.1 Common search interface

All search providers should expose a normalized search method with a common result envelope.

Normalized result fields should include:

- title
- url
- snippet
- source provider
- retrieval timestamp
- rank
- raw payload reference

### 14.2 Provider usage guidance

- **Tavily:** broad topical search and extraction-rich workflows
- **SerpAPI:** search engine coverage and result diversity
- **Apify:** targeted site crawling, structured page extraction, or actor-based pipelines

### 14.3 Aggregation strategy

The search aggregator should support:

- fan-out to multiple providers
- provider-specific quotas and priority ordering
- deduplication by canonical URL/content hash
- provenance preservation per provider

### 14.4 Crawling policy

- respect robots and terms-of-use constraints configured by operations
- limit crawl depth by policy
- prefer official site pages for core identity fields
- preserve crawl metadata such as fetch time, actor, and crawl depth

---

## 15. LangGraph Orchestration Design

### 15.1 State object

The LangGraph state should be explicit and typed.

Suggested state fields:

- request metadata
- canonical company ref
- active schema
- retrieval profile
- known local profile/evidence summary
- freshness assessment by section
- research plan
- retrieved evidence
- extracted claims
- graph expansion results
- synthesized profile draft
- validation results
- persistence results
- metrics/cost/errors

### 15.2 Node sequence

Recommended initial sequence:

1. `normalize_company`
2. `load_local_context`
3. `assess_freshness`
4. `plan_research`
5. conditional branch:
   - reuse local only
   - retrieve external evidence
6. `persist_evidence`
7. `extract_claims`
8. optional `expand_graph_context`
9. `synthesize_profile`
10. `validate_profile`
11. `persist_snapshot`
12. `finalize_run`

### 15.3 Branching rules

Branch on:

- freshness sufficient / insufficient
- retrieval mode requiring graph expansion / not requiring it
- profile validation pass / repair needed
- provider failure recoverable / unrecoverable

### 15.4 Recovery and resumability

- persist state checkpoint after every meaningful stage
- include stage status and error detail in run record
- allow rerun from a failed stage where safe
- make external side effects idempotent where possible

---

## 16. API Design

### 16.1 Main endpoints

Recommended first-class endpoints:

- `POST /api/v1/profiles/build`
- `GET /api/v1/profiles/{company_id}`
- `GET /api/v1/profiles/{company_id}/snapshots`
- `POST /api/v1/retrieval/search`
- `POST /api/v1/chat`
- `POST /api/v1/continuation`
- `POST /api/v1/experiments/run`
- `GET /api/v1/runs/{run_id}`
- `GET /health`

### 16.2 Request examples

#### Build profile

```json
{
  "company_url": "https://www.company.com",
  "schema": "default_due_diligence",
  "retrieval_profile": "graph_expanded",
  "force_refresh": false,
  "target_sections": ["company_identity", "compliance_risk"],
  "chat_context_id": null
}
```

#### Chat

```json
{
  "company_id": "company:www.company.com",
  "question": "What are the main compliance risks and what evidence supports them?",
  "retrieval_profile": "graph_contradiction_aware",
  "snapshot_id": null
}
```

#### Continuation research

```json
{
  "company_id": "company:www.company.com",
  "instruction": "Investigate ownership and sanctions-related exposure in more depth",
  "target_sections": ["ownership", "compliance_risk"],
  "retrieval_profile": "graph_expanded"
}
```

### 16.3 Response design principles

- return stable typed shapes
- include `run_id`, `schema_version`, and `retrieval_profile`
- include profile freshness summary
- include evidence/citation references where applicable
- expose unresolved sections explicitly

### 16.4 API versioning

Namespace APIs under `/api/v1`. Breaking changes require version bump or additive rollout policy.

---

## 17. Validation Model

Validation is not a single step. It is a layered design discipline.

### 17.1 Input validation

Validate:

- company URL format
- schema existence
- retrieval profile existence
- endpoint payload shape
- section keys against schema

### 17.2 Data validation

Validate:

- provider responses into normalized search/evidence models
- LLM structured outputs into claim/profile models
- persistence write payloads before DB interaction

### 17.3 Profile validation

Validate:

- required fields present or explicitly unresolved
- evidence coverage for material fields
- contradiction markers surfaced where detected
- freshness state computed per section
- schema conformance for output snapshot

### 17.4 Run validation

Before marking a run successful:

- all required stages reached terminal state
- snapshot persisted
- current profile view updated if applicable
- metrics stored
- no unresolved fatal validation failures

---

## 18. Testing Strategy

Testing is a core platform requirement because the system is both operational and experimental.

### 18.1 Test categories

#### Unit tests

Focus on pure logic and small modules.

Must cover:

- URL normalization
- schema loading/validation
- freshness rules
- retrieval profile parsing
- ranking and dedup rules
- contradiction detection heuristics
- state transitions in orchestration utilities

#### Integration tests

Focus on boundaries across modules.

Must cover:

- FastAPI with app dependencies
- SurrealDB repositories against a real local DB instance
- provider clients with mocked external services
- LangGraph runs over a realistic small fixture company

#### Contract tests

Focus on stability of:

- API schemas
- config file schemas
- prompt-rendering variables
- repository return shapes
- structured LLM outputs

#### Evaluation tests

Focus on profiling quality and GraphRAG outcomes.

Must cover:

- golden-company datasets with expected fields or evidence
- comparison of baseline vs graph profiles
- groundedness checks on chat answers
- regression detection on coverage and contradiction handling

#### Performance tests

Focus on:

- retrieval latency
- graph expansion cost
- end-to-end profile build time
- memory behavior under repeated retrieval

#### Resilience tests

Focus on:

- provider timeouts
- partial provider failure
- retry behavior
- resume after run interruption
- duplicate request idempotency

### 18.2 Test data strategy

Maintain a stable set of fixture companies representing diverse scenarios:

- simple official-site-only company
- multi-page company with richer metadata
- company with conflicting signals across sources
- company with sparse public presence
- company with repeated prior snapshots for freshness testing

### 18.3 LLM testing strategy

Because LLM outputs are probabilistic, use layered validation:

- mock provider responses for deterministic unit tests
- run contract tests against structured output schemas
- use golden evaluations for prompt regressions
- prefer assert ranges and invariants over brittle exact string matching

### 18.4 Minimum quality gates

A merge should fail if any of the following fail:

- formatting/linting
- type checks
- unit tests
- integration smoke tests
- API contract tests
- config/schema validation tests

Nightly or scheduled CI should run heavier suites:

- evaluation regression suite
- performance smoke suite
- migration replay suite

---

## 19. Code Validation Commands

The repository should expose simple standard commands so coding agents do not invent their own.

Recommended commands:

```bash
make format
make lint
make typecheck
make test
make test-unit
make test-integration
make test-contract
make test-eval
make test-performance
make db-up
make db-migrate
make api
make smoke-profile
```

### 19.1 Expected command behavior

- `make format`: run formatter and import cleanup if configured
- `make lint`: run ruff with fail-on-warning policy for agreed rules
- `make typecheck`: run mypy on `src/`
- `make test`: run all required fast CI suites
- `make smoke-profile`: build a sample profile end to end against local services

### 19.2 Suggested CI order

1. install dependencies
2. validate config files
3. lint
4. typecheck
5. run unit tests
6. start local SurrealDB service
7. apply migrations
8. run integration and contract tests
9. publish coverage and artifacts

---

## 20. Observability and Debuggability

### 20.1 Structured logging

Every request and run must emit structured logs with:

- correlation ID
- run ID
- company ID
- schema version
- retrieval profile
- stage name
- latency
- provider/tool metadata

### 20.2 Metrics

Track at minimum:

- request counts and failure rates
- run stage durations
- retrieval counts by provider and mode
- graph expansion sizes
- token usage and cost by stage
- profile success/failure rates
- chat grounded answer rates where measured

### 20.3 Traceability

Persist enough metadata to reconstruct:

- which evidence produced which claim
- which claims fed which profile fields
- which retrieval decisions formed each context pack
- which prompts and model versions were used

---

## 21. Documentation Guidelines for Coding Agents

Documentation is required deliverable work, not cleanup work.

### 21.1 Every meaningful feature PR must include

- code changes
- tests
- docs updates if behavior or architecture changed
- ADR entry if a major architecture decision changed

### 21.2 Required documents to keep current

- `README.md` for project bootstrap
- `docs/architecture.md` for current system design
- `docs/data-model.md` for SurrealDB entities and edges
- `docs/retrieval.md` for GraphRAG strategies and retrieval profiles
- `docs/api.md` for endpoint semantics
- `docs/testing.md` for validation strategy
- `docs/runbooks/*` for operations and recovery steps

### 21.3 Documentation style rules

- write what the code does now, not what it might do later
- include example requests and responses
- include failure cases and troubleshooting notes
- keep diagrams text-first or Mermaid for versionable docs

---

## 22. Implementation Phases

The phases below are intended for coding agents. Each phase has required outputs and validation criteria.

### Phase 0 — Foundation and project bootstrap

#### Objectives

- create repository structure
- set up packaging, linting, typing, testing, local dev tooling
- define settings and config loading
- bootstrap local FastAPI app and SurrealDB connection

#### Deliverables

- repo skeleton
- `pyproject.toml`
- local compose file
- settings models
- health endpoint
- CI workflow skeleton
- migration bootstrap

#### Validation

- app boots locally
- health endpoint responds
- config loads and validates
- CI lint/type/test-unit passes

### Phase 1 — Core domain and persistence

#### Objectives

- implement domain models
- implement SurrealDB repositories and migrations
- support company, evidence, claim, snapshot, and run persistence

#### Deliverables

- domain models
- repository interfaces and initial implementations
- migration scripts
- sample seed data

#### Validation

- repository integration tests pass against local SurrealDB
- create/read/update flows work for key entities
- migrations replay from empty DB

### Phase 2 — Provider adapters

#### Objectives

- implement Azure LLM adapter
- implement Tavily, SerpAPI, and Apify wrappers
- normalize outputs into common models

#### Deliverables

- provider interfaces
- provider implementations
- mockable test harnesses
- normalized evidence/result models

#### Validation

- provider unit tests pass with mocked responses
- timeout and retry behavior verified
- structured output parsing tests pass

### Phase 3 — Retrieval foundation

#### Objectives

- implement retrieval interfaces and baseline strategies
- add section-aware context assembly
- add provenance representation

#### Deliverables

- keyword retriever
- hybrid retriever
- context assembler
- retrieval profile config loader

#### Validation

- retrieval tests show deterministic ranking on fixtures
- context assembly preserves citations and diversity
- retrieval endpoint smoke test passes

### Phase 4 — GraphRAG and graph expansion

#### Objectives

- implement graph neighborhood retrieval
- add contradiction-aware retrieval and provenance path ranking
- persist retrieval events for evaluation

#### Deliverables

- graph retriever
- contradiction handling module
- graph expansion query helpers
- retrieval event persistence

#### Validation

- graph retrieval integration tests pass
- contradiction-linked claims surface in relevant cases
- evaluation fixtures show graph mode differs from baseline in measurable ways

### Phase 5 — LangGraph orchestration

#### Objectives

- implement state model and graph nodes
- support local-data-first refresh logic
- synthesize and validate profile snapshots

#### Deliverables

- LangGraph state
- node implementations
- build profile workflow
- run checkpoint persistence

#### Validation

- end-to-end profile build passes for fixture companies
- rerun of same company reuses fresh data
- failed run can resume from checkpoint where supported

### Phase 6 — Chat and continuation research

#### Objectives

- implement profile-grounded chat
- implement continuation research flow
- persist conversations and deltas

#### Deliverables

- chat service and endpoint
- continuation planner/service and endpoint
- conversation repositories

#### Validation

- chat answers contain citations
- continuation run updates targeted sections only when appropriate
- conversation history retrieval works

### Phase 7 — Evaluation platform

#### Objectives

- build experiment runner and reporting
- compare retrieval profiles across fixture datasets
- expose evaluation metrics and reports

#### Deliverables

- experiment config loader
- runner/comparator/reporting modules
- CLI or API for experiment execution
- baseline datasets and golden cases

#### Validation

- same company set can be run under multiple retrieval profiles
- metrics persisted and comparable
- regression suite flags degraded performance

### Phase 8 — Hardening and operating guidelines

#### Objectives

- improve observability, docs, resilience, and operational runbooks
- finalize engineering guidance for long-lived platform use

#### Deliverables

- runbooks
- expanded docs
- performance smoke tests
- failure recovery procedures

#### Validation

- local bootstrap docs are reproducible from scratch
- runbooks cover top failure modes
- performance and resilience suites pass agreed thresholds

---

## 23. Phase Exit Criteria

A phase is not complete when code exists. It is complete only when all exit criteria are met.

### Common exit criteria for every phase

- code merged and typed
- tests added and passing
- documentation updated
- config changes validated
- example or smoke command available where relevant
- no TODO placeholders in critical paths unless explicitly logged in backlog

### Additional exit criteria for platform-critical phases

For Phases 4–7 additionally require:

- evaluation or regression coverage added
- observability hooks added
- example artifacts captured in docs or fixtures

---

## 24. Coding Rules for Agents

1. Do not hardcode schema-specific logic into orchestration nodes if it can be config-driven.
2. Do not leak provider-specific payload shapes outside provider modules.
3. Do not bypass repositories to issue ad hoc DB writes from services.
4. Prefer typed models over raw dictionaries for all internal boundaries.
5. Keep prompts in templates and version them.
6. Add tests in the same change as implementation.
7. Update docs when behavior changes.
8. Log with structured metadata, not free-form strings only.
9. Preserve provenance through all transformations.
10. Fail explicitly when groundedness or schema validation requirements are unmet.

---

## 25. Definition of Done for Coding Agents

A task is done only if all of the following are true:

- implementation satisfies the design intent
- tests exist and pass at the right level
- types and lint pass
- docs were updated if behavior changed
- there is a clear validation path for reviewers
- observability hooks were added for non-trivial runtime behavior
- no critical provenance or persistence gaps remain

For workflow tasks, “done” additionally requires a successful local smoke run.

---

## 26. Recommended First Execution Order for Coding Agents

If work must begin immediately, use this order:

1. Phase 0 foundation
2. Phase 1 persistence and domain
3. Phase 2 providers
4. Phase 3 retrieval baseline
5. Phase 5 orchestration shell with local-only reuse path
6. Phase 4 graph retrieval expansion
7. Phase 6 chat and continuation
8. Phase 7 evaluation framework
9. Phase 8 hardening

This order is intentionally not fully linear relative to numbering. It prioritizes a thin end-to-end vertical slice before deeper GraphRAG experimentation.

---

## 27. Initial Validation Checklist

Before coding agents declare the platform “usable”, verify all of the following:

- a company URL can be submitted to the API
- the system canonicalizes the company ID correctly
- SurrealDB is checked before external retrieval
- stale and missing sections trigger targeted research
- evidence and claims persist with provenance
- profile snapshots are immutable and queryable
- current profile view is available
- chat answers cite evidence and claims
- continuation research produces a delta rather than blind rebuild where possible
- at least one baseline retrieval mode and one graph retrieval mode are comparable
- evaluation results are persisted and inspectable
- docs explain how to run, test, and debug the system

---

## 28. Open Design Questions to Track as ADRs

These are expected evolution areas and should be managed explicitly through ADRs instead of informal drift.

1. whether to add embeddings from day one or after baseline graph retrieval is stable
2. how far to separate `company` and `domain` as first-class graph nodes
3. whether chat uses the latest current profile or an explicit immutable snapshot by default
4. how contradiction scoring should work across source reliability levels
5. how to version prompt templates and evaluation datasets across releases
6. what operational freshness defaults are appropriate per schema section
7. whether long-running builds need external job queueing beyond synchronous API-triggered orchestration

---

## 29. Final Guidance

Coding agents should optimize for:

- correctness before cleverness
- provenance before polish
- modularity before premature optimization
- experiment traceability before broad feature sprawl

The distinctive value of this platform is not merely “agentic profiling.” It is the combination of:

- durable stateful profiling
- graph-native evidence and claim storage
- schema-driven orchestration
- evidence-backed analyst interaction
- measurable GraphRAG experimentation

Any implementation choice that weakens those properties should be treated as suspect and reviewed explicitly.
