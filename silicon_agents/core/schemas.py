"""Pydantic models shared across Silicon Agents."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, Field


Priority = Literal["HIGH", "MEDIUM", "LOW"]
AgentType = Literal["verification", "yield"]
ParsedReportType = Literal["coverage", "regression", "ate", "spc", "unknown"]
FeedbackStatus = Literal["accepted", "rejected", "refined"]


class ParsedItem(BaseModel):
    id: str
    name: str
    status: str = "unknown"
    value: Optional[Union[float, int, str]] = None
    hits: Optional[int] = None
    misses: Optional[int] = None
    spec_min: Optional[float] = None
    spec_max: Optional[float] = None
    bin_assignment: Optional[Union[int, str]] = None
    context: dict[str, Any] = Field(default_factory=dict)


class ParsedSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    covered: int = 0
    uncovered: int = 0
    anomalies: int = 0
    coverage_pct: Optional[float] = None


class ParsedReport(BaseModel):
    type: ParsedReportType
    agent: Optional[AgentType] = None
    summary: ParsedSummary = Field(default_factory=ParsedSummary)
    items: list[ParsedItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    raw_excerpt: Optional[str] = None


class Decision(BaseModel):
    id: str
    project_id: str
    type: str
    target: str
    action: str
    rationale: str
    priority: Priority
    confidence: float
    effort: str
    status: str = "open"
    metadata: dict[str, Any] = Field(default_factory=dict)


class StepEvent(BaseModel):
    num: int
    label: str


class DoneEvent(BaseModel):
    total_decisions: int
    high: int = 0
    medium: int = 0
    low: int = 0
    provider: str = "mock"


class VerifyRequest(BaseModel):
    report_text: str
    format: Literal["auto", "vcs", "xcelium"] = "auto"
    mode: Literal["coverage", "triage"] = "coverage"
    design_name: str = "Unknown Design"
    project_id: str = "demo-verification"
    context: Optional[str] = None
    artifact_name: Optional[str] = None
    run_profile_id: Optional[str] = None
    run_profile_name: Optional[str] = None
    chip_type: Optional[str] = None
    client_profile: Optional[str] = None
    custom_instructions: Optional[str] = None
    reference_data: Optional[str] = None
    reference_data_label: Optional[str] = None


class YieldRequest(BaseModel):
    csv_data: str
    lot_id: str = "LOT-DEMO"
    mode: Literal["ate", "spc"] = "ate"
    project_id: str = "demo-yield"
    context: Optional[str] = None
    artifact_name: Optional[str] = None
    run_profile_id: Optional[str] = None
    run_profile_name: Optional[str] = None
    chip_type: Optional[str] = None
    client_profile: Optional[str] = None
    custom_instructions: Optional[str] = None
    reference_data: Optional[str] = None
    reference_data_label: Optional[str] = None


class FeedbackRequest(BaseModel):
    decision_id: str
    accepted: bool
    notes: str = ""
    project_id: str = "default-project"
    engineer_id: str = "local-user"
    run_id: Optional[str] = None


class FeedbackRecord(BaseModel):
    decision_id: str
    project_id: str
    accepted: bool
    notes: str
    engineer_id: str
    timestamp: datetime
    run_id: Optional[str] = None


class DecisionListResponse(BaseModel):
    project_id: str
    decisions: list[Decision]


class FeedbackListResponse(BaseModel):
    project_id: str
    feedback: list[FeedbackRecord]


class FeedbackSummary(BaseModel):
    total: int = 0
    accepted: int = 0
    rejected: int = 0
    latest_timestamp: Optional[datetime] = None


class ExportHistoryRecord(BaseModel):
    run_id: str
    target: Literal["jira", "email"]
    title: str
    filename: str
    created_at: datetime


class RunHistoryRecord(BaseModel):
    run_id: str
    project_id: str
    agent: Literal["agent01", "agent02"]
    mode: str
    status: Literal["completed", "failed"]
    provider: str = "mock"
    model: Optional[str] = None
    artifact_name: Optional[str] = None
    runtime_label: Optional[str] = None
    run_profile_id: Optional[str] = None
    run_profile_name: Optional[str] = None
    chip_type: Optional[str] = None
    client_profile: Optional[str] = None
    started_at: datetime
    completed_at: datetime
    duration_ms: int = 0
    total_decisions: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    request_payload: dict[str, Any] = Field(default_factory=dict)
    orchestration: dict[str, Any] = Field(default_factory=dict)
    analysis_log: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    observability: dict[str, Any] = Field(default_factory=dict)
    benchmark_title: Optional[str] = None
    benchmark_score: Optional[str] = None
    benchmark_notes: list[str] = Field(default_factory=list)
    scorecard_mode: str = "live"
    feedback_summary: FeedbackSummary = Field(default_factory=FeedbackSummary)
    feedback: list[FeedbackRecord] = Field(default_factory=list)
    export_history: list[ExportHistoryRecord] = Field(default_factory=list)
    error_message: Optional[str] = None


class RunHistorySummary(BaseModel):
    run_id: str
    project_id: str
    agent: Literal["agent01", "agent02"]
    mode: str
    status: Literal["completed", "failed"]
    provider: str = "mock"
    model: Optional[str] = None
    artifact_name: Optional[str] = None
    runtime_label: Optional[str] = None
    run_profile_id: Optional[str] = None
    run_profile_name: Optional[str] = None
    started_at: datetime
    duration_ms: int = 0
    total_decisions: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    benchmark_title: Optional[str] = None
    benchmark_score: Optional[str] = None
    feedback_summary: FeedbackSummary = Field(default_factory=FeedbackSummary)
    export_count: int = 0
    error_message: Optional[str] = None


class RunHistoryListResponse(BaseModel):
    runs: list[RunHistorySummary] = Field(default_factory=list)


class BenchmarkFindingMatch(BaseModel):
    expected: str
    observed_target: str
    priority: Priority
    evidence: str = ""


class BenchmarkMetrics(BaseModel):
    overall_score: int
    findings_recall: float
    high_priority_alignment: float
    first_action_alignment: float
    evidence_coverage: float
    matched_expected_findings: int
    expected_findings: int


class BenchmarkDefinitionResponse(BaseModel):
    id: str
    title: str
    workflow: str
    artifact_name: str
    manual_review_minutes: int
    expected_findings: int


class BenchmarkEvaluationRequest(BaseModel):
    benchmark_id: str
    decisions: list[Decision]


class BenchmarkEvaluationResponse(BaseModel):
    benchmark_id: str
    title: str
    workflow: str
    artifact_name: str
    manual_review_minutes: int
    assisted_review_minutes: int
    review_time_saved_minutes: int
    matched_findings: list[BenchmarkFindingMatch]
    missed_findings: list[str]
    metrics: BenchmarkMetrics
    notes: list[str]


class VerificationBriefRequest(BaseModel):
    project_id: str
    design_name: str
    mode: Literal["coverage", "triage"]
    context: Optional[str] = None
    provider: str = "mock/local"
    artifact_name: Optional[str] = None
    workflow_label: Optional[str] = None
    review_time_saved: Optional[str] = None
    benchmark_title: Optional[str] = None
    benchmark_score: Optional[str] = None
    benchmark_notes: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    analysis_log: list[str] = Field(default_factory=list)


class YieldBriefRequest(BaseModel):
    project_id: str
    lot_id: str
    mode: Literal["ate", "spc"]
    context: Optional[str] = None
    provider: str = "mock/local"
    artifact_name: Optional[str] = None
    workflow_label: Optional[str] = None
    review_time_saved: Optional[str] = None
    benchmark_title: Optional[str] = None
    benchmark_score: Optional[str] = None
    benchmark_notes: list[str] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    analysis_log: list[str] = Field(default_factory=list)


class StructuredExportResponse(BaseModel):
    format: Literal["jira", "email"]
    run_id: str
    title: str
    filename: str
    mime_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class Agent01EnterpriseConfig(BaseModel):
    org_name: str = "Fabless Semiconductor Division"
    review_board: str = "Verification Signoff Council"
    output_style: str = "Evidence-first engineering review"
    escalation_policy: str = "Escalate highest escape-risk items before routine optimization work."
    evidence_policy: str = "Every recommendation must cite precise report evidence."
    instruction_addendum: str = "Prefer standard organizational workflows and avoid unnecessary churn."


class Agent02EnterpriseConfig(BaseModel):
    org_name: str = "Product and Yield Engineering"
    review_board: str = "Yield Escalation Committee"
    output_style: str = "Revenue-aware lot review"
    escalation_policy: str = "Escalate highest escape-risk items before routine optimization work."
    risk_policy: str = "Prioritize revenue upside and containment before exploratory follow-up."
    instruction_addendum: str = "Prefer operationally actionable recommendations that fit existing review governance."


class EnterpriseConfigEnvelope(BaseModel):
    agent: Literal["agent01", "agent02"]
    config: Union[Agent01EnterpriseConfig, Agent02EnterpriseConfig]
