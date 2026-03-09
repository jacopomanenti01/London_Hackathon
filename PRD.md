# PRD: Company Due Diligence Agent Platform

## 1. Document Control

**Product name:** Company Due Diligence Agent Platform  
**Document type:** Product Requirements Document + Engineering Delivery Guidelines  
**Primary audience:** Coding agents, engineers, platform architects, and evaluators  
**Status:** Implementation-ready draft for platform delivery  
**Owner:** Product owner  
**Target stack:** Python, FastAPI, LangGraph, Azure OpenAI-compatible LLM endpoint, SurrealDB, Tavily, SerpAPI, Apify

---

## 2. Executive Summary

Build a production-grade exploratory platform for supply-chain due diligence profiling of companies, using the company’s main URL as the canonical identifier. The platform must not be framed as a throwaway PoC. It must be designed as a durable working system that supports repeated profiling, targeted refresh, evidence-backed chat, continuation research, observability, controlled experimentation, and ongoing comparison of GraphRAG strategies.

The core system flow is:

1. Accept a company main URL such as `www.company.com`
2. Normalize it into the canonical company ID
3. Check SurrealDB for existing profile snapshots, evidence, claims, graph neighborhood, freshness state, and prior runs
4. Decide what can be reused and what must be refreshed
5. Use web tools selectively to fetch new evidence when needed
6. Extract claims and synthesize a due diligence profile under the active schema
7. Persist all intermediate and final artifacts in SurrealDB
8. Expose chat and continuation workflows grounded in profile, claims, evidence, and graph relations
9. Measure how different GraphRAG retrieval strategies affect profile quality, evidence coverage, latency, and cost

This platform is explicitly exploratory. A major purpose is to test whether graph-enhanced RAG improves profiling performance compared with simpler retrieval strategies. The architecture must therefore support controlled experimentation, feature flags, retrieval mode switching, offline evaluation, and auditability.

---

## 3. Product Intent

This is a **working platform** for repeated use, benchmarking, and evolution. It is not only an initial scaffold.

The platform must support three parallel outcomes:

1. **Operational profiling** for real company due diligence workflows
2. **Research and experimentation** on GraphRAG performance and retrieval design
3. **Engineering extensibility** so new schemas, tools, prompts, and retrieval policies can be added without destabilizing the core system

---

## 4. Problem Statement

Supply-chain due diligence requires timely, structured, explainable, and refreshable company intelligence. Relevant facts are distributed across official company websites, public pages, search results, structured crawls, and broader web content. Manual workflows are slow, inconsistent, expensive, and difficult to reproduce.

The platform must solve the following:

1. **Canonical identity resolution** across repeated company requests
2. **Incremental refresh** so repeated runs reuse existing knowledge instead of redoing work
3. **Schema-driven profiling** so profile structure can change without rewriting orchestration logic
4. **Graph-backed explainability** so users can inspect evidence, claims, contradictions, and provenance paths
5. **Interactive continuation** so analysts can steer deeper research after the initial profile
6. **Experimental GraphRAG evaluation** so the team can test which retrieval strategies improve due diligence outcomes

---

## 5. Product Goals

### 5.1 Primary goals

- Deliver a production-oriented Python platform for building, updating, storing, and chatting with company due diligence profiles
- Use the normalized company main URL as the canonical company identifier
- Support Azure-hosted LLMs via a clean provider adapter
- Support Tavily, SerpAPI, and Apify behind stable tool interfaces
- Persist company knowledge, graph relationships, evidence, claims, runs, conversations, schema versions, and experimental metadata in SurrealDB
- Use LangGraph to orchestrate stateful and resumable workflows
- Make profile schema runtime-configurable and hot-swappable
- Enable evidence-backed chat and targeted continuation research
- Treat GraphRAG as a first-class capability rather than an optional add-on
- Instrument the platform so the effect of GraphRAG on profiling quality can be evaluated over time

### 5.2 Secondary goals

- Support hybrid retrieval across graph, keyword, vector, and structured filters
- Surface contradictions rather than silently merging them away
- Allow retrieval strategies to be toggled per run for benchmarking
- Support durable profile snapshots and current materialized views
- Make evidence freshness and confidence explicit per field and per section

---

## 6. Non-Goals

The following are not required in the first production platform cut, but the architecture should not block them later:

- Full end-user UI application
- OCR-heavy document intelligence pipelines
- Paid proprietary datasets beyond Tavily, SerpAPI, Apify, and public web sources
- Full legal entity resolution across all subsidiaries and beneficial ownership chains
- Final compliance decisions or legal certification
- Complex tenancy, billing, or reviewer workflow systems

---

## 7. Platform Principles

1. **Evidence first** — no material profile field should exist without supporting evidence unless explicitly marked unknown or inferred
2. **Graph native** — evidence, claims, profile fields, conversations, risks, and runs are graph-linked entities, not isolated blobs
3. **Schema driven** — planning, extraction, synthesis, validation, and chat formatting must derive from active schema configuration
4. **Incremental by default** — the system checks local knowledge first and only refreshes what is necessary
5. **Experiment friendly** — retrieval modes, prompts, ranking policies, and graph expansion logic must be configurable and measurable
6. **Explainable** — responses and profile outputs must expose evidence path, confidence, freshness, and contradiction state
7. **Durable** — all major runs are restartable or resumable from persisted state
8. **Composable** — adding a new tool, schema section, or retrieval policy should not require rewriting the whole system

