# Silicon Agents Project Dossier

This document summarizes what has been designed and implemented so far in the Silicon Agents MVP repository. It is intended to function as a current-state engineering, product, and architecture reference.

## 1. Executive Summary

Silicon Agents is an AI workflow copilot for semiconductor engineering.

The current product wedge is:

- `Agent 01`: Verification Workflow Copilot
  - coverage closure
  - regression triage

The current adjacent expansion workflow is:

- `Agent 02`: Yield Intelligence Copilot
  - ATE anomaly detection and binning review
  - SPC drift analysis

The platform is designed as an orchestration layer above existing semiconductor tools rather than a replacement for them. It reads raw artifacts, converts them into structured representations, applies enterprise context, invokes LLM reasoning, produces ranked actions, and captures human feedback.

## 2. Current Scope Delivered

### Product pages delivered

The frontend currently includes 8 product pages:

1. `Home / Executive Brief`
2. `Agent 01`
3. `Agent 02`
4. `Enterprise Configuration`
5. `Run History`
6. `Pitch Deck`
7. `Pilot Dashboard`
8. `Product Docs`

### Active workflow scope

#### Agent 01

- Coverage report ingestion
- Regression log ingestion
- Artifact upload and local file reading
- Benchmark artifact loading
- 5-step streamed reasoning
- Ranked decision queue
- Accept / reject feedback capture
- Benchmark scorecard
- Verification brief export

#### Agent 02

- ATE CSV ingestion
- SPC CSV ingestion
- 5-step streamed reasoning
- Ranked yield / SPC action stream
- Accept / reject feedback capture
- Benchmark scorecard
- Yield brief export
- Jira-ready export
- Email-ready export
- Enterprise orchestration support

### Enterprise customization delivered

- Centralized enterprise configuration page
- Separate saved setup for Agent 01 and Agent 02
- Server-backed enterprise policy persistence
- Organization-specific review and evidence policy
- Escalation and output-style guidance
- Reference-data weighting guidance
- Two-stage orchestration before analysis

### Run governance and observability delivered

- Persisted run history in SQLite
- Raw artifact persistence per saved run
- Artifact provenance persistence per saved run
- Parser format, confidence, and warning persistence
- Per-run provider and model tracking
- Per-run latency and status tracking
- Stored orchestration preview payload
- Stored analysis trace and decision payload
- Export history per run
- Feedback visibility per saved run
- Pilot metrics aggregation across saved runs
- Pilot access-code generation utility

### Pilot access and deployment delivered

- Dockerfile
- docker-compose deployment packaging
- Render deployment manifest
- Pilot access login page
- Header-based pilot token enforcement
- Browser-session cookie unlock flow
- Request logging middleware for pilot usage visibility

## 3. High-Level Architecture

### System intent

Silicon Agents is structured as a workflow intelligence layer that sits above:

- verification simulators and reports
- regression infrastructure
- ATE outputs
- SPC trend exports

It does not directly edit RTL, UVM testbenches, manufacturing systems, or binning rules automatically.

### HLD view

```text
User / Engineer
    ->
Frontend pages
    ->
FastAPI application
    ->
Request schema validation
    ->
Artifact parser layer
    ->
Enterprise orchestration layer
    ->
LLM analysis layer
    ->
Decision extraction and ranking
    ->
Streaming response / run persistence / structured exports / stored feedback
```

### Product-level flows

#### Agent 01 flow

1. User uploads or pastes a coverage or regression artifact.
2. Backend parses the artifact into structured report objects.
3. Enterprise orchestration builds a run-specific prompt plan.
4. Analysis agent runs the 5-step reasoning flow.
5. Decisions are ranked and streamed to the UI.
6. Benchmark scoring can run for known bundled artifacts.
7. Run data is persisted with scorecard, observability, feedback, and export trail.
8. User can export a verification brief, Jira payload, email payload, and/or submit feedback.

#### Agent 02 flow

