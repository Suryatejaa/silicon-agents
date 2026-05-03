"""Structured export builders for workflow systems."""

from __future__ import annotations

from silicon_agents.core.schemas import RunHistoryRecord, StructuredExportResponse


def build_jira_export(run: RunHistoryRecord) -> StructuredExportResponse:
    agent_label = "Agent 01" if run.agent == "agent01" else "Agent 02"
    workflow = _workflow_label(run)
    top_decision = run.decisions[0] if run.decisions else None
    priority = top_decision.priority if top_decision else "MEDIUM"
    summary_target = top_decision.target if top_decision else (run.runtime_label or run.project_id)
    title = f"{agent_label} {workflow} review: {summary_target}"

    description_lines = [
        f"Project: {run.project_id}",
        f"Agent: {agent_label}",
        f"Workflow: {workflow}",
        f"Artifact: {run.artifact_name or 'Not provided'}",
        f"Run profile: {run.run_profile_name or 'Custom workspace run'}",
        f"Model source: {run.provider}",
        f"Runtime label: {run.runtime_label or 'Not provided'}",
        f"Chip focus: {run.chip_type or 'Not provided'}",
        f"Latency: {run.duration_ms} ms",
        "",
        "Why this matters:",
        _jira_risk_posture(run),
        "",
        "Recommended actions:",
    ]
    if run.decisions:
        for idx, decision in enumerate(run.decisions[:5], start=1):
            description_lines.append(
                f"{idx}. [{decision.priority}] {decision.target}: {decision.action} "
                f"(confidence {round(decision.confidence * 100)}%, effort {decision.effort})"
            )
            if decision.metadata.get("evidence"):
                description_lines.append(f"   Evidence: {decision.metadata['evidence']}")
    else:
        description_lines.append("1. No decisions were generated in this run.")

    if run.analysis_log:
        description_lines.extend(["", "Analysis trace excerpts:"])
        for entry in run.analysis_log[:5]:
            description_lines.append(f"- {entry}")

    payload = {
        "issue_type": "Task" if run.agent == "agent01" else "Incident",
        "summary": title,
        "description": "\n".join(description_lines),
        "priority": priority,
        "labels": [
            "silicon-agents",
            run.agent,
            run.mode,
            _slug(run.chip_type or "semiconductor"),
        ],
        "custom_fields": {
            "project_id": run.project_id,
            "run_id": run.run_id,
            "artifact_name": run.artifact_name or "",
            "run_profile_id": run.run_profile_id or "",
            "run_profile_name": run.run_profile_name or "",
            "provider": run.provider,
            "model": run.model or "",
            "duration_ms": run.duration_ms,
            "decision_count": run.total_decisions,
        },
    }
    return StructuredExportResponse(
        format="jira",
        run_id=run.run_id,
        title=title,
        filename=f"{run.run_id}-jira.json",
        mime_type="application/json",
        payload=payload,
    )


def build_email_export(run: RunHistoryRecord) -> StructuredExportResponse:
    agent_label = "Agent 01" if run.agent == "agent01" else "Agent 02"
    workflow = _workflow_label(run)
    top_decision = run.decisions[0] if run.decisions else None
    subject = f"{agent_label} {workflow} summary for {run.runtime_label or run.project_id}"
    intro = (
        f"The latest {agent_label} run completed in {run.duration_ms} ms using {run.provider} "
        f"and generated {run.total_decisions} engineer-reviewable findings."
    )
    body_lines = [
        intro,
        "",
        f"Project: {run.project_id}",
        f"Artifact: {run.artifact_name or 'Not provided'}",
        f"Run profile: {run.run_profile_name or 'Custom workspace run'}",
        f"Chip focus: {run.chip_type or 'Not provided'}",
        "",
        "Top recommendation:",
        (
            f"{top_decision.target}: {top_decision.action}"
            if top_decision
            else "No top recommendation was produced in this run."
        ),
        "",
        "Risk summary:",
        _jira_risk_posture(run),
        "",
        "Decision queue:",
    ]
    if run.decisions:
        for decision in run.decisions[:5]:
            body_lines.append(
                f"- [{decision.priority}] {decision.target}: {decision.action} "
                f"(confidence {round(decision.confidence * 100)}%, effort {decision.effort})"
            )
    else:
        body_lines.append("- No decisions were generated.")

    payload = {
        "subject": subject,
        "to": ["semiconductor-review@enterprise.example"],
        "cc": [],
        "body_text": "\n".join(body_lines),
        "metadata": {
            "run_id": run.run_id,
            "project_id": run.project_id,
            "agent": run.agent,
            "mode": run.mode,
            "provider": run.provider,
            "model": run.model or "",
        },
    }
    return StructuredExportResponse(
        format="email",
        run_id=run.run_id,
        title=subject,
        filename=f"{run.run_id}-email.json",
        mime_type="application/json",
        payload=payload,
    )


def _workflow_label(run: RunHistoryRecord) -> str:
    mapping = {
        ("agent01", "coverage"): "coverage closure",
        ("agent01", "triage"): "regression triage",
        ("agent02", "ate"): "ATE review",
        ("agent02", "spc"): "SPC review",
    }
    return mapping.get((run.agent, run.mode), run.mode)


def _jira_risk_posture(run: RunHistoryRecord) -> str:
    if run.high >= 2:
        return "Multiple P1 findings require near-term engineering review."
    if run.high == 1:
        return "One P1 finding should be reviewed before routine follow-up work."
    if run.total_decisions:
        return "No P1 findings were produced, but the run surfaced actionable review items."
    return "No decisions were produced, so the current artifact needs deeper investigation."


def _slug(value: str) -> str:
    return "-".join(part for part in value.lower().replace("/", " ").split() if part)