---

## 8. Primary Users and Jobs to Be Done

### 8.1 Primary users

- Supply-chain risk analysts
- Internal operations teams
- Engineers and research teams evaluating GraphRAG effectiveness

### 8.2 Core jobs

- Submit a company URL and obtain a due diligence profile
- Reuse prior knowledge when the same company is profiled again
- Understand which facts are fresh, stale, contradictory, or unknown
- Ask questions against the profile and see evidence-backed answers
- Direct agents to continue research into specific areas
- Compare retrieval strategies and see how GraphRAG affects outcomes
- Modify the profile schema without rewriting core orchestration

---

## 9. Key Concepts

### 9.1 Canonical company identifier

The canonical identifier is the normalized company main URL host.

Example:

- Input: `www.company.com/`
- Canonical ID: `company:www.company.com`
- Canonical host: `www.company.com`
- Root domain: `company.com`

### 9.2 Evidence

A retrieved source fragment or normalized content segment used to support claims or profile fields.

### 9.3 Claim

A normalized statement derived from one or more pieces of evidence, such as headquarters, certification, sanctions exposure signal, litigation signal, or ownership statement.

### 9.4 Profile snapshot

An immutable, schema-bound, time-stamped representation of the company profile published by a run.

### 9.5 GraphRAG

For this platform, GraphRAG means retrieval and reasoning that use graph structure as a first-class retrieval signal in addition to text and vector similarity. GraphRAG includes graph expansion, neighborhood retrieval, entity linking, evidence path ranking, contradiction-aware traversal, and section-aware context assembly.

### 9.6 Retrieval profile

A named retrieval strategy used during build or chat, such as `keyword_only`, `vector_only`, `graph_only`, `hybrid_basic`, or `graph_hybrid_expanded`.

---

## 10. Scope

### 10.1 In scope

- URL normalization and canonical company identity
- Azure LLM adapter
- Tavily, SerpAPI, and Apify tool wrappers
- SurrealDB graph and repository layer
- Hybrid retrieval and retrieval API
- LangGraph stateful orchestration
- Runtime-configurable profile schema
- Freshness-aware incremental research
- Evidence-backed profile chat
- Targeted continuation research
- Experiment framework for GraphRAG evaluation
- Documentation, tests, observability, and platform operating guidelines

### 10.2 Out of scope but design for later

- UI workbench
- analyst task queues
- human review approvals
- bulk import orchestration
- billing and multi-tenant RBAC

---

## 11. Success Metrics

### 11.1 Product and operational metrics

- A company URL can be profiled end to end through the API
- Repeat requests reuse fresh knowledge instead of performing full recrawls
- Every material profile section exposes evidence coverage and last refresh time
- Chat answers cite claims and evidence
- Continuation research produces deltas rather than rebuilding blindly

### 11.2 GraphRAG evaluation metrics

The platform must support collection of the following metrics per run and per retrieval profile:

- profile field coverage
- evidence coverage rate
- grounded answer rate
- contradiction detection rate
- retrieval precision at top-k
- retrieval recall at top-k where labeled data exists
- claim validation pass rate
- latency by stage
- cost by stage and per completed profile
- user-judged usefulness of profile and chat answers
- delta quality between graph-enhanced retrieval and baseline retrieval

### 11.3 Target outcomes

- at least 90% of populated material fields have supporting evidence
- repeated requests within TTL avoid unnecessary refresh in most cases
- GraphRAG runs can be compared against non-graph baselines from the same platform
- contradictory evidence is surfaced explicitly rather than hidden

---

## 12. Functional Requirements

## 12.1 URL normalization and identity resolution

The system shall:

- accept `http` and `https` inputs
- normalize scheme, casing, default paths, fragments, and tracking parameters
- extract canonical host and root domain
- store aliases for redirects and known alternative domains
- reject invalid or obviously non-company URLs
- generate canonical ID as `company:<normalized_host>`

A dedicated `CompanyIdentityService` shall own normalization and alias handling.

## 12.2 LLM adapter

The system shall provide a provider-agnostic LLM adapter with Azure as the first production implementation.

### Requirements

- support chat completion style invocation
- support structured generation where available
- support task-specific deployment selection
- support retries, timeouts, and rate-limit backoff
- capture prompt version, model, token usage, latency, and failure metadata
- keep provider details out of orchestration and domain logic

### Required interface

```python
class LLMAdapter(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse: ...
    async def generate_structured(self, request: StructuredLLMRequest, schema: dict) -> LLMResponse: ...
```

## 12.3 Research tools

The system shall wrap Tavily, SerpAPI, and Apify as interchangeable research tools.

### Tool requirements

- common interface and normalized output envelope
- retries, timeout handling, and circuit breaking
- structured logging of all invocations
- raw payload reference persisted for auditability
- graceful degradation on partial tool failure
- ability to tag results with source class such as official site, news, directory, marketplace, registry, or social mention

### Required abstraction

```python
class ResearchTool(Protocol):
    name: str
    async def execute(self, input: ToolInput) -> ToolOutput: ...
```

## 12.4 SurrealDB as system of record

SurrealDB shall be the system of record for:

- companies
- aliases
- source documents
- evidence fragments
- claims
- profile snapshots
- profile sections
- risk signals
- conversations and messages
- research tasks
- run metadata
- schema configurations
- retrieval experiments and evaluation outputs