1. User pastes or loads ATE or SPC data.
2. Backend parses CSV into structured yield / SPC report objects.
3. Enterprise orchestration builds a run-specific prompt plan.
4. Analysis agent runs the 5-step reasoning flow.
5. Decisions are ranked and streamed to the UI.
6. Benchmark or live scorecard evaluation can run after completion.
7. Run data is persisted for later feedback, export, review, and audit.
8. User can export a yield brief, Jira payload, email payload, and/or submit feedback.

## 4. Architectural Layers

The currently implemented system is best described as **8 functional layers**.

### Layer 1. Experience Layer

Files:

- [frontend/index.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/index.html)
- [frontend/agent01.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/agent01.html)
- [frontend/agent02.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/agent02.html)
- [frontend/configuration.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/configuration.html)
- [frontend/history.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/history.html)
- [frontend/pitch.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/pitch.html)
- [frontend/pilot.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/pilot.html)
- [frontend/docs.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/docs.html)
- [frontend/pilot_access.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/pilot_access.html)

Responsibilities:

- navigation
- input collection
- step-by-step reasoning display
- decision review
- benchmark and impact visibility
- configuration management
- run-history review and workflow exports
- pilot evidence visualization
- pilot access unlock flow
- long-form product documentation

### Layer 2. API / App Shell Layer

Files:

- [main.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/main.py)
- [silicon_agents/api/router_verify.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_verify.py)
- [silicon_agents/api/router_yield.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_yield.py)
- [silicon_agents/api/router_feedback.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_feedback.py)
- [silicon_agents/api/router_benchmark.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_benchmark.py)
- [silicon_agents/api/router_config.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_config.py)

Responsibilities:

- HTTP entrypoint
- static page routing
- sample data routing
- SSE response streaming
- request size enforcement
- benchmark and feedback endpoints
- configuration endpoints
- run-history and structured-export endpoints
- pilot metrics endpoint
- pilot access-code generation endpoint
- browser pilot-gate enforcement

### Layer 3. Schema / Contract Layer

File:

- [silicon_agents/core/schemas.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/core/schemas.py)

Responsibilities:

- typed request models
- typed parsed-report models
- typed decision models
- benchmark request / response models
- export request model
- run-history, export-history, and feedback-summary models

### Layer 4. Parser Layer

Files:

- [silicon_agents/parsers/coverage_parser.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/parsers/coverage_parser.py)
- [silicon_agents/parsers/regression_parser.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/parsers/regression_parser.py)
- [silicon_agents/parsers/ate_parser.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/parsers/ate_parser.py)

Responsibilities:

- convert raw text / CSV into `ParsedReport`
- extract coverpoints, failures, anomalies, trend points
- normalize report metadata and summaries
- emit parser confidence and parser warnings

### Layer 5. Enterprise Orchestration Layer

File:

- [silicon_agents/orchestration/prompt_orchestrator.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/orchestration/prompt_orchestrator.py)

Responsibilities:

- synthesize chip context
- synthesize client workflow style
- synthesize historical notes
- build compact run-specific prompt plans

### Layer 6. LLM Reasoning Layer

Files:

- [silicon_agents/core/llm.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/core/llm.py)
- [silicon_agents/prompts/coverage_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/coverage_prompt.py)
- [silicon_agents/prompts/regression_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/regression_prompt.py)
- [silicon_agents/prompts/ate_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/ate_prompt.py)
- [silicon_agents/prompts/spc_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/spc_prompt.py)

Responsibilities:

- provider abstraction
- Gemini / OpenAI selection
- fallback-to-mock behavior
- JSON-oriented response generation
- streamed model output

### Layer 7. Agent and Decision Layer

Files:

- [silicon_agents/agents/agent01_verify.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/agents/agent01_verify.py)
- [silicon_agents/agents/agent02_yield.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/agents/agent02_yield.py)
- [silicon_agents/agents/decision_layer.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/agents/decision_layer.py)

Responsibilities:

- workflow-specific orchestration
- fallback reasoning
- decision extraction
- decision enrichment
- ranking and deduplication
- SSE event sequencing

### Layer 8. Output / Memory / Evaluation Layer

Files:

- [silicon_agents/output/report_html.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/output/report_html.py)
- [silicon_agents/output/report_json.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/output/report_json.py)
- [silicon_agents/output/report_structured.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/output/report_structured.py)
- [silicon_agents/storage/feedback_store.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/storage/feedback_store.py)
- [silicon_agents/benchmarks/agent01_scorecard.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/benchmarks/agent01_scorecard.py)
- [silicon_agents/benchmarks/agent02_scorecard.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/benchmarks/agent02_scorecard.py)
- [silicon_agents/benchmarks/run_scorecard.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/benchmarks/run_scorecard.py)

Responsibilities:

- verification brief export
- structured Jira / email export formatting
- JSON report formatting
- SQLite persistence
- feedback capture
- benchmark evaluation
- per-run scorecard persistence
- export audit persistence
- pilot metrics aggregation over stored runs

## 5. Low-Level Design

### 5.1 App entrypoint

File:

- [main.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/main.py)

Current FastAPI responsibilities:

- initialize `FeedbackStore`
- mount frontend static directory
- mount sample-data directory
- expose product pages:
  - `/`
  - `/agent01`
  - `/agent02`
  - `/configuration`
  - `/history`
  - `/pitch`
  - `/pilot`
  - `/product-docs`
  - `/pilot-login`
- expose API routes
- expose `/health`
- enforce optional pilot token protection
- expose `/pilot/unlock`

### 5.2 Request models

#### Verification request

`VerifyRequest` fields:

- `report_text`
- `format`
- `mode`
- `design_name`
- `project_id`
- `artifact_name`
- `artifact_source`
- `run_profile_id`
- `run_profile_name`
- `context`
- `chip_type`
- `client_profile`
- `custom_instructions`
- `reference_data`
- `reference_data_label`

#### Yield request

`YieldRequest` fields:

- `csv_data`
- `lot_id`
- `mode`
- `project_id`
- `artifact_name`
- `artifact_source`
- `run_profile_id`
- `run_profile_name`
- `context`
- `chip_type`
- `client_profile`
- `custom_instructions`
- `reference_data`
- `reference_data_label`

### 5.3 Event model

The UI consumes streamed SSE events.

Current event types:

- `orchestration`
- `step`
- `chunk`
- `decision`
- `done`

Meaning:

- `orchestration`: displays the synthesized prompt plan
- `step`: opens a new step in the 5-step reasoning trace
- `chunk`: step text or reasoning text
- `decision`: adds a ranked finding/action to the review queue
- `done`: emits totals, provider summary, persisted `run_id`, and model summary

### 5.4 Agent 01 internals

#### Modes

- `coverage`
- `triage`

#### Coverage pipeline

1. Parse coverage report
2. Identify gaps
3. Generate fallback decisions
4. Run orchestration
5. Run LLM analysis
6. Enrich decisions with evidence and rank basis
7. Stream 5-step trace + decisions

#### Triage pipeline

1. Parse regression log
2. Identify failures
3. Cluster failures
4. Generate fallback decisions
5. Run orchestration
6. Run LLM analysis
7. Enrich decisions with evidence and samples
8. Stream 5-step trace + decisions

### 5.5 Agent 02 internals

#### Modes

- `ate`
- `spc`

#### ATE pipeline

1. Parse ATE CSV
2. Build fallback mis-bin / anomaly decisions
3. Run orchestration
4. Run LLM analysis
5. Stream 5-step trace + decisions

#### SPC pipeline

1. Parse SPC CSV
2. Build fallback drift decisions
3. Run orchestration
4. Run LLM analysis
5. Stream 5-step trace + decisions

### 5.6 Decision enrichment

Current decision enrichment includes:

