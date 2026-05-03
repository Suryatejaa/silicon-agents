# Silicon Agents

Silicon Agents is an AI workflow copilot for semiconductor engineering. The current product wedge focuses on the highest-friction workflow in fabless design organizations:

- Agent 01: verification coverage closure and regression triage

Agent 02 remains in the repository as a secondary workflow preview for ATE anomaly detection, binning validation, and SPC drift analysis.

This repository was scaffolded from the attached architecture, MVP strategy, and development plan documents. It now serves as a sponsor-facing prototype for a verification-first semiconductor AI product.

The implementation follows a six-layer design:

1. Input interface
2. Parser layer
3. Reasoning and analysis
4. Decision layer
5. Output generator
6. Feedback and memory

## MVP Scope

The repo is intentionally local-first but structured like a serious workflow product:

- FastAPI backend with SSE streaming
- Vanilla HTML frontend with a visible 5-step agent loop
- Direct local artifact upload for verification reports and logs
- Synthetic benchmark artifacts for controlled demos
- Built-in benchmark scorecard for Agent 01 sample artifacts
- One-click verification brief export for sponsor or client review
- Executive-style verification brief with business impact, risk posture, and pilot next step
- Enterprise orchestration layer for chip-specific instructions, historical logs, and custom analysis style
- Saved client profile templates for one-click demo switching across chip programs and workflow styles
- SQLite-backed enterprise policy, run history, feedback, and export audit trail
- Run history console with Jira-ready and email-ready exports
- Pilot access gate with a shared header token and browser unlock flow
- Deterministic offline reasoning fallback so the demo works without live API keys
- Optional Gemini/OpenAI provider hooks for later activation

Non-goals for the current prototype:

- Direct EDA tool integration
- Production deployment
- Multi-user auth
- Fine-tuning on proprietary client data

## Repository Layout

```text
silicon_agents/
  api/
  agents/
  core/
  output/
  parsers/
  prompts/
  storage/
frontend/
sample_data/
cli/
tests/
devlog/
```

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload
```

Then open `http://127.0.0.1:8000/`.

If `PILOT_ACCESS_TOKEN` is set, the app will redirect browsers to `/pilot-login` until the token is unlocked for that session. API clients can call protected routes with the `X-Pilot-Access-Token` header.

## Docker / Pilot Deployment

Build and run locally with Docker:

```bash
docker compose up --build
```

Deployment artifacts now included:

- [Dockerfile](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/Dockerfile)
- [docker-compose.yml](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/docker-compose.yml)
- [render.yaml](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/render.yaml)

Recommended pilot env values:

```env
PILOT_ACCESS_TOKEN=replace-with-shared-pilot-token
GEMINI_API_KEY=...
OPENAI_API_KEY=
DATABASE_URL=postgresql://...
SA_DB_PATH=./silicon_agents.db
SA_LOG_LEVEL=INFO
```

Recommended deployment split:

- `Frontend`: Vercel
- `Backend`: Render web service
- `Database`: Render PostgreSQL

Repository split for deployment:

- `Render backend repo`: `https://github.com/EchoLift/silicon-agent-mvp.git`
- `Vercel frontend repo`: your personal frontend deployment repo
- Render should be connected to the backend repo only, even though the codebase currently contains both frontend and backend assets.

Deployment notes:

- The backend now supports `DATABASE_URL` for PostgreSQL deployments and falls back to `SA_DB_PATH` for local SQLite development.
- If you host the frontend separately from the backend, open `Enterprise Config` and save the Render backend URL in `Deployment API Base`.
- Leave `Deployment API Base` blank for local same-origin runs.

## Core Endpoints

- `GET /health`
- `GET /pitch`
- `GET /pilot`
- `GET /product-docs`
- `POST /api/v1/verify`
- `POST /api/v1/yield`
- `POST /api/v1/feedback`
- `GET /api/v1/feedback/{project_id}`
- `GET /api/v1/decisions/{project_id}`
- `GET /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/{run_id}/export/jira`
- `GET /api/v1/runs/{run_id}/export/email`
- `GET /api/v1/pilot/metrics`
- `POST /api/v1/pilot/access-code/generate`

## Testing From Day One

The repo now includes a baseline automated test setup intended to stay in place from the first week of development:

```bash
make test-compile
make test
```

If `make` is unavailable:

```bash
PYTHONPYCACHEPREFIX=/tmp/sa-pycache python3 -m compileall silicon_agents main.py cli tests
PYTHONPYCACHEPREFIX=/tmp/sa-pycache python3 -m unittest discover -s tests -v
```

There is also a starter CI workflow at [.github/workflows/tests.yml](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/.github/workflows/tests.yml) so every push and PR can run the suite automatically once the repo is connected to Git hosting.

## Sample Demo Flow

1. Open the landing page.
2. Launch the verification workflow.
3. Upload a verification artifact or load a benchmark sample.
4. Watch the agent stream the five-stage reasoning process.
5. Review findings with evidence, ranking, and the benchmark scorecard.
6. Export a verification brief for sponsor or engineering review circulation.
7. Accept or reject recommendations to build the memory layer.
8. Open Run History to review saved runs, scorecards, feedback, and Jira/email exports.

Saved demo templates for enterprise profiles live in [sample_data/client_profiles.json](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/sample_data/client_profiles.json).

## Notes on LLM Use

The repo exposes a single `LLMProvider` interface. When provider keys and SDKs are available, it can try Gemini first and then OpenAI. If they are unavailable, it falls back to a deterministic local stream so the product loop remains runnable during early MVP development.

Agent 01 and Agent 02 now also support an enterprise-oriented two-stage prompt flow:

1. An orchestration pass synthesizes chip context, client instructions, and historical reference data into a run-specific prompt plan.
2. The analysis pass uses that plan to generate the ranked findings and actions.

This gives enterprise teams a path to tailor the agents without forking the product logic for every chip program.

## Planning Docs

- [DEV_PLAN.md](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/DEV_PLAN.md)
- [ARCHITECTURE.md](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/ARCHITECTURE.md)
- [EVALUATION_PLAN.md](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/EVALUATION_PLAN.md)
- [devlog/week01.md](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/devlog/week01.md)
- [devlog/week02.md](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/devlog/week02.md)
# silicon-agents