The repository layer must be async, typed, and isolated from orchestration logic.

## 12.5 Graph-native data model

The platform shall treat graph structure as essential, not optional.

### Minimum node types

- `company`
- `domain_alias`
- `source_document`
- `evidence`
- `claim`
- `profile_snapshot`
- `profile_section`
- `risk_signal`
- `agent_run`
- `research_task`
- `conversation`
- `message`
- `schema_config`
- `retrieval_experiment`
- `evaluation_result`

### Minimum edge types

- `company_has_alias`
- `company_has_source`
- `source_has_evidence`
- `evidence_supports_claim`
- `claim_belongs_to_company`
- `claim_populates_section`
- `claim_related_to_claim`
- `company_has_profile_snapshot`
- `profile_snapshot_has_section`
- `agent_run_for_company`
- `agent_run_generated_claim`
- `agent_run_used_source`
- `conversation_about_company`
- `message_references_claim`
- `message_references_evidence`
- `research_task_for_company`
- `retrieval_experiment_for_run`
- `evaluation_result_for_run`

### Graph design principles

- never overwrite evidence; append and timestamp
- keep immutable snapshots for published profiles
- version claims rather than deleting them when possible
- preserve contradiction state
- allow materialized latest views for fast reads
- preserve provenance paths from source document to evidence to claim to profile field

## 12.6 Retrieval and GraphRAG requirements

GraphRAG functionality must be exploited deliberately and measurably.

### Mandatory retrieval modes

The platform must support these retrieval profiles:

- `keyword_only`
- `vector_only`
- `graph_only`
- `hybrid_basic`
- `graph_hybrid_expanded`
- `schema_aware_graph_hybrid`
- `contradiction_aware_graph_hybrid`

### Mandatory GraphRAG capabilities

- graph traversal from company to related claims, evidence, and latest profile sections
- neighborhood expansion around matched claims and evidence
- section-aware retrieval using active schema field metadata
- field-aware retrieval using `section_id` and `field_id`
- retrieval path explanations showing why a result was selected
- contradiction-aware ranking that boosts verification-relevant evidence where conflicts exist
- freshness-aware ranking that prefers newer evidence when appropriate
- official-source biasing that boosts first-party or authoritative sources
- reranking of merged candidate contexts before LLM consumption
- configurable graph expansion depth and edge weighting
- retrieval mode feature flags at run time

### Retrieval assembly requirements

For each build, chat, or continuation request, the retrieval layer shall be able to assemble context from:

- latest profile snapshot
- active claims
- contradictory claims
- evidence snippets
- source document text
- graph-adjacent claims and evidence
- schema hints
- freshness metadata
- prior research tasks and conversation context where relevant

### Retrieval endpoint requirement

Expose a dedicated retrieval endpoint that returns ranked results plus provenance and scoring metadata.

## 12.7 LangGraph orchestration

LangGraph shall orchestrate stateful workflows with durable state and resumability.

### Required workflow characteristics

- checkpointed execution
- resumable major stages
- conditional branches
- partial completion handling
- targeted re-entry for continuation research
- configurable retrieval profile per run
- experiment tags attached to runs

### Minimum graph states

- `input_received`
- `company_resolved`
- `schema_loaded`
- `db_checked`
- `freshness_evaluated`
- `retrieval_profile_selected`
- `research_plan_built`
- `tool_research_running`
- `evidence_normalized`
- `claims_extracted`
- `claims_reconciled`
- `profile_synthesized`
- `profile_validated`
- `profile_persisted`
- `chat_context_ready`
- `evaluation_logged`
- `completed`
- `failed`

## 12.8 Configurable profile schema

The profile schema must be defined in configuration and changeable at runtime.

### Requirements

- schema stored in YAML or JSON and mirrored in SurrealDB
- support versioning and activation of specific versions
- support section and field additions without rewriting orchestration logic
- support field-level metadata including:
  - `id`
  - `title`
  - `description`
  - `data_type`
  - `required`
  - `ttl_days`
  - `evidence_requirements`
  - `confidence_threshold`
  - `contradiction_policy`
  - `preferred_source_types`
  - `retrieval_hints`
  - `synthesis_hints`
  - `validation_rules`
- compile runtime validators dynamically
- allow schema-specific prompts and retrieval hints

The active schema must drive:

- freshness evaluation
- research planning
- retrieval filters
- extraction prompts
- synthesis prompts
- validation rules
- chat answer formatting

## 12.9 Profile chat

The platform shall support grounded chat against the latest profile and supporting knowledge graph.

### Requirements

- retrieve from snapshot, claims, evidence, and graph neighborhood
- cite claim IDs, evidence IDs, and source URLs where available
- distinguish among known, inferred, contradictory, stale, and unknown information
- store conversation history and retrieval references
- allow chat to create follow-up research tasks
- allow chat runs to choose retrieval profiles for experimentation

## 12.10 Continuation research

Users must be able to direct agents to continue research into selected areas.

### Requirements

- accept company ID plus natural language instruction
- map instruction to one or more sections, fields, or risk topics
- reuse existing evidence before performing new tool calls
- execute only the relevant subgraph
- merge new evidence and claims into the graph
- optionally publish a new profile snapshot
- return a delta summary and experiment metadata

---

## 13. Default Due Diligence Profile Schema