- priority
- confidence
- effort
- evidence text
- rank basis
- workflow-stage metadata
- group or cluster context
- representative tests for triage

## 6. UI / UX Delivered So Far

### Global shell

All major pages now use a consistent global header with:

- product branding
- global navigation
- page-local active state
- `file://`-safe and server-safe routing

### Home / Executive Brief

Purpose:

- sponsor-facing overview
- product wedge explanation
- adoption framing
- live demo-readiness signal

Current UX elements:

- executive narrative
- KPI cards
- adoption path
- runtime status
- latest-runs widget
- links into Agent 01, Agent 02, pitch, pilot dashboard, configuration, docs, and run history

### Agent 01 UX

Purpose:

- verification-first sponsor-grade demo

Current UX features:

- artifact upload and drag-drop
- benchmark sample loader
- artifact source visibility
- artifact analysis summary card
- runtime status cards
- impact snapshot
- first recommended action summary
- benchmark scorecard
- orchestration preview
- parser trust visibility
- separate decision review queue
- separate analysis trace
- loading spinners with step-wise progression
- disabled controls while analysis is running
- verification brief export
- feedback capture via accept / reject buttons
- hidden enterprise configuration from workspace
- reads enterprise setup from the dedicated configuration page

### Agent 02 UX

Purpose:

- show platform extensibility into yield / SPC workflows

Current UX features:

- ATE/SPC mode selector
- sample data loading
- artifact source visibility
- status metrics
- impact snapshot
- benchmark scorecard
- orchestration preview
- separate decision review queue
- separate analysis trace
- step-wise streaming trace
- disabled controls while analysis is running
- yield brief export
- Jira/email direct export actions
- feedback capture via accept / reject buttons
- hidden enterprise configuration from workspace
- reads enterprise setup from the dedicated configuration page

### Enterprise Configuration UX

Purpose:

- remove enterprise setup from operator workspace
- centralize chip-program configuration

Current UX features:

- one page
- two sections:
  - Agent 01 configuration
  - Agent 02 configuration
- profile template selection
- policy-oriented governance fields
- organization / review / evidence policy fields
- backend SQLite persistence
- saved configuration summary

### Pilot Dashboard UX

Purpose:

- turn saved runs into sponsor-grade pilot evidence
- expose operational sharing utilities for protected pilot deployments

Current UX features:

- pilot evidence summary metrics
- agent/provider/artifact-source breakdowns
- parser warning visibility
- recent pilot runs
- pilot access-code generation utility
- direct navigation into run history and docs

### Product Docs UX

Purpose:

- provide detailed product, workflow, and field-level documentation for sponsors, delivery teams, and pilot users

Current UX features:

- left navigation index
- architecture overview
- agent workflow explanation
- enterprise policy explanation
- field-by-field request and run-history reference
- pilot operations guidance
- current API surface summary

### Run History UX

Purpose:

- make the platform auditable and pilot-ready
- expose saved run details, scorecards, feedback, and exports

Current UX features:

- recent run listing
- filter by agent and project
- saved run detail inspection
- benchmark and live score visibility
- feedback summary and feedback history
- export history visibility
- Jira/email export actions from saved runs

## 7. Backend Stack

### Languages and runtime

- Python 3.x

### Frameworks and libraries

From [requirements.txt](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/requirements.txt):

- `fastapi`
- `uvicorn[standard]`
- `google-genai`
- `openai`
- `pydantic`
- `pandas`
- `numpy`
- `scipy`
- `aiosqlite`
- `python-dotenv`
- `click`
- `pytest`
- `httpx`

### Persistence

- SQLite
- async path: `aiosqlite`
- sync fallback path: builtin `sqlite3`

### Data storage tables

Current tables:

- `decisions`
- `feedback`
- `enterprise_config`
- `run_history`
- `export_history`

Stored decision fields:

- ID
- project ID
- type
- target
- action
- rationale
- priority
- confidence
- effort
- status
- metadata JSON

Stored feedback fields:

