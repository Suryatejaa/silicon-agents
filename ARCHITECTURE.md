# Silicon Agents Architecture

This summary consolidates the attached architecture documents into a repo-native reference.

## What Silicon Agents Is

Silicon Agents is an orchestration layer above EDA and manufacturing test tooling. It does not replace VCS, Xcelium, or ATE systems. It reads their outputs, reasons about them, and turns them into prioritised next actions for engineers.

## Product Focus

The near-term sponsor-grade MVP is verification-first. Agent 01 is the primary product wedge because verification consumes the largest engineering effort in most chip programs and is the easiest workflow to position as a high-ROI AI copilot.

## Two Initial Agents

### Agent 01: Verification

Inputs:

- coverage reports from VCS or Xcelium
- regression logs
- optional design context

Outputs:

- coverage gap summary
- root-cause explanations
- directed test or constraint suggestions
- prioritised action plan
- regression failure clusters

### Agent 02: Yield

Agent 02 remains a roadmap and adjacent workflow expansion. It is useful for demonstrating platform extensibility, but the current product story should lead with Agent 01.

Inputs:

- ATE parametric CSV data
- SPC lot trend data
- optional bin specification context

Outputs:

- anomaly summary
- likely mis-bin recommendations
- SPC drift alerts
- estimated business impact

## Six-Layer Pipeline

1. Input interface: accept raw file or pasted text
2. Parser layer: convert raw text into structured schemas
3. Orchestration layer: combine chip context, client instructions, and historical reference data into a run-specific prompt plan
4. Reasoning and analysis: produce the five-step chain
5. Decision layer: extract actions and rank them
6. Output layer: HTML, CLI, and JSON views
7. Feedback and memory: capture accept or reject signals

## Five-Step Reasoning Experience

1. Parse
2. Detect
3. Analyse
4. Recommend
5. Prioritise

The visible step-by-step stream is part of the product value. It helps the system feel like an agent, not just a one-shot chatbot response.

## Enterprise Flexibility

The target product should not lock clients into one hard-coded verification or yield style. Different chip programs need different operating instructions, historical baselines, and review priorities.

The current architecture now supports:

- chip-specific context such as controller, CPU, DSP, PMIC, or mixed-signal program type
- client-specific workflow instructions and review preferences
- historical logs or prior analysis notes as additional reference data
- a two-stage LLM pattern where prompt orchestration happens before analysis

This is the basis for a future enterprise configuration layer rather than a one-size-fits-all agent.

## MVP Strategy

- use public and synthetic data to prove the workflow
- keep the product local-first and easy to demo
- build trust through explainability and explicit approval
- never auto-apply changes to design or binning flows