This is the default starter schema and must remain runtime-configurable.

```yaml
schema_id: due_diligence_v1
version: 1
sections:
  - id: company_identity
    title: Company Identity
    fields:
      - id: legal_name
        type: string
        required: true
        ttl_days: 180
      - id: trade_names
        type: list[string]
        required: false
        ttl_days: 180
      - id: headquarters
        type: object
        required: false
        ttl_days: 180
      - id: incorporation_country
        type: string
        required: false
        ttl_days: 365
      - id: founded_year
        type: integer
        required: false
        ttl_days: 365
      - id: employee_estimate
        type: string
        required: false
        ttl_days: 90
      - id: company_description
        type: string
        required: false
        ttl_days: 90

  - id: ownership_and_structure
    title: Ownership and Structure
    fields:
      - id: parent_company
        type: string
        required: false
        ttl_days: 180
      - id: subsidiaries
        type: list[string]
        required: false
        ttl_days: 180
      - id: beneficial_ownership_notes
        type: string
        required: false
        ttl_days: 180
      - id: public_or_private
        type: enum[public, private, unknown]
        required: false
        ttl_days: 90

  - id: operations_and_supply_chain
    title: Operations and Supply Chain
    fields:
      - id: industry
        type: list[string]
        required: false
        ttl_days: 180
      - id: products_services
        type: list[string]
        required: false
        ttl_days: 90
      - id: operating_countries
        type: list[string]
        required: false
        ttl_days: 90
      - id: manufacturing_presence
        type: string
        required: false
        ttl_days: 90
      - id: key_supply_chain_notes
        type: string
        required: false
        ttl_days: 90

  - id: compliance_and_risk
    title: Compliance and Risk
    fields:
      - id: sanctions_exposure
        type: string
        required: false
        ttl_days: 30
      - id: adverse_media_summary
        type: string
        required: false
        ttl_days: 30
      - id: litigation_summary
        type: string
        required: false
        ttl_days: 30
      - id: regulatory_flags
        type: list[string]
        required: false
        ttl_days: 30
      - id: corruption_or_bribery_signals
        type: string
        required: false
        ttl_days: 30

  - id: esg_and_certifications
    title: ESG and Certifications
    fields:
      - id: sustainability_commitments
        type: string
        required: false
        ttl_days: 90
      - id: certifications
        type: list[string]
        required: false
        ttl_days: 90
      - id: human_rights_policy
        type: string
        required: false
        ttl_days: 90
      - id: environmental_policy
        type: string
        required: false
        ttl_days: 90

  - id: financial_health
    title: Financial Health
    fields:
      - id: revenue_estimate
        type: string
        required: false
        ttl_days: 90
      - id: funding_or_listing_status
        type: string
        required: false
        ttl_days: 90
      - id: insolvency_or_distress_signals
        type: string
        required: false
        ttl_days: 30

  - id: profile_meta
    title: Profile Metadata
    fields:
      - id: confidence_summary
        type: string
        required: true
        ttl_days: 1
      - id: evidence_coverage_score
        type: float
        required: true
        ttl_days: 1
      - id: last_full_refresh_at
        type: datetime
        required: true
        ttl_days: 1
      - id: open_questions
        type: list[string]
        required: false
        ttl_days: 1
```

---

## 14. Freshness and Incremental Update Logic

The system shall decide whether to reuse or refresh data by section and field.

### Inputs

- last snapshot timestamp
- last evidence timestamp per field or section
- schema TTL
- confidence level
- contradiction state
- user force-refresh flag
- continuation instruction urgency
- source authority ranking

### Freshness states

- `fresh`
- `stale`
- `missing`
- `contradictory`
- `refresh_recommended`

### Refresh rules

- if requested scope is fresh, skip external research
- if only selected sections are stale, refresh those sections only
- if contradictions exist in high-priority fields, trigger verification subgraph
- if user forces refresh, bypass standard TTL checks
- if retrieval experiment requires alternate mode, reuse existing evidence but rerun retrieval and synthesis where appropriate

### Output

The freshness engine shall produce a `ResearchPlan` containing:

- sections to refresh
- fields to refresh
- recommended tools
- recommended retrieval profile
- rationale
- target evidence count
- confidence repair targets

---

## 15. System Architecture

### 15.1 Core components

1. **API layer** — FastAPI routes
2. **Identity layer** — company normalization and alias handling
3. **Schema layer** — load, validate, compile, and activate schemas
4. **LLM layer** — Azure adapter and prompt/version management
5. **Tool layer** — Tavily, SerpAPI, Apify wrappers
6. **Knowledge layer** — SurrealDB repositories and graph queries
7. **Retrieval layer** — keyword, vector, graph, and hybrid retrieval profiles
8. **Orchestration layer** — LangGraph workflows
9. **Synthesis layer** — claim extraction, reconciliation, profile generation, chat answering
10. **Evaluation layer** — experiment logging, scoring, comparison
11. **Observability layer** — metrics, logs, traces, audit data

### 15.2 Logical flow

```text
POST company URL
  -> normalize URL
  -> load active schema
  -> load existing graph context from SurrealDB
  -> evaluate freshness and contradictions
  -> select retrieval profile and research plan
  -> fetch only missing or stale evidence when needed
  -> normalize evidence and persist
  -> extract and reconcile claims
  -> assemble GraphRAG context
  -> synthesize schema-valid profile snapshot
  -> persist snapshot, run metadata, and experiment metadata
  -> return profile plus freshness, coverage, and provenance information
```