- decision ID
- project ID
- accepted / rejected
- notes
- engineer ID
- timestamp

Stored enterprise config fields:

- agent key
- organization
- review board
- output style
- escalation policy
- evidence policy
- enterprise instruction addendum
- timestamp

Stored run-history fields:

- run ID
- agent
- mode
- project ID
- artifact name
- artifact source
- raw artifact
- run profile ID and name
- parser format, confidence, and warnings
- provider and model
- latency
- benchmark / live scorecard summary
- orchestration payload
- analysis trace
- decisions JSON
- feedback summary
- export history
- status
- timestamp

## 8. Frontend Stack

Current frontend stack is intentionally simple and local-first:

- vanilla HTML
- embedded CSS
- embedded JavaScript
- no frontend framework
- no build system

This keeps the prototype easy to run locally and easy to demo in sponsor settings.

## 9. LLM Architecture

### Providers implemented

Current provider abstraction:

- `Gemini` via `google.genai`
- `OpenAI` via `openai`
- deterministic `mock` fallback

### Provider selection behavior

`LLMProvider` behavior:

1. try primary provider from env
2. try secondary provider
3. if both fail or are unavailable, use mock fallback

### Current model configuration

From [silicon_agents/core/config.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/core/config.py):

- primary provider env: `SA_LLM_PRIMARY`
- Gemini model default: `gemini-2.5-pro`
- Gemini fallback model: `gemini-2.5-flash`
- OpenAI model default: `gpt-4o`

### LLM usage pattern

The platform currently supports a **2-call LLM pattern** for enterprise runs:

#### Call 1. Orchestration call

Purpose:

- build a run-specific prompt plan using:
  - chip type
  - client profile
  - custom instructions
  - reference data
  - parsed artifact summary

#### Call 2. Analysis call

Purpose:

- perform domain reasoning using:
  - domain system prompt
  - current parsed artifact
  - orchestrated prompt plan

### Prompt taxonomy

The current implementation includes **5 prompt families**.

#### 1. Orchestrator system prompt

File:

- [silicon_agents/orchestration/prompt_orchestrator.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/orchestration/prompt_orchestrator.py)

Purpose:

- transform enterprise inputs into a compact prompt plan

Expected JSON fields:

- `chip_focus`
- `instruction_overrides`
- `reference_priorities`
- `analysis_directives`
- `output_emphasis`
- `prompt_addendum`

#### 2. Coverage system prompt

File:

- [silicon_agents/prompts/coverage_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/coverage_prompt.py)

Purpose:

- verification closure reasoning
- coverage-gap prioritization
- realistic UVM/verification-style next actions

#### 3. Regression system prompt

File:

- [silicon_agents/prompts/regression_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/regression_prompt.py)

Purpose:

- regression triage
- failure clustering
- common-cause investigation suggestions

#### 4. ATE system prompt

File:

- [silicon_agents/prompts/ate_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/ate_prompt.py)

Purpose:

- ATE parametric reasoning
- mis-bin detection
- yield action generation

#### 5. SPC system prompt

File:

- [silicon_agents/prompts/spc_prompt.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/prompts/spc_prompt.py)

Purpose:

- lot-to-lot trend analysis
- drift identification
- escalation candidate generation

### Prompt types used in the codebase

The platform currently uses these prompt types:

1. `System prompts`
2. `Structured user prompts`
3. `Orchestration prompts`
4. `Fallback prompts / fallback text`
5. `JSON contract prompts`

### Analysis prompt structure

Current analysis prompts typically contain:

- response format requirements
- expected JSON contract
- design or lot identifier
- context
- chip type
- client profile
- custom instructions
- reference data excerpt
- orchestrated prompt plan
- parsed artifact JSON

### Output contract style

Current LLM analysis prompt contract expects:

- `parse`
- `detect`
- `analyse`
- `prioritise`
- `decisions`

### Reasoning style

All domain prompts enforce the same 5-step reasoning model:

