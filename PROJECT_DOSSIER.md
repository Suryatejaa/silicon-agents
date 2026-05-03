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

The frontend currently includes 4 product pages:

1. `Home / Executive Brief`
2. `Agent 01`
3. `Agent 02`
4. `Enterprise Configuration`

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
- Enterprise orchestration support

### Enterprise customization delivered

- Centralized enterprise configuration page
- Separate saved setup for Agent 01 and Agent 02
- Chip-specific operating context
- Client workflow profile
- Custom review instructions
- Historical reference data
- Two-stage orchestration before analysis

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
Streaming response / HTML export / stored feedback
```

### Product-level flows

#### Agent 01 flow

1. User uploads or pastes a coverage or regression artifact.
2. Backend parses the artifact into structured report objects.
3. Enterprise orchestration builds a run-specific prompt plan.
4. Analysis agent runs the 5-step reasoning flow.
5. Decisions are ranked and streamed to the UI.
6. Benchmark scoring can run for known bundled artifacts.
7. User can export a verification brief and/or submit feedback.

#### Agent 02 flow

1. User pastes or loads ATE or SPC data.
2. Backend parses CSV into structured yield / SPC report objects.
3. Enterprise orchestration builds a run-specific prompt plan.
4. Analysis agent runs the 5-step reasoning flow.
5. Decisions are ranked and streamed to the UI.
6. Stored decisions are persisted for later feedback or review.

## 4. Architectural Layers

The currently implemented system is best described as **8 functional layers**.

### Layer 1. Experience Layer

Files:

- [frontend/index.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/index.html)
- [frontend/agent01.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/agent01.html)
- [frontend/agent02.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/agent02.html)
- [frontend/configuration.html](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/frontend/configuration.html)

Responsibilities:

- navigation
- input collection
- step-by-step reasoning display
- decision review
- benchmark and impact visibility
- configuration management

### Layer 2. API / App Shell Layer

Files:

- [main.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/main.py)
- [silicon_agents/api/router_verify.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_verify.py)
- [silicon_agents/api/router_yield.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_yield.py)
- [silicon_agents/api/router_feedback.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_feedback.py)
- [silicon_agents/api/router_benchmark.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/api/router_benchmark.py)

Responsibilities:

- HTTP entrypoint
- static page routing
- sample data routing
- SSE response streaming
- request size enforcement
- benchmark and feedback endpoints

### Layer 3. Schema / Contract Layer

File:

- [silicon_agents/core/schemas.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/core/schemas.py)

Responsibilities:

- typed request models
- typed parsed-report models
- typed decision models
- benchmark request / response models
- export request model

### Layer 4. Parser Layer

Files:

- [silicon_agents/parsers/coverage_parser.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/parsers/coverage_parser.py)
- [silicon_agents/parsers/regression_parser.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/parsers/regression_parser.py)
- [silicon_agents/parsers/ate_parser.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/parsers/ate_parser.py)

Responsibilities:

- convert raw text / CSV into `ParsedReport`
- extract coverpoints, failures, anomalies, trend points
- normalize report metadata and summaries

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
- [silicon_agents/storage/feedback_store.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/storage/feedback_store.py)
- [silicon_agents/benchmarks/agent01_scorecard.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/benchmarks/agent01_scorecard.py)

Responsibilities:

- verification brief export
- JSON report formatting
- SQLite persistence
- feedback capture
- benchmark evaluation

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
- expose API routes
- expose `/health`

### 5.2 Request models

#### Verification request

`VerifyRequest` fields:

- `report_text`
- `format`
- `mode`
- `design_name`
- `project_id`
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
- `done`: emits totals and provider summary

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
- links into Agent 01, Agent 02, and configuration

### Agent 01 UX

Purpose:

- verification-first sponsor-grade demo

Current UX features:

- artifact upload and drag-drop
- benchmark sample loader
- runtime status cards
- impact snapshot
- first recommended action summary
- benchmark scorecard
- orchestration preview
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
- status metrics
- orchestration preview
- step-wise streaming trace
- disabled controls while analysis is running
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
- editable project metadata
- editable chip / client / instruction fields
- local browser persistence
- saved configuration summary

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
- Gemini model default: `gemini-2.5-flash`
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

- in browser local storage
- separately for Agent 01 and Agent 02

This is adequate for local demos but not yet multi-user or server-backed.

## 11. Benchmarking and Evaluation

### Sample artifacts currently included

Verification:

- `coverage_vcs_sample.log`
- `coverage_xcelium_sample.log`
- `regression_sample.log`

Yield:

- `ate_parametric_sample.csv`
- `spc_trend_sample.csv`

Configuration:

- `client_profiles.json`

### In-product benchmarking

Current benchmarking is implemented for Agent 01.

Capabilities:

- list known benchmarks
- evaluate decisions against expected findings
- grade action alignment
- estimate review time saved

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

File:

- [silicon_agents/output/report_html.py](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/silicon_agents/output/report_html.py)

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

## 13. Persistence and Feedback

### What is persisted

- streamed decisions after a run
- user feedback on decisions

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

## 14. File and Module Inventory

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
```

### Support areas

```text
sample_data/
cli/
tests/
devlog/
```

## 15. Automated Testing Status

The repo includes automated tests from the beginning.

Current test coverage areas include:

- parsers
- agents
- API endpoints
- benchmark evaluation
- orchestration schema behavior
- feedback storage

Current observed suite status in this workspace:

- `18/18` tests passing

Notes:

- Python 3.9 environment warnings are currently visible from dependency stack
- Gemini network calls fail in sandboxed test runs and correctly fall back to mock mode

## 16. Current Technical Constraints

### Implemented constraints

- local-first
- no auth
- no RBAC
- no multi-user persistence
- no server-side enterprise config persistence
- no direct EDA integration
- no job queue
- no long-term memory beyond SQLite feedback and local browser config

### Practical limitations

- enterprise configuration is browser-local today
- UI is still vanilla HTML rather than componentized frontend architecture
- Agent 02 is functional but not yet as sponsor-ready as Agent 01
- sample data is still synthetic / benchmark-oriented
- there is no production deployment packaging yet

## 17. Current Product Readiness Assessment

### Strongest areas

- clear Agent 01 wedge
- real parser + orchestration + streaming loop
- benchmark-backed demo path
- exportable sponsor artifact
- centralized enterprise configuration model
- human-in-the-loop review posture

### Areas still considered MVP / pre-pilot

- production deployment model
- auth and enterprise tenancy
- richer benchmark corpus
- server-side config management
- audit trails beyond basic feedback store
- real customer artifact integration

## 18. Recommended Next Engineering Steps

1. Move enterprise configuration from browser local storage to backend persistence.
2. Add auth, role boundaries, and workspace-level project separation.
3. Expand Agent 01 benchmark corpus with 10 to 20 richer sanitized artifacts.
4. Add file upload persistence and artifact history.
5. Improve Agent 02 parity so it feels closer to Agent 01 in sponsor readiness.
6. Add structured export targets for Jira / Confluence / email-ready formats.
7. Add observability and per-run logging for pilot environments.

## 19. One-Line Summary

Silicon Agents today is a verification-first semiconductor AI workflow platform with:

- 2 agents
- 4 frontend pages
- 8 implemented functional layers
- 5 prompt families
- 2-stage orchestration + analysis LLM flow
- SSE-based step streaming
- benchmark scoring
- exportable reporting
- SQLite-backed decisions and feedback
- centralized enterprise configuration for both agents
