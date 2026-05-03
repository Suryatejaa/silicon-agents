# Silicon Agents MVP Development Plan

This plan is adapted directly from `silicon_agents_dev_plan.html` and aligned to the architecture and MVP strategy documents.

## Vision

Build a lightweight, local-first MVP that proves agentic AI can reduce the cognitive workload of chip design engineers in:

- verification coverage closure and regression triage
- ATE analysis, binning validation, and SPC drift monitoring

## Product Shape

- Backend: FastAPI
- Frontend: vanilla HTML and JavaScript
- Agents:
  - Agent 01: verification
  - Agent 02: yield
- Reasoning UX: visible five-step streamed reasoning loop
- LLM chain: Gemini primary, OpenAI fallback, offline mock fallback for local demos

## Phase Plan

### Phase 1: Core Engine

Timeline: Weeks 1-2

Deliverables:

- repo scaffold
- FastAPI app entrypoint
- shared schemas
- SSE streaming helpers
- coverage report parser
- Agent 01 coverage mode
- frontend with reasoning step viewer
- synthetic sample coverage reports
- tests for parser and verify flow

Definition of done:

- a developer can run the app locally
- a user can paste a coverage report
- the app streams five visible steps
- the system returns prioritised closure actions

### Phase 2: Agent Expansion

Timeline: Weeks 3-4

Deliverables:

- regression triage mode for Agent 01
- ATE parser and SPC trend parser
- Agent 02 anomaly and binning analysis
- SQLite feedback storage
- accept and reject actions in UI
- stored decision retrieval APIs

Definition of done:

- both agents run end-to-end with sample data
- decisions can be stored and feedback recorded
- yield analysis surfaces anomalies, mis-bins, and SPC alerts

### Phase 3: Demo Polish

Timeline: Weeks 5-6

Deliverables:

- CLI wrapper
- API key auth
- improved README and setup docs
- sample datasets packaged cleanly
- demo recording checklist
- weekly devlog complete

Definition of done:

- Seeder-ready demo
- repo understandable by a new engineer in one pass
- local setup documented and repeatable

## Architecture Principles

### Six Layers

1. Input layer
2. Parser layer
3. Reasoning and analysis layer
4. Decision layer
5. Output layer
6. Feedback and memory layer

### Deployment Modes

- Web UI for demo and rapid feedback
- CLI for power users
- REST API for enterprise integration

## MVP Constraints

- no direct EDA tool control
- no production deployment
- no proprietary client data required for Phase 1
- single-user local workflow is enough

## Engineering Backlog

### Now

- land the project skeleton
- validate the sample flows
- tighten prompt contracts and parsers
- stabilize streaming events and frontend UX

### Next

- richer coverage heuristics
- stronger yield confidence scoring
- CSV upload support in UI
- better decision rationales and export formats

### Later

- data partnerships and fine-tuning dataset creation
- project-aware memory
- CI integration
- demo hosting