1. parse
2. detect
3. analyse
4. recommend
5. prioritise

## 10. Prompt and Orchestration Strategy

### Why orchestration exists

Different semiconductor clients will not want the same review behavior.

Examples:

- one client may prioritize protocol escapes
- another may prioritize brownout recovery
- another may care most about mis-binning revenue recovery
- another may care most about SPC escalation policy

The orchestration layer exists so the product can adapt without forking the whole codebase for each client.

### What orchestration currently changes

It currently influences:

- chip focus statement
- instruction overrides
- reference-data priorities
- analysis directives
- output emphasis
- downstream prompt addendum

### Current storage model for enterprise config

Today, the enterprise config page stores settings:

- in backend SQLite
- separately for Agent 01 and Agent 02
- as durable top-level policy rather than per-run workspace context

This is stronger than the original local-demo implementation, but it is not yet multi-user or tenant-aware.

## 11. Benchmarking and Evaluation

### Sample artifacts currently included

Verification:

- `coverage_vcs_sample.log`
- `coverage_xcelium_sample.log`
- `regression_sample.log`
- `coverage_pcie_dma_sample.log`
- `coverage_lpddr_refresh_sample.log`
- `coverage_noc_qos_sample.log`
- `coverage_secure_boot_sample.log`
- `regression_pcie_dma_sample.log`
- `regression_audio_dsp_sample.log`
- `regression_secure_boot_sample.log`

Yield:

- `ate_parametric_sample.csv`
- `spc_trend_sample.csv`

Configuration:

- `client_profiles.json`

### In-product benchmarking

Current benchmarking is implemented for Agent 01 and Agent 02.

Capabilities:

- list known benchmarks
- evaluate decisions against expected findings
- grade action alignment
- estimate review time saved
- compute persisted run scorecards for saved-run review

### Evaluation dimensions

Current scorecard metrics include:

- overall score
- findings recall
- high-priority alignment
- first-action alignment
- evidence coverage
- matched expected findings

## 12. Export and Reporting

### Current export implemented

- verification brief HTML export
- yield brief HTML export
- Jira-ready structured export
- email-ready structured export

File:

- [silicon_agents/output/report_html.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/output/report_html.py)
- [silicon_agents/output/report_structured.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/output/report_structured.py)

Current export contents:

- executive summary
- top recommendation
- business impact
- risk posture
- pilot next step
- benchmark summary
- ranked decisions
- evidence
- rank basis
- analysis trace
- Jira-ready ticket payloads with summary, description, severity, and metadata
- email-ready payloads with subject, recipients placeholder, executive summary, and action list

## 13. Pilot Access and Deployment Readiness

### Pilot sharing model

The MVP now supports a lightweight pilot-protection model intended for controlled sharing before full enterprise auth exists.

Current behavior:

- if `PILOT_ACCESS_TOKEN` is empty, the app behaves like an open pilot build
- if `PILOT_ACCESS_TOKEN` is set:
  - browser users are redirected to `/pilot-login`
  - API clients must send `X-Pilot-Access-Token`
  - a successful browser unlock sets a session cookie for continued access

### Deployment artifacts

Current deployment packaging includes:

- [Dockerfile](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/Dockerfile)
- [docker-compose.yml](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/docker-compose.yml)
- [render.yaml](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/render.yaml)
- [.dockerignore](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/.dockerignore)

### Why this matters

This is the transition point from a laptop-only demo to a pilot that can be shared with an Infosys or client reviewer via URL without asking them to run Python locally.

## 14. Persistence and Feedback

### What is persisted

- streamed decisions after a run
- user feedback on decisions
- enterprise policy per agent
- full run history with observability and scorecards
- export audit history
- pilot evidence aggregates derived from persisted runs

### Feedback semantics

Current feedback states:

- accepted
- rejected
- refined

### Why feedback matters

This establishes the foundation for:

- reviewer learning
- future ranking calibration
- enterprise pilot studies
- outcome-based evaluation
- auditable engineering run replay