---

## 16. LangGraph Workflow Design

### 16.1 Main build graph

Recommended node sequence:

1. `resolve_company_identity`
2. `load_active_schema`
3. `load_existing_company_context`
4. `evaluate_freshness`
5. `select_retrieval_profile`
6. `build_research_plan`
7. `run_tool_research`
8. `normalize_sources_and_evidence`
9. `extract_claims`
10. `reconcile_claims`
11. `assemble_graphrag_context`
12. `synthesize_profile`
13. `validate_profile_against_schema`
14. `persist_profile_snapshot`
15. `log_experiment_and_metrics`
16. `prepare_chat_context`
17. `return_response`

### 16.2 Required conditional branches

- no external research needed -> synthesize from local graph context
- retrieval mode override present -> use specified retrieval profile
- contradiction detected -> route to verification branch
- insufficient evidence -> return partial profile with explicit unknowns
- validation failure -> run repair or publish partial with warnings
- provider/tool failure -> continue where minimum viability remains possible

### 16.3 Chat graph

1. load latest snapshot and active graph context
2. run selected retrieval profile
3. answer with grounded citations
4. optionally create research task
5. persist message and retrieval refs
6. log answer quality metrics where available

### 16.4 Continuation graph

1. parse instruction
2. map to schema scope and risk areas
3. reuse graph context and prior evidence
4. run targeted research subgraph
5. update claims and graph links
6. optionally publish new snapshot
7. return delta summary and experiment metadata

---

## 17. SurrealDB Data Model

### 17.1 Core tables / records

#### `company`

- `id`: `company:<host>`
- `canonical_url`
- `canonical_host`
- `root_domain`
- `display_name`
- `latest_profile_snapshot_id`
- `active_schema_version`
- `created_at`
- `updated_at`
- `status`

#### `domain_alias`

- `id`
- `company_id`
- `alias_host`
- `alias_url`
- `reason`
- `created_at`

#### `source_document`

- `id`
- `company_id`
- `url`
- `title`
- `provider`
- `source_type`
- `published_at`
- `retrieved_at`
- `raw_payload_ref`
- `content_hash`
- `content_text`
- `metadata`

#### `evidence`

- `id`
- `company_id`
- `source_document_id`
- `section_id`
- `field_id`
- `excerpt`
- `normalized_fact_candidate`
- `retrieved_at`
- `published_at`
- `confidence`
- `embedding`
- `metadata`

#### `claim`

- `id`
- `company_id`
- `section_id`
- `field_id`
- `value`
- `value_type`
- `confidence`
- `status`
- `first_seen_at`
- `last_verified_at`
- `derived_from_evidence_count`
- `schema_version`
- `metadata`

#### `profile_snapshot`

- `id`
- `company_id`
- `schema_id`
- `schema_version`
- `profile_json`
- `coverage_summary`
- `quality_summary`
- `retrieval_profile`
- `created_at`
- `created_by_run_id`
- `is_latest`

#### `profile_section`

- `id`
- `profile_snapshot_id`
- `section_id`
- `section_json`
- `freshness_status`
- `updated_at`

#### `risk_signal`

- `id`
- `company_id`
- `category`
- `severity`
- `summary`
- `status`
- `detected_at`
- `source_claim_ids`

#### `agent_run`

- `id`
- `company_id`
- `run_type`
- `status`
- `retrieval_profile`
- `experiment_tags`
- `started_at`
- `ended_at`
- `active_schema_version`
- `input_payload`
- `output_summary`
- `trace_id`
- `error_summary`
- `metrics`

#### `research_task`

- `id`
- `company_id`
- `instruction`
- `scope`
- `priority`
- `status`
- `created_at`
- `created_from_message_id`
- `completed_at`

#### `conversation`

- `id`
- `company_id`
- `created_at`
- `updated_at`

#### `message`

- `id`
- `conversation_id`
- `role`
- `content`
- `created_at`
- `retrieval_refs`
- `research_task_id`

#### `schema_config`

- `id`
- `schema_id`
- `version`
- `is_active`
- `schema_json`
- `created_at`
- `notes`

#### `retrieval_experiment`

- `id`
- `run_id`
- `company_id`
- `retrieval_profile`
- `candidate_count`
- `selected_count`
- `config_json`
- `created_at`

#### `evaluation_result`

- `id`
- `run_id`
- `company_id`
- `metric_name`
- `metric_value`
- `metric_group`
- `notes`
- `created_at`

### 17.2 Index requirements

Create indexes for at least:

- `company.canonical_host`
- `company.root_domain`
- `source_document.company_id`
- `source_document.url`
- `evidence.company_id`
- `evidence.section_id`
- `evidence.field_id`
- `claim.company_id`
- `claim.section_id`
- `claim.field_id`
- `claim.status`
- `profile_snapshot.company_id`
- `profile_snapshot.is_latest`
- `agent_run.company_id`
- `agent_run.retrieval_profile`
- `research_task.company_id`
- `message.conversation_id`
- `retrieval_experiment.run_id`
- `evaluation_result.run_id`

If vector retrieval is enabled, index embeddings for `evidence` and optionally `claim`.

---

## 18. API Requirements

