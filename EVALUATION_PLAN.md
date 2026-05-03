# Silicon Agents Evaluation Plan

This document defines how the verification-first MVP should be evaluated in sponsor, internal, and early client conversations.

## Goal

Demonstrate that Silicon Agents Agent 01 can reduce the time required to review coverage and regression artifacts while producing recommendations that are credible enough for engineer review.

## Primary Workflow

- Coverage closure
- Regression triage

These two workflows form the current evaluation wedge because they map directly to schedule pressure in fabless verification organizations.

## Benchmark Artifact Set

The repository includes benchmark-style synthetic artifacts in [sample_data](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/sample_data):

- [coverage_vcs_sample.log](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/sample_data/coverage_vcs_sample.log)
- [coverage_xcelium_sample.log](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/sample_data/coverage_xcelium_sample.log)
- [regression_sample.log](/Volumes/D-Drive/Projects/Silicon-Agents-MVP/sample_data/regression_sample.log)

These are not sufficient for customer proof on their own, but they provide repeatable baselines for:

- parser accuracy
- workflow demo stability
- prompt iteration
- UI and review-flow testing
- benchmark scorecard grading inside Agent 01

## In-Product Scorecard

Agent 01 now includes a benchmark scorecard for the bundled artifacts. After a run completes, the UI compares the generated findings against the expected benchmark sheet and reports:

- expected findings matched
- high-priority alignment
- first-action alignment
- evidence coverage
- estimated review-time saved versus a manual first pass

This scorecard does not replace domain review, but it gives sponsor conversations a measurable and repeatable baseline instead of a purely anecdotal demo.

## Evaluation Questions

1. Does the parser correctly identify the critical bins, groups, or failure clusters?
2. Does the agent ground its recommendations in visible artifact evidence?
3. Are the top-ranked actions believable to a verification engineer?
4. Does the review flow reduce the time to decide what to investigate next?
5. Does the tool preserve human control and trust?

## Success Metrics

### Product Metrics

- Time to first ranked action
- Number of high-priority findings surfaced
- Evidence coverage per decision
- Acceptance rate of recommendations in review sessions
- Quality of orchestration when chip-specific instructions and historical data are supplied

### Workflow Metrics

- Estimated reduction in first-pass coverage review time
- Estimated reduction in regression triage time
- Reduction in manual scan effort across large logs
- Percentage of findings judged actionable by domain reviewers

## Review Rubric

Each finding should be judged on:

1. Correctness
2. Evidence grounding
3. Actionability
4. Priority quality
5. Trustworthiness

Suggested scoring:

- 0 = unusable
- 1 = weak
- 2 = acceptable
- 3 = strong

## Next Benchmark Upgrades

- Add 10 to 20 sanitized verification artifacts across protocol, DMA, reset, arbitration, and power-management scenarios
- Add expected finding sheets for each artifact
- Record time-to-review for manual and assisted analysis
- Capture reviewer accept/reject notes in the feedback store
- Add client-style evaluation runs where the same artifact is analyzed under different chip contexts and instruction sets

## Sponsor Story

The point of the benchmark set is not to claim full production readiness.
It is to show that:

- the workflow is real
- the problem is expensive
- the product can fit into existing verification practice
- the prototype can be evaluated systematically rather than anecdotally