## 15. Pilot Metrics and Documentation Layer

### Pilot dashboard

The product now includes a dedicated pilot dashboard at:

- [frontend/pilot.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/pilot.html)

Its purpose is to expose measurable proof signals such as:

- total runs
- completed vs failed runs
- accepted vs rejected decisions
- parser confidence trends
- benchmark vs live scorecard mix
- export counts
- recent pilot activity

### Product documentation site

The product now includes a dedicated product docs experience at:

- [frontend/docs.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/docs.html)

Its purpose is to explain:

- architecture
- workflow lifecycle
- Agent 01 and Agent 02 use cases
- enterprise config importance
- field-by-field semantics
- pilot operations
- current API surface
- next-phase EDA/API integration direction

## 16. File and Module Inventory

### Core backend directories

```text
silicon_agents/
  agents/
  api/
  benchmarks/
  core/
  orchestration/
  output/
  parsers/
  prompts/
  storage/
```

### Frontend pages

```text
frontend/
  index.html
  agent01.html
  agent02.html
  configuration.html
  history.html
  pitch.html
  pilot.html
  docs.html
  pilot_access.html
```

### Support areas

```text
sample_data/
cli/
tests/
devlog/
```

## 17. Automated Testing Status

The repo includes automated tests from the beginning.

Current test coverage areas include:

- parsers
- agents
- API endpoints
- benchmark evaluation
- orchestration schema behavior
- feedback storage
- run history and structured exports

Current observed suite status in this workspace:

- `38/38` tests passing

Notes:

- Python 3.9 environment warnings are currently visible from dependency stack
- Gemini network calls fail in sandboxed test runs and correctly fall back to mock mode

## 18. Current Technical Constraints

### Implemented constraints

- local-first
- no auth
- no RBAC
- no multi-user persistence
- no direct EDA integration
- no job queue
- no long-term memory beyond SQLite-backed run, config, and feedback persistence

### Practical limitations

- UI is still vanilla HTML rather than componentized frontend architecture
- sample data is still synthetic / benchmark-oriented
- pilot access is still token-based rather than full auth / RBAC
- no tenant isolation or per-client workspace isolation
- no direct EDA/API integration layer yet
- no Confluence export yet

## 19. Current Product Readiness Assessment

### Strongest areas

- clear Agent 01 wedge
- real parser + orchestration + streaming loop
- benchmark-backed demo path
- exportable sponsor and workflow artifacts
- centralized enterprise configuration model
- human-in-the-loop review posture
- auditable run history and observability

### Areas still considered MVP / pre-pilot

- enterprise API integration for EDA workflows
- richer auth and enterprise tenancy
- richer benchmark corpus
- real customer artifact integration
- stronger parser coverage for heterogeneous client report formats
- pilot dashboard trend depth and downstream analytics

## 20. Recommended Next Engineering Steps

1. Expose enterprise integration APIs so EDA and review tools can submit artifacts and consume structured outcomes.
2. Expand benchmark corpus further with richer sanitized client-style artifacts.
3. Add deeper pilot dashboard trends and sponsor reporting views.
4. Improve parser tolerance for heterogeneous client report formats.
5. Add tenant-aware enterprise policy management and versioning.
6. Add Confluence-ready export and workflow integrations beyond Jira/email.
7. Introduce fuller auth, role boundaries, and workspace-level project separation.

## 21. One-Line Summary

Silicon Agents today is a verification-first semiconductor AI workflow platform with:

- 2 agents
- 8 frontend pages
- 8 implemented functional layers
- 5 prompt families
- 2-stage orchestration + analysis LLM flow
- SSE-based step streaming
- benchmark scoring
- HTML + Jira + email exportable reporting
- pilot dashboard, pilot access protection, and long-form product docs
- SQLite-backed runs, decisions, feedback, exports, parser trust, and enterprise policy
- centralized enterprise configuration plus workspace run profiles