Use FastAPI for all HTTP APIs.

### 18.1 POST `/v1/profiles/build`

#### Request

```json
{
  "company_url": "https://www.company.com",
  "force_refresh": false,
  "schema_id": "due_diligence_v1",
  "publish_snapshot": true,
  "research_scope": ["all"],
  "retrieval_profile": "graph_hybrid_expanded",
  "experiment_tags": ["baseline_candidate"]
}
```

#### Behavior

- normalize URL
- load schema
- check DB first
- evaluate freshness and contradictions
- select or honor retrieval profile
- fetch only missing or stale evidence when needed
- return latest or new profile snapshot

### 18.2 GET `/v1/profiles/{company_id}`

Return latest profile snapshot and profile metadata.

### 18.3 GET `/v1/profiles/{company_id}/evidence`

Support filters by `section_id`, `field_id`, `claim_id`, `freshness_status`, and `limit`.

### 18.4 POST `/v1/research/continue`

#### Request

```json
{
  "company_id": "company:www.company.com",
  "instruction": "Investigate recent litigation and sanctions exposure in the EU.",
  "publish_snapshot": true,
  "retrieval_profile": "contradiction_aware_graph_hybrid"
}
```

Return delta summary, new evidence count, claim changes, and optional new snapshot ID.

### 18.5 POST `/v1/chat`

#### Request

```json
{
  "company_id": "company:www.company.com",
  "conversation_id": "optional",
  "message": "What are the biggest due diligence risks and what evidence supports them?",
  "retrieval_profile": "schema_aware_graph_hybrid"
}
```

#### Response

```json
{
  "conversation_id": "conversation:...",
  "answer": "...",
  "citations": [
    {"claim_id": "claim:...", "evidence_id": "evidence:...", "url": "https://..."}
  ],
  "follow_up_research_suggested": true,
  "retrieval_profile": "schema_aware_graph_hybrid"
}
```

### 18.6 POST `/v1/retrieval/search`

Support search over graph, keyword, vector, and hybrid modes with ranking metadata returned.

### 18.7 GET `/v1/schemas/active`

Return active schema config.

### 18.8 POST `/v1/schemas/activate`

Activate a new schema version.

### 18.9 POST `/v1/experiments/evaluate`

Run or register an evaluation workflow for a set of retrieval profiles against test cases.

### 18.10 GET `/v1/experiments/runs/{run_id}`

Return retrieval profile, experiment metadata, metrics, and comparison data if available.

---

## 19. Retrieval Design

### 19.1 Inputs

- company ID
- query or build context
- active schema
- optional section filters
- optional field filters
- retrieval profile
- freshness and contradiction metadata

### 19.2 Ranking strategy

The retrieval service shall support a configurable hybrid ranking pipeline using:

1. exact section and field matches
2. company-specific active claims
3. evidence keyword matches
4. vector similarity on evidence and claims when enabled
5. graph proximity boosts for evidence connected to matching claims and latest snapshot sections
6. freshness boosts or penalties
7. official-source boosts
8. contradiction-aware boosts for verification queries
9. final reranking prior to LLM context assembly

### 19.3 Retrieval outputs

Each result should include:

- result type
- score
- score breakdown
- text snippet
- section and field IDs where applicable
- freshness metadata
- contradiction metadata
- provenance path
- source URL if available
- retrieval profile used

### 19.4 GraphRAG assembly rules

The platform must support at least the following GraphRAG context assembly behaviors:

- include 1-hop and configurable 2-hop graph neighbors around highly ranked claims
- include latest snapshot section summaries when directly relevant
- include contradictory evidence pairs for verification-sensitive fields
- include authoritative source preference when multiple equivalent candidates exist
- deduplicate semantically overlapping evidence before context packing
- preserve provenance chains in context metadata even if compressed for the LLM

---

## 20. Business Logic Rules

1. evidence-backed population takes priority over narrative generation
2. unknown remains unknown when evidence is insufficient
3. official company and authoritative sources rank above broad web sources where appropriate
4. stale data can remain visible but must be marked
5. contradictory claims must remain queryable and reduce certainty
6. retrieval planning must derive from active schema and run context, not hardcoded field lists
7. profile publication occurs only on success or explicit partial-publication rules
8. experiment metadata must be attached to runs that change retrieval behavior
9. profile quality and experiment quality are both first-class outcomes

---

## 21. Error Handling Requirements

The platform shall:

- return typed API errors with machine-readable codes
- distinguish validation, provider, timeout, partial completion, and persistence failures
- support partial profiles when some sections fail
- persist failure state with debug context
- avoid corrupting graph state on interrupted runs

### Example error classes

- `InvalidCompanyUrlError`
- `SchemaNotFoundError`
- `ExternalToolTimeoutError`
- `LLMProviderError`
- `ProfileValidationError`
- `SurrealPersistenceError`
- `RetrievalProfileNotFoundError`
- `ExperimentLoggingError`

---

## 22. Security and Compliance Requirements

- secrets only in environment variables or managed secret stores
- no secrets in logs or persisted payloads
- source provenance stored for auditability
- domain allow/block list support must be possible
- prepare for future auth and access control
- store prompt and model metadata needed for audit without storing sensitive credentials

---

## 23. Observability and Platform Operations

The platform shall emit:

