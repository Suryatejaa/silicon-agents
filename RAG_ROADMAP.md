# Silicon Agents RAG Roadmap

This document defines how Silicon Agents should evolve from context-injected orchestration into a true retrieval-augmented generation pipeline suitable for semiconductor pilot programs and enterprise deployments.

## 1. Current State

Silicon Agents now implements a pilot-safe RAG MVP.

What exists today:

- parser-driven artifact normalization
- enterprise policy injection
- run-profile presets
- manually supplied `reference_data`
- orchestration that synthesizes context into a run-specific prompt
- persisted run history with raw artifact replay
- saved run history converted into retrieval documents
- manual engineering-note ingestion with deterministic chunking
- Gemini embeddings with local deterministic embedding fallback
- metadata-filtered retrieval by project, agent, mode, run profile, and source type
- runtime retrieval injection for Agent 01 and Agent 02
- retrieved-source metadata attached to decisions
- retrieved-source citations displayed on Agent 01 and Agent 02 decision cards
- pgvector-ready storage with local app-scored ranking fallback

What does **not** exist yet:

- dedicated RAG admin / evidence-review UI
- background reindex or backfill jobs
- production pgvector migration and index hardening
- reranking, threshold tuning, or retrieval eval harness
- tenant-aware enterprise knowledge boundaries beyond metadata filters

So the current architecture is best described as:

`artifact parsing + orchestration + metadata-filtered retrieval over run history/manual notes`

The remaining work is productionizing the retrieval layer, not adding the first RAG foundation.

## 2. Why RAG Matters Here

Semiconductor workflows depend heavily on historical context that is rarely present in the current artifact alone. A modern RAG layer would let the agents retrieve prior engineering knowledge at run time instead of relying only on static profile notes.

Examples:

- prior coverage closure reviews for the same IP block
- waiver notes for intentionally uncovered bins
- historical regression debug clusters and root-cause mappings
- lot review notes for recurring ATE excursions
- SPC excursion response playbooks
- methodology notes specific to a client or delivery team
- signoff checklists and escalation policies

This matters because the same zero-hit bin or failing test cluster can mean very different things depending on:

- whether it was intentionally waived before
- whether it historically maps to a shared RTL bug
- whether it is a known testbench constraint issue
- whether the client’s process team already identified a repeating yield excursion pattern

## 3. Target RAG Objectives

The RAG layer should help the agents:

1. retrieve the most relevant prior engineering context for the active artifact
2. cite retrieved evidence in the generated decisions
3. reduce repeated human interpretation of historically familiar issues
4. preserve enterprise trust by separating retrieved evidence from model inference
5. stay safe around proprietary semiconductor data boundaries

## 4. Recommended RAG Scope

### Agent 01 retrieval corpus

- historical coverage closure notes
- waiver logs and waiver rationales
- regression triage notes
- previous run-history decisions
- testcase or sequence review summaries
- verification methodology notes
- client-specific signoff expectations

### Agent 02 retrieval corpus

- prior lot review notes
- mis-bin investigation summaries
- ATE debug findings
- yield containment actions
- SPC excursion playbooks
- historical process-correlation observations
- product-engineering escalation guidelines

## 5. Semiconductor-Safe Data Model

The retrieval layer should not begin with a giant generic corpus. It should be segmented by enterprise, program, and workflow type.

Recommended document metadata:

- `doc_id`
- `enterprise_id`
- `program_id`
- `agent`
- `workflow_type`
- `chip_type`
- `artifact_type`
- `source_type`
- `created_at`
- `owner_team`
- `sensitivity`
- `tags`
- `text`

Recommended `source_type` values:

- `closure_note`
- `waiver_note`
- `regression_debug_note`
- `yield_review_note`
- `spc_playbook`
- `signoff_policy`
- `run_history_summary`
- `methodology_doc`

Recommended `sensitivity` values:

- `internal_sanitized`
- `client_confidential`
- `program_restricted`

This metadata is what makes retrieval safe and filterable in enterprise contexts.

## 6. Proposed RAG Architecture

### Ingestion pipeline

1. accept a document, note set, or prior run export
2. normalize metadata
3. chunk long documents
4. generate embeddings
5. store embeddings + metadata in the vector index
6. store canonical text in the relational store

### Retrieval pipeline

1. parse the active artifact
2. derive retrieval query from:
   - parser output
   - run profile
   - enterprise policy
   - chip type
   - workflow mode
