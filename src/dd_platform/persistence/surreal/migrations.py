"""SurrealDB schema migrations.

Defines the graph schema: tables, edges, indexes, and constraints.
All DDL is replayable in local environments.
"""

from __future__ import annotations

from ...logging import get_logger
from .client import SurrealClient

logger = get_logger(__name__)

# Schema definition in SurrealQL
SCHEMA_DDL = """
-- ============================================================
-- Company Due Diligence Platform — SurrealDB Schema
-- ============================================================

-- Node tables
DEFINE TABLE company SCHEMAFULL;
DEFINE FIELD canonical_url ON company TYPE string;
DEFINE FIELD canonical_host ON company TYPE string;
DEFINE FIELD root_domain ON company TYPE string;
DEFINE FIELD display_name ON company TYPE option<string>;
DEFINE FIELD latest_profile_snapshot_id ON company TYPE option<string>;
DEFINE FIELD active_schema_version ON company TYPE option<int>;
DEFINE FIELD created_at ON company TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON company TYPE datetime DEFAULT time::now();
DEFINE FIELD status ON company TYPE string DEFAULT 'active';
DEFINE FIELD metadata ON company TYPE option<object> FLEXIBLE;
DEFINE INDEX idx_company_host ON company FIELDS canonical_host UNIQUE;
DEFINE INDEX idx_company_domain ON company FIELDS root_domain;

DEFINE TABLE domain_alias SCHEMAFULL;
DEFINE FIELD company_id ON domain_alias TYPE string;
DEFINE FIELD alias_host ON domain_alias TYPE string;
DEFINE FIELD alias_url ON domain_alias TYPE option<string>;
DEFINE FIELD reason ON domain_alias TYPE string DEFAULT 'redirect';
DEFINE FIELD created_at ON domain_alias TYPE datetime DEFAULT time::now();

DEFINE TABLE source_document SCHEMAFULL;
DEFINE FIELD company_id ON source_document TYPE string;
DEFINE FIELD url ON source_document TYPE string;
DEFINE FIELD title ON source_document TYPE option<string>;
DEFINE FIELD provider ON source_document TYPE string;
DEFINE FIELD source_type ON source_document TYPE string DEFAULT 'other';
DEFINE FIELD published_at ON source_document TYPE option<datetime>;
DEFINE FIELD retrieved_at ON source_document TYPE datetime DEFAULT time::now();
DEFINE FIELD raw_payload_ref ON source_document TYPE option<string>;
DEFINE FIELD content_hash ON source_document TYPE option<string>;
DEFINE FIELD content_text ON source_document TYPE option<string>;
DEFINE FIELD metadata ON source_document TYPE option<object> FLEXIBLE;
DEFINE INDEX idx_source_company ON source_document FIELDS company_id;
DEFINE INDEX idx_source_url ON source_document FIELDS url;

DEFINE TABLE evidence SCHEMAFULL;
DEFINE FIELD company_id ON evidence TYPE string;
DEFINE FIELD source_document_id ON evidence TYPE string;
DEFINE FIELD section_id ON evidence TYPE option<string>;
DEFINE FIELD field_id ON evidence TYPE option<string>;
DEFINE FIELD excerpt ON evidence TYPE string;
DEFINE FIELD normalized_fact_candidate ON evidence TYPE option<string>;
DEFINE FIELD retrieved_at ON evidence TYPE datetime DEFAULT time::now();
DEFINE FIELD published_at ON evidence TYPE option<datetime>;
DEFINE FIELD confidence ON evidence TYPE float DEFAULT 0.5;
DEFINE FIELD metadata ON evidence TYPE option<object> FLEXIBLE;
DEFINE INDEX idx_evidence_company ON evidence FIELDS company_id;
DEFINE INDEX idx_evidence_section ON evidence FIELDS section_id;
DEFINE INDEX idx_evidence_field ON evidence FIELDS field_id;

DEFINE TABLE claim SCHEMAFULL;
DEFINE FIELD company_id ON claim TYPE string;
DEFINE FIELD section_id ON claim TYPE string;
DEFINE FIELD field_id ON claim TYPE string;
DEFINE FIELD value ON claim TYPE string;
DEFINE FIELD value_type ON claim TYPE string DEFAULT 'string';
DEFINE FIELD confidence ON claim TYPE float DEFAULT 0.5;
DEFINE FIELD status ON claim TYPE string DEFAULT 'active';
DEFINE FIELD first_seen_at ON claim TYPE datetime DEFAULT time::now();
DEFINE FIELD last_verified_at ON claim TYPE datetime DEFAULT time::now();
DEFINE FIELD derived_from_evidence_count ON claim TYPE int DEFAULT 0;
DEFINE FIELD schema_version ON claim TYPE int DEFAULT 1;
DEFINE FIELD metadata ON claim TYPE option<object> FLEXIBLE;
DEFINE INDEX idx_claim_company ON claim FIELDS company_id;
DEFINE INDEX idx_claim_section ON claim FIELDS section_id;
DEFINE INDEX idx_claim_field ON claim FIELDS field_id;
DEFINE INDEX idx_claim_status ON claim FIELDS status;

DEFINE TABLE profile_snapshot SCHEMAFULL;
DEFINE FIELD company_id ON profile_snapshot TYPE string;
DEFINE FIELD schema_id ON profile_snapshot TYPE string;
DEFINE FIELD schema_version ON profile_snapshot TYPE int;
DEFINE FIELD profile_json ON profile_snapshot TYPE object FLEXIBLE;
DEFINE FIELD coverage_summary ON profile_snapshot TYPE option<object> FLEXIBLE;
DEFINE FIELD quality_summary ON profile_snapshot TYPE option<object> FLEXIBLE;
DEFINE FIELD retrieval_profile ON profile_snapshot TYPE option<string>;
DEFINE FIELD created_at ON profile_snapshot TYPE datetime DEFAULT time::now();
DEFINE FIELD created_by_run_id ON profile_snapshot TYPE option<string>;
DEFINE FIELD is_latest ON profile_snapshot TYPE bool DEFAULT true;
DEFINE INDEX idx_snapshot_company ON profile_snapshot FIELDS company_id;
DEFINE INDEX idx_snapshot_latest ON profile_snapshot FIELDS is_latest;

DEFINE TABLE profile_section SCHEMAFULL;
DEFINE FIELD profile_snapshot_id ON profile_section TYPE string;
DEFINE FIELD section_id ON profile_section TYPE string;
DEFINE FIELD section_json ON profile_section TYPE object FLEXIBLE;
DEFINE FIELD freshness_status ON profile_section TYPE string DEFAULT 'fresh';
DEFINE FIELD updated_at ON profile_section TYPE datetime DEFAULT time::now();

DEFINE TABLE risk_signal SCHEMAFULL;
DEFINE FIELD company_id ON risk_signal TYPE string;
DEFINE FIELD category ON risk_signal TYPE string;
DEFINE FIELD severity ON risk_signal TYPE string DEFAULT 'medium';
DEFINE FIELD summary ON risk_signal TYPE string;
DEFINE FIELD status ON risk_signal TYPE string DEFAULT 'active';
DEFINE FIELD detected_at ON risk_signal TYPE datetime DEFAULT time::now();
DEFINE FIELD source_claim_ids ON risk_signal TYPE option<array>;

DEFINE TABLE agent_run SCHEMAFULL;
DEFINE FIELD company_id ON agent_run TYPE string;
DEFINE FIELD run_type ON agent_run TYPE string;
DEFINE FIELD status ON agent_run TYPE string DEFAULT 'pending';
DEFINE FIELD retrieval_profile ON agent_run TYPE option<string>;
DEFINE FIELD experiment_tags ON agent_run TYPE option<array>;
DEFINE FIELD started_at ON agent_run TYPE datetime DEFAULT time::now();
DEFINE FIELD ended_at ON agent_run TYPE option<datetime>;
DEFINE FIELD active_schema_version ON agent_run TYPE option<int>;
DEFINE FIELD input_payload ON agent_run TYPE option<object> FLEXIBLE;
DEFINE FIELD output_summary ON agent_run TYPE option<object> FLEXIBLE;
DEFINE FIELD trace_id ON agent_run TYPE option<string>;
DEFINE FIELD error_summary ON agent_run TYPE option<string>;
DEFINE FIELD metrics ON agent_run TYPE option<object> FLEXIBLE;
DEFINE INDEX idx_run_company ON agent_run FIELDS company_id;
DEFINE INDEX idx_run_profile ON agent_run FIELDS retrieval_profile;

DEFINE TABLE research_task SCHEMAFULL;
DEFINE FIELD company_id ON research_task TYPE string;
DEFINE FIELD instruction ON research_task TYPE string;
DEFINE FIELD scope ON research_task TYPE option<array>;
DEFINE FIELD priority ON research_task TYPE string DEFAULT 'normal';
DEFINE FIELD status ON research_task TYPE string DEFAULT 'pending';
DEFINE FIELD created_at ON research_task TYPE datetime DEFAULT time::now();
DEFINE FIELD created_from_message_id ON research_task TYPE option<string>;
DEFINE FIELD completed_at ON research_task TYPE option<datetime>;
DEFINE INDEX idx_task_company ON research_task FIELDS company_id;

DEFINE TABLE conversation SCHEMAFULL;
DEFINE FIELD company_id ON conversation TYPE string;
DEFINE FIELD created_at ON conversation TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON conversation TYPE datetime DEFAULT time::now();

DEFINE TABLE message SCHEMAFULL;
DEFINE FIELD conversation_id ON message TYPE string;
DEFINE FIELD role ON message TYPE string;
DEFINE FIELD content ON message TYPE string;
DEFINE FIELD created_at ON message TYPE datetime DEFAULT time::now();
DEFINE FIELD retrieval_refs ON message TYPE option<array>;
DEFINE FIELD research_task_id ON message TYPE option<string>;
DEFINE INDEX idx_message_conversation ON message FIELDS conversation_id;

DEFINE TABLE schema_config SCHEMAFULL;
DEFINE FIELD schema_id ON schema_config TYPE string;
DEFINE FIELD version ON schema_config TYPE int;
DEFINE FIELD is_active ON schema_config TYPE bool DEFAULT true;
DEFINE FIELD schema_json ON schema_config TYPE object FLEXIBLE;
DEFINE FIELD created_at ON schema_config TYPE datetime DEFAULT time::now();
DEFINE FIELD notes ON schema_config TYPE option<string>;

DEFINE TABLE retrieval_experiment SCHEMAFULL;
DEFINE FIELD run_id ON retrieval_experiment TYPE string;
DEFINE FIELD company_id ON retrieval_experiment TYPE string;
DEFINE FIELD retrieval_profile ON retrieval_experiment TYPE string;
DEFINE FIELD candidate_count ON retrieval_experiment TYPE int DEFAULT 0;
DEFINE FIELD selected_count ON retrieval_experiment TYPE int DEFAULT 0;
DEFINE FIELD config_json ON retrieval_experiment TYPE option<object> FLEXIBLE;
DEFINE FIELD created_at ON retrieval_experiment TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_exp_run ON retrieval_experiment FIELDS run_id;

DEFINE TABLE evaluation_result SCHEMAFULL;
DEFINE FIELD run_id ON evaluation_result TYPE string;
DEFINE FIELD company_id ON evaluation_result TYPE string;
DEFINE FIELD metric_name ON evaluation_result TYPE string;
DEFINE FIELD metric_value ON evaluation_result TYPE float;
DEFINE FIELD metric_group ON evaluation_result TYPE string DEFAULT 'quality';
DEFINE FIELD notes ON evaluation_result TYPE option<string>;
DEFINE FIELD created_at ON evaluation_result TYPE datetime DEFAULT time::now();
DEFINE INDEX idx_eval_run ON evaluation_result FIELDS run_id;

-- ============================================================
-- Graph edge tables (RELATE)
-- ============================================================
DEFINE TABLE company_has_alias SCHEMAFULL TYPE RELATION IN company OUT domain_alias;
DEFINE FIELD created_at ON company_has_alias TYPE datetime DEFAULT time::now();

DEFINE TABLE company_has_source SCHEMAFULL TYPE RELATION IN company OUT source_document;
DEFINE FIELD created_at ON company_has_source TYPE datetime DEFAULT time::now();

DEFINE TABLE source_has_evidence SCHEMAFULL TYPE RELATION IN source_document OUT evidence;
DEFINE FIELD created_at ON source_has_evidence TYPE datetime DEFAULT time::now();

DEFINE TABLE evidence_supports_claim SCHEMAFULL TYPE RELATION IN evidence OUT claim;
DEFINE FIELD confidence ON evidence_supports_claim TYPE float DEFAULT 1.0;
DEFINE FIELD created_at ON evidence_supports_claim TYPE datetime DEFAULT time::now();

DEFINE TABLE claim_belongs_to_company SCHEMAFULL TYPE RELATION IN claim OUT company;
DEFINE FIELD created_at ON claim_belongs_to_company TYPE datetime DEFAULT time::now();

DEFINE TABLE claim_populates_section SCHEMAFULL TYPE RELATION IN claim OUT profile_section;
DEFINE FIELD created_at ON claim_populates_section TYPE datetime DEFAULT time::now();

DEFINE TABLE claim_related_to_claim SCHEMAFULL TYPE RELATION IN claim OUT claim;
DEFINE FIELD relation_type ON claim_related_to_claim TYPE string DEFAULT 'related';
DEFINE FIELD created_at ON claim_related_to_claim TYPE datetime DEFAULT time::now();

DEFINE TABLE company_has_snapshot SCHEMAFULL TYPE RELATION IN company OUT profile_snapshot;
DEFINE FIELD created_at ON company_has_snapshot TYPE datetime DEFAULT time::now();

DEFINE TABLE snapshot_has_section SCHEMAFULL TYPE RELATION IN profile_snapshot OUT profile_section;
DEFINE FIELD created_at ON snapshot_has_section TYPE datetime DEFAULT time::now();

DEFINE TABLE run_for_company SCHEMAFULL TYPE RELATION IN agent_run OUT company;
DEFINE FIELD created_at ON run_for_company TYPE datetime DEFAULT time::now();

DEFINE TABLE run_generated_claim SCHEMAFULL TYPE RELATION IN agent_run OUT claim;
DEFINE FIELD created_at ON run_generated_claim TYPE datetime DEFAULT time::now();

DEFINE TABLE run_used_source SCHEMAFULL TYPE RELATION IN agent_run OUT source_document;
DEFINE FIELD created_at ON run_used_source TYPE datetime DEFAULT time::now();

DEFINE TABLE conversation_about_company SCHEMAFULL TYPE RELATION IN conversation OUT company;
DEFINE FIELD created_at ON conversation_about_company TYPE datetime DEFAULT time::now();

DEFINE TABLE message_references_claim SCHEMAFULL TYPE RELATION IN message OUT claim;
DEFINE FIELD created_at ON message_references_claim TYPE datetime DEFAULT time::now();

DEFINE TABLE message_references_evidence SCHEMAFULL TYPE RELATION IN message OUT evidence;
DEFINE FIELD created_at ON message_references_evidence TYPE datetime DEFAULT time::now();
"""


async def run_migrations(client: SurrealClient) -> None:
    """Apply the full schema DDL to SurrealDB.

    This is idempotent — DEFINE statements in SurrealDB create-or-update.

    Args:
        client: Connected SurrealDB client.
    """
    logger.info("surrealdb_migration_start")

    # Split into individual statements and execute
    statements = [s.strip() for s in SCHEMA_DDL.split(";") if s.strip() and not s.strip().startswith("--")]
    for statement in statements:
        if statement:
            try:
                await client.execute(statement + ";")
            except Exception as e:
                logger.warning(
                    "surrealdb_migration_statement_warning",
                    statement=statement[:100],
                    error=str(e),
                )

    logger.info("surrealdb_migration_complete", statements_executed=len(statements))