- structured logs per request and per run
- traces across API, tools, LLM, retrieval, and DB calls
- metrics for latency, tool usage, token usage, cache reuse, refresh rates, evidence coverage, retrieval profile use, and experiment outcomes

### IDs to propagate

- `request_id`
- `run_id`
- `company_id`
- `conversation_id`
- `trace_id`
- `experiment_id` when relevant

### Operational guidelines

- every major workflow stage must log start, finish, and outcome
- long-running workflows must support resume from checkpoint
- all external calls must have timeout, retry, and circuit-breaker policies
- every release should include migration notes if DB or schema behavior changed
- on-call or operator runbooks must exist for failed tool providers, schema issues, and DB incidents

---

## 24. Testing Guidelines

Testing is mandatory and not optional platform hardening.

### 24.1 Unit tests

Cover at minimum:

- URL normalization and alias handling
- schema loading and runtime compilation
- freshness evaluation
- retrieval profile selection
- research planning
- claim extraction and reconciliation helpers
- graph ranking functions
- prompt builders
- repository contracts
- adapter behavior

### 24.2 Integration tests

Cover at minimum:

- SurrealDB repositories with real or containerized DB
- Azure adapter happy path and failure paths with mocks or test doubles
- Tavily, SerpAPI, and Apify wrappers with mocked provider responses
- graph persistence and traversal queries
- LangGraph checkpoint and resume behavior
- retrieval endpoint behavior across multiple retrieval profiles
- build, chat, and continuation endpoints end to end with fixtures

### 24.3 Contract tests

Required for:

- API request and response schemas
- tool wrapper normalized envelopes
- LLM adapter request and response contracts
- schema compiler output contracts
- retrieval result payload structure

### 24.4 Evaluation tests

The platform must include evaluation-oriented tests for GraphRAG exploration.

Required:

- benchmark fixtures with labeled questions and expected evidence targets
- retrieval comparison tests between baseline and graph-enhanced modes
- field coverage evaluation for sample company sets
- contradiction detection tests
- chat grounding tests that verify citations map to stored evidence
- regression tests to detect when a retrieval strategy materially worsens quality

### 24.5 Performance and resilience tests

Required:

- latency tests for warm and cold profile builds
- load tests for concurrent build and chat requests
- DB query performance tests for common company-centric queries
- retry and fallback tests under simulated provider failures
- checkpoint recovery tests for interrupted runs

### 24.6 Test data guidelines

- use deterministic fixtures where possible
- separate golden test cases from exploratory benchmark cases
- store expected outputs and evaluation labels under version control
- every new schema version must include at least one test fixture set

### 24.7 Minimum CI requirements

CI must run:

- linting and type checks
- unit tests
- contract tests
- selected integration tests
- schema validation checks
- prompt/config sanity checks

---

## 25. Documentation Guidelines

Documentation is a required deliverable for every major component.

### 25.1 Repository-level docs

The repository must include:

- `README.md` with setup, local run instructions, environment variables, and architecture summary
- `docs/architecture.md` with component diagram and data flow
- `docs/data-model.md` describing SurrealDB records, edges, and indexing strategy
- `docs/retrieval.md` describing retrieval profiles, ranking, and GraphRAG behaviors
- `docs/schemas.md` describing schema format and activation process
- `docs/prompts.md` describing prompt ownership, versioning, and editing guidelines
- `docs/evaluation.md` describing benchmarking and experiment workflows
- `docs/runbooks/` for incident and operator procedures

### 25.2 Code documentation rules

- every public class and function must have a docstring
- repository methods must document expected record shape and edge behavior
- graph nodes and LangGraph states must be documented inline and in architecture docs
- prompt templates must include purpose, input contract, and expected output form
- config classes must document each environment variable

### 25.3 Change management docs

The platform must maintain:

- ADRs for major architectural decisions
- migration notes for DB schema changes
- changelog entries for retrieval profile changes
- release notes for schema activation changes
- experiment notes when GraphRAG logic materially changes

### 25.4 Documentation quality rules

- examples must be runnable or syntactically correct
- API docs must match actual request and response contracts
- every retrieval profile must be described in one canonical place
- every schema version must be documented with rationale and deltas

---

## 26. Component-Level Implementation Guidelines

### 26.1 Recommended project structure

```text
app/
  api/
    routes/
      profiles.py
      chat.py
      retrieval.py
      schemas.py
      experiments.py
      health.py
  core/
    config.py
    logging.py
    exceptions.py
    urls.py
    feature_flags.py
  llm/
    base.py
    azure_adapter.py
    prompts/
  tools/
    base.py
    tavily_tool.py
    serpapi_tool.py
    apify_tool.py
  db/
    surreal_client.py
    migrations/
    repositories/
      company_repo.py
      source_repo.py
      evidence_repo.py
      claim_repo.py
      profile_repo.py
      conversation_repo.py
      schema_repo.py
      run_repo.py
      experiment_repo.py
  schemas/
    loader.py
    compiler.py
    validators.py
  retrieval/
    profiles.py
    rankers.py
    graph_expansion.py
    assembler.py
  domain/
    models/
    services/
      identity_service.py
      freshness_service.py
      retrieval_service.py
      profile_service.py
      chat_service.py
      evaluation_service.py
  graphs/
    state.py
    build_profile_graph.py
    continuation_graph.py
    chat_graph.py
    nodes/
  observability/
    metrics.py
    tracing.py
  docs/
  tests/
```