3. apply metadata filters
4. retrieve top-k chunks
5. rerank retrieved chunks if needed
6. pass top evidence to orchestration
7. pass orchestration + evidence to analysis call

### Generation pipeline

1. model receives parsed artifact + orchestration plan + retrieved evidence
2. decisions include:
   - rationale
   - confidence
   - retrieved evidence references
   - clear separation between retrieved fact and model inference

## 7. Retrieval Flow by Agent

### Agent 01 flow

1. parse coverage or regression artifact
2. identify likely hot spots
3. form a retrieval query using:
   - covergroups
   - bin names
   - test names
   - cluster labels
   - design or IP identity
4. retrieve:
   - prior closure notes
   - waivers
   - regression debug notes
   - similar past runs
5. use retrieved context to:
   - avoid re-raising known waivers as critical gaps
   - prioritize historically high-blast-radius clusters
   - cite previous closure knowledge in decisions

### Agent 02 flow

1. parse ATE or SPC artifact
2. identify anomaly patterns
3. form a retrieval query using:
   - lot pattern
   - bin behavior
   - leakage/frequency signatures
   - process-related hints
4. retrieve:
   - previous lot review notes
   - process excursion patterns
   - historical binning review notes
   - SPC escalation playbooks
5. use retrieved context to:
   - identify repeat patterns faster
   - route actions to the right engineering function
   - justify escalation based on historical precedent

## 8. RAG Safety Principles

For semiconductor enterprise use, the retrieval layer should follow these constraints:

1. metadata filtering before semantic retrieval
2. no cross-client retrieval mixing
3. no unrestricted global memory
4. clear source attribution in outputs
5. support for sanitized-only pilot mode
6. document-level ownership and deletion path

This is especially important because semiconductor logs, waiver notes, and yield investigations can contain highly sensitive IP and manufacturing signals.

## 9. What the Output Should Look Like

When RAG is added, decisions should evolve from:

- generic rationale text

to:

- parsed evidence from current artifact
- retrieved evidence from historical context
- model inference connecting the two

Recommended output shape per decision:

- `current_evidence`
- `retrieved_evidence`
- `retrieved_sources`
- `inference`
- `action`
- `priority`
- `confidence`

This separation is critical for enterprise trust.

## 10. Recommended Phase Plan

### Phase R1: Retrieval-ready history

Use what already exists:

- run history
- feedback
- raw artifact replay
- orchestration payloads

Goal:

- derive retrieval documents from saved runs before introducing broader document ingestion

Status: implemented.

### Phase R2: Document ingestion MVP

Add:

- upload endpoint for notes or sanitized engineering docs
- metadata form
- chunking
- embedding generation
- vector index storage

Goal:

- support a small enterprise knowledge base for one pilot program

Status: implemented for manual note ingestion and deterministic chunking.

### Phase R3: Runtime retrieval

Add:

- retrieval query builder
- metadata filters
- top-k retrieval
- evidence injection into orchestration and analysis

Goal:

- true RAG behavior during Agent 01 and Agent 02 runs

Status: implemented for both Agent 01 and Agent 02 with metadata-filtered retrieval and runtime context injection.

### Phase R4: Retrieval citations in UI

Add:

- retrieved-evidence panel
- cited source labels in decision cards
- run-history replay of retrieved chunks

Goal:

- make RAG visible and auditable in the product

Status: partially implemented. Decision cards now show retrieved source citations; a dedicated evidence-review panel and run-history replay of retrieved chunks are still pending.

## 11. Suggested Initial Technology Pattern

Keep this simple at first:

- relational store:
  - PostgreSQL
- vector store:
  - PostgreSQL + pgvector
  - or a dedicated vector DB later if scale requires it
- embedding model:
  - provider chosen based on deployment constraints and data policy

Why this is a good first step:

- keeps pilot architecture compact
- easier to deploy on Render/Postgres
- easier to explain to sponsors

## 12. Best First Retrieval Source

The best first corpus is not broad enterprise documentation.

It is:

- saved run history converted into retrieval documents

Why:

- already structured
- already relevant
- already tied to agent workflows
- lower governance burden than arbitrary document ingestion

This lets Silicon Agents become retrieval-enhanced using its own pilot history first.

## 13. Bottom Line

The product is not missing a RAG foundation; it is missing the retrieval layer itself.

The current architecture already provides:

- parsing
- orchestration
- persistence
- provenance
- pilot metrics

That is exactly the right base for adding enterprise-safe RAG next.

The most practical first implementation is:

`run history -> retrieval documents -> pgvector -> runtime retrieval -> cited decisions`