### 26.2 Configuration

Support env-based config for:

- Azure endpoint, API version, keys, and deployment names
- Tavily key
- SerpAPI key
- Apify token and actor IDs
- SurrealDB connection details
- active schema ID and version
- feature flags for embeddings and retrieval profiles
- timeout and retry policies
- experiment toggles and evaluation thresholds

### 26.3 Prompt management

Prompts must be versioned and separated by purpose:

- query planning
- research planning
- evidence extraction
- claim extraction
- contradiction detection
- profile synthesis
- chat answering
- continuation planning
- evaluation or grading prompts where used

Prompts must be schema-aware and retrieval-profile-aware when relevant.

---

## 27. Milestones

### Milestone 1: Platform foundation

- FastAPI service skeleton
- config system
- health and readiness routes
- URL normalization service
- SurrealDB client and repository base
- schema loader and compiler
- documentation skeleton

### Milestone 2: Core research platform

- Azure adapter
- Tavily, SerpAPI, Apify wrappers
- evidence and claim persistence
- initial graph edges and indexes
- LangGraph base states

### Milestone 3: GraphRAG and retrieval platform

- retrieval service with multiple retrieval profiles
- graph expansion logic
- retrieval endpoint with provenance metadata
- experiment logging for retrieval profile selection

### Milestone 4: Profile generation workflows

- build workflow
- continuation workflow
- schema validation
- profile snapshot publication
- contradiction handling

### Milestone 5: Interactive workflows

- chat endpoint
- conversation persistence
- follow-up research task creation
- citation path support

### Milestone 6: Evaluation, hardening, and operations

- evaluation workflows and benchmark fixtures
- observability
- resilience policies
- runbooks
- full documentation pass
- CI quality gates

---

## 28. Acceptance Criteria

The platform is considered ready for active use when:

1. a company URL can be submitted and a structured profile is returned
2. the normalized company URL is used as canonical ID
3. the system checks SurrealDB before new external research
4. freshness logic drives selective refresh rather than full recrawl by default
5. Tavily, SerpAPI, and Apify are integrated behind stable interfaces
6. LangGraph orchestrates the build flow with durable state
7. SurrealDB stores graph-linked companies, sources, evidence, claims, and profile snapshots
8. retrieval supports at least graph, keyword, and hybrid modes
9. the active schema is configuration-driven and switchable at runtime
10. chat answers are grounded in stored profile, claims, and evidence
11. continuation research updates the graph and optionally publishes a new snapshot
12. experiment metadata allows comparison of retrieval profiles
13. tests and documentation described in this PRD are present and maintained
14. every material answer or profile field can be traced back to evidence and provenance path

---

## 29. Decisions to Lock Early

These should be decided early and kept stable unless there is a strong reason to change them:

1. canonical company ID format
2. sync versus async execution model for long builds
3. whether embeddings are enabled by default
4. exact SurrealDB edge naming conventions
5. retrieval profile naming and baseline definitions
6. profile publication rules for minor versus material deltas
7. evaluation dataset ownership and versioning

---

## 30. Recommended Defaults

Use these defaults unless explicitly overridden:

- API framework: FastAPI
- data modeling: Pydantic v2
- runtime: asyncio
- LLM provider: Azure OpenAI-compatible endpoint via adapter
- orchestration: LangGraph with persisted checkpoints
- primary DB: SurrealDB
- schema format: YAML mirrored into `schema_config`
- canonical ID: `company:<normalized_host>`
- default retrieval profile for builds: `graph_hybrid_expanded`
- default retrieval profile for chat: `schema_aware_graph_hybrid`
- embeddings: feature-flagged, enabled where supported and useful
- publication: publish snapshot after successful build or material continuation update

---

## 31. Open Questions

These are not blockers, but they should be tracked:

1. should long-running builds return job handles by default
2. which jurisdictions or regulatory frameworks matter first
3. what authoritative source classes should receive the highest ranking boosts
4. how should risk severity be scored across categories
5. what exact benchmark set will be used for GraphRAG evaluation
6. what threshold defines meaningful uplift versus baseline retrieval

---

## 32. Build Order for Coding Agents

Implement in this sequence:

1. project scaffold, config, health routes, docs skeleton
2. URL normalization and company identity service
3. SurrealDB client, migrations, repositories, graph bootstrap
4. schema loader, compiler, validators
5. Azure LLM adapter
6. research tool abstractions and wrappers
7. freshness service and research planner
8. retrieval service and retrieval profiles
9. LangGraph build workflow
10. claim extraction, reconciliation, and profile synthesis
11. profile persistence and retrieval endpoint
12. chat workflow
13. continuation research workflow
14. experiment logging and evaluation workflows
15. observability, tests, and final documentation

---

## 33. Definition of Done

The platform is done for this delivery stage when a developer can:

1. configure the service using environment variables
2. start the API locally or in a deployment environment
3. submit `https://www.company.com`
4. observe SurrealDB being checked first
5. see selective external research only when required
6. receive a schema-valid profile snapshot with evidence coverage and freshness metadata
7. ask follow-up questions through chat and receive grounded answers with citations
8. direct additional research through continuation endpoints
9. inspect graph-linked evidence, claims, contradictions, and run traces
10. compare retrieval profiles and inspect experiment metrics for GraphRAG impact
11. run automated tests and consult documentation sufficient to operate and extend the platform
