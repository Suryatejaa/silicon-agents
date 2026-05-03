"""Simple HTML report formatting."""

from __future__ import annotations

from html import escape

from silicon_agents.core.schemas import (
    Decision,
    ParsedReport,
    VerificationBriefRequest,
    YieldBriefRequest,
)


def render_html_report(parsed: ParsedReport, decisions: list[Decision]) -> str:
    rows = "".join(
        f"<tr><td>{d.priority}</td><td>{d.target}</td><td>{d.action}</td><td>{d.confidence:.0%}</td></tr>"
        for d in decisions
    )
    return f"""
    <html>
      <body>
        <h1>Silicon Agents Report</h1>
        <p>Total items: {parsed.summary.total}</p>
        <table border="1" cellspacing="0" cellpadding="8">
          <tr><th>Priority</th><th>Target</th><th>Action</th><th>Confidence</th></tr>
          {rows}
        </table>
      </body>
    </html>
    """


def render_verification_brief(request: VerificationBriefRequest) -> str:
    """Render a sponsor-friendly verification brief."""

    high_count = sum(1 for decision in request.decisions if decision.priority == "HIGH")
    medium_count = sum(1 for decision in request.decisions if decision.priority == "MEDIUM")
    top_decision = request.decisions[0] if request.decisions else None

    benchmark_score_value = _extract_score(request.benchmark_score)
    if request.review_time_saved and "not" not in request.review_time_saved.lower():
        business_impact = f"This run suggests {request.review_time_saved} can be removed from first-pass verification review."
    else:
        business_impact = "This run demonstrates a ranked review queue that can shorten manual time spent scanning raw verification outputs."

    if high_count >= 2:
        risk_posture = "High schedule attention recommended. Multiple P1 findings suggest meaningful closure or bug-escape risk if this area is left unreviewed."
    elif high_count == 1:
        risk_posture = "Moderate schedule attention recommended. One top-priority finding should be reviewed before lower-value closure work."
    elif request.decisions:
        risk_posture = "Contained workflow risk. The run produced reviewable findings, but none indicate an immediate high-severity escape path."
    else:
        risk_posture = "No material findings were produced in this run, so workflow risk could not be assessed from the current artifact."

    if benchmark_score_value is not None and benchmark_score_value >= 85:
        pilot_next_step = "Use this workflow with a small batch of sanitized partner artifacts and measure manual versus assisted time-to-first-action."
    elif benchmark_score_value is not None:
        pilot_next_step = "Keep the workflow in benchmark mode, tighten prompt and parser quality, and review the misses with a domain expert before external pilot use."
    else:
        pilot_next_step = "Run the workflow against the bundled benchmarks first, then progress to sanitized client artifacts once the scorecard results are stable."

    executive_call = (
        f"Lead the next review with {top_decision.target}: {top_decision.action}"
        if top_decision
        else "No top recommendation is available yet. Re-run the analysis with a richer artifact or benchmark sample."
    )

    decisions_html = "".join(
        f"""
        <section class="decision">
          <div class="priority priority-{escape(decision.priority.lower())}">{escape(decision.priority)}</div>
          <h3>{escape(decision.target)}</h3>
          <p class="action">{escape(decision.action)}</p>
          <p class="rationale">{escape(decision.rationale)}</p>
          <p class="meta"><strong>Confidence:</strong> {round(decision.confidence * 100)}% · <strong>Effort:</strong> {escape(decision.effort)}</p>
          <p class="meta"><strong>Evidence:</strong> {escape(str(decision.metadata.get("evidence", "Not provided")))}</p>
          <p class="meta"><strong>Why ranked here:</strong> {escape(str(decision.metadata.get("rank_basis", "Not provided")))}</p>
        </section>
        """
        for decision in request.decisions
    )

    analysis_html = "".join(
        f"<li>{escape(entry)}</li>"
        for entry in request.analysis_log
    )

    benchmark_block = ""
    if request.benchmark_title or request.benchmark_score or request.benchmark_notes:
        notes = "".join(f"<li>{escape(note)}</li>" for note in request.benchmark_notes)
        benchmark_block = f"""
        <section class="card">
          <div class="eyebrow">Benchmark readout</div>
          <h2>{escape(request.benchmark_title or "No benchmark attached")}</h2>
          <p class="lead">Score: {escape(request.benchmark_score or "Not scored")}</p>
          <ul>{notes}</ul>
        </section>
        """

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Silicon Agents Verification Brief</title>
        <style>
          body {{
            margin: 0;
            padding: 32px;
            background: #f7f4ec;
            color: #1b1a16;
            font-family: Georgia, "Iowan Old Style", serif;
          }}
          .page {{
            max-width: 980px;
            margin: 0 auto;
          }}
          .hero, .card, .decision {{
            background: #fffdf9;
            border: 1px solid #ddd4c1;
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 16px;
          }}
          .eyebrow {{
            color: #0f6d69;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 8px;
          }}
          h1 {{
            margin: 0 0 10px;
            font-size: 2.4rem;
            line-height: 1;
          }}
          h2 {{
            margin: 0 0 10px;
            font-size: 1.2rem;
          }}
          h3 {{
            margin: 0 0 8px;
            font-size: 1.1rem;
          }}
          .grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 18px;
          }}
          .grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-top: 16px;
          }}
          .metric {{
            border: 1px solid #e6decd;
            border-radius: 14px;
            padding: 14px;
            background: #faf8f2;
          }}
          .metric .label {{
            color: #655f54;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 11px;
            margin-bottom: 6px;
          }}
          .metric .value {{
            font-size: 1.05rem;
            font-weight: 700;
          }}
          .lead, p, li {{
            color: #655f54;
            line-height: 1.6;
          }}
          .priority {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 10px;
          }}
          .priority-high {{ background: rgba(180, 83, 9, 0.15); color: #b45309; }}
          .priority-medium {{ background: rgba(202, 138, 4, 0.15); color: #a16207; }}
          .priority-low {{ background: rgba(17, 97, 73, 0.15); color: #116149; }}
          .action {{
            color: #1b1a16;
            font-weight: 700;
          }}
          .meta strong {{
            color: #1b1a16;
          }}
          .executive {{
            background: linear-gradient(180deg, #fffdfa, #f8f3ea);
          }}
          .executive-copy {{
            color: #1b1a16;
            font-size: 1.05rem;
            line-height: 1.65;
          }}
          .summary-card {{
            border: 1px solid #e6decd;
            border-radius: 14px;
            padding: 14px;
            background: #faf8f2;
          }}
          .summary-card h3 {{
            margin: 0 0 8px;
            font-size: 1rem;
          }}
          ul {{
            margin: 10px 0 0;
            padding-left: 18px;
          }}
          @media (max-width: 860px) {{
            .grid, .grid-4 {{
              grid-template-columns: 1fr;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="page">
          <section class="hero">
            <div class="eyebrow">Silicon Agents · Verification brief</div>
            <h1>{escape(request.design_name)}</h1>
            <p class="lead">A sponsor-ready analysis brief for verification workflow review. This document summarizes the ranked findings, evidence, benchmark posture, and reasoning trace from a single Agent 01 run.</p>
            <div class="grid">
              <div class="metric">
                <div class="label">Project</div>
                <div class="value">{escape(request.project_id)}</div>
              </div>
              <div class="metric">
                <div class="label">Workflow</div>
                <div class="value">{escape(request.workflow_label or request.mode.title())}</div>
              </div>
              <div class="metric">
                <div class="label">Model source</div>
                <div class="value">{escape(request.provider)}</div>
              </div>
              <div class="metric">
                <div class="label">Artifact</div>
                <div class="value">{escape(request.artifact_name or "Verification artifact")}</div>
              </div>
              <div class="metric">
                <div class="label">Review time saved</div>
                <div class="value">{escape(request.review_time_saved or "Not estimated")}</div>
              </div>
              <div class="metric">
                <div class="label">Decisions</div>
                <div class="value">{len(request.decisions)}</div>
              </div>
            </div>
            <p><strong>Context:</strong> {escape(request.context or "Not provided")}</p>
          </section>
          <section class="card executive">
            <div class="eyebrow">Executive summary</div>
            <p class="executive-copy">{escape(executive_call)}</p>
            <div class="grid-4">
              <div class="metric">
                <div class="label">P1 findings</div>
                <div class="value">{high_count}</div>
              </div>
              <div class="metric">
                <div class="label">P2 findings</div>
                <div class="value">{medium_count}</div>
              </div>
              <div class="metric">
                <div class="label">Benchmark score</div>
                <div class="value">{escape(request.benchmark_score or "Not scored")}</div>
              </div>
              <div class="metric">
                <div class="label">Primary action owner</div>
                <div class="value">{escape(request.workflow_label or request.mode.title())}</div>
              </div>
            </div>
            <div class="grid" style="margin-top: 16px;">
              <div class="summary-card">
                <div class="eyebrow">Business impact</div>
                <p>{escape(business_impact)}</p>
              </div>
              <div class="summary-card">
                <div class="eyebrow">Risk posture</div>
                <p>{escape(risk_posture)}</p>
              </div>
              <div class="summary-card">
                <div class="eyebrow">Recommended next pilot step</div>
                <p>{escape(pilot_next_step)}</p>
              </div>
            </div>
          </section>
          {benchmark_block}
          <section class="card">
            <div class="eyebrow">Ranked findings</div>
            {decisions_html or "<p>No decisions were generated for this run.</p>"}
          </section>
          <section class="card">
            <div class="eyebrow">Analysis trace</div>
            <ul>{analysis_html or "<li>No analysis trace captured.</li>"}</ul>
          </section>
        </div>
      </body>
    </html>
    """


def render_yield_brief(request: YieldBriefRequest) -> str:
    """Render a sponsor-friendly yield or SPC brief."""

    high_count = sum(1 for decision in request.decisions if decision.priority == "HIGH")
    medium_count = sum(1 for decision in request.decisions if decision.priority == "MEDIUM")
    top_decision = request.decisions[0] if request.decisions else None

    benchmark_score_value = _extract_score(request.benchmark_score)
    if request.review_time_saved and "not" not in request.review_time_saved.lower():
        business_impact = f"This run suggests {request.review_time_saved} can be removed from first-pass yield review and escalation triage."
    else:
        business_impact = "This run demonstrates a ranked engineering queue that can reduce manual time spent scanning raw ATE or SPC outputs."

    if high_count >= 2:
        risk_posture = "High operational attention recommended. Multiple P1 findings suggest meaningful revenue, binning, or process-control risk if left unreviewed."
    elif high_count == 1:
        risk_posture = "Moderate operational attention recommended. One top-priority yield or SPC escalation should be reviewed before lower-value follow-up."
    elif request.decisions:
        risk_posture = "Contained workflow risk. The run produced reviewable findings, but none suggest an immediate top-severity lot or process excursion."
    else:
        risk_posture = "No material findings were produced in this run, so yield risk could not be assessed from the current artifact."

    if benchmark_score_value is not None and benchmark_score_value >= 85:
        pilot_next_step = "Use this workflow with sanitized lot review data and compare manual versus assisted escalation time on a small pilot set."
    elif benchmark_score_value is not None:
        pilot_next_step = "Keep the workflow in benchmark mode, tighten prompt and parser quality, and review the misses with a yield or product engineering lead before pilot use."
    else:
        pilot_next_step = "Run the workflow against the bundled Agent 02 benchmarks first, then progress to sanitized client ATE or SPC artifacts once scorecard results are stable."

    executive_call = (
        f"Lead the next yield review with {top_decision.target}: {top_decision.action}"
        if top_decision
        else "No top recommendation is available yet. Re-run the analysis with a richer artifact or benchmark sample."
    )

    decisions_html = "".join(
        f"""
        <section class="decision">
          <div class="priority priority-{escape(decision.priority.lower())}">{escape(decision.priority)}</div>
          <h3>{escape(decision.target)}</h3>
          <p class="action">{escape(decision.action)}</p>
          <p class="rationale">{escape(decision.rationale)}</p>
          <p class="meta"><strong>Confidence:</strong> {round(decision.confidence * 100)}% · <strong>Effort:</strong> {escape(decision.effort)}</p>
          <p class="meta"><strong>Evidence:</strong> {escape(str(decision.metadata.get("evidence", decision.rationale or "Not provided")))}</p>
          <p class="meta"><strong>Why ranked here:</strong> {escape(str(decision.metadata.get("rank_basis", "Not provided")))}</p>
        </section>
        """
        for decision in request.decisions
    )

    analysis_html = "".join(f"<li>{escape(entry)}</li>" for entry in request.analysis_log)

    benchmark_block = ""
    if request.benchmark_title or request.benchmark_score or request.benchmark_notes:
        notes = "".join(f"<li>{escape(note)}</li>" for note in request.benchmark_notes)
        benchmark_block = f"""
        <section class="card">
          <div class="eyebrow">Benchmark readout</div>
          <h2>{escape(request.benchmark_title or "No benchmark attached")}</h2>
          <p class="lead">Score: {escape(request.benchmark_score or "Not scored")}</p>
          <ul>{notes}</ul>
        </section>
        """

    workflow_label = request.workflow_label or ("ATE anomaly review" if request.mode == "ate" else "SPC drift review")
    artifact_label = request.artifact_name or ("Yield artifact" if request.mode == "ate" else "SPC artifact")

    return f"""
    <html>
      <head>
        <meta charset="utf-8" />
        <title>Silicon Agents Yield Brief</title>
        <style>
          body {{
            margin: 0;
            padding: 32px;
            background: #f3f5fa;
            color: #172b4d;
            font-family: "Segoe UI Variable Text", "Segoe UI", "Helvetica Neue", Arial, sans-serif;
          }}
          .page {{
            max-width: 980px;
            margin: 0 auto;
          }}
          .hero, .card, .decision {{
            background: #ffffff;
            border: 1px solid #dfe1e6;
            border-radius: 18px;
            padding: 22px;
            margin-bottom: 16px;
            box-shadow: 0 10px 28px rgba(9, 30, 66, 0.06);
          }}
          .eyebrow {{
            color: #0c66e4;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-size: 11px;
            font-weight: 700;
            margin-bottom: 8px;
          }}
          h1 {{
            margin: 0 0 10px;
            font-size: 2.4rem;
            line-height: 1;
          }}
          h2 {{
            margin: 0 0 10px;
            font-size: 1.2rem;
          }}
          h3 {{
            margin: 0 0 8px;
            font-size: 1.1rem;
          }}
          .grid {{
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 12px;
            margin-top: 18px;
          }}
          .grid-4 {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
            margin-top: 16px;
          }}
          .metric {{
            border: 1px solid #dfe1e6;
            border-radius: 14px;
            padding: 14px;
            background: #f8fafc;
          }}
          .metric .label {{
            color: #5e6c84;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-size: 11px;
            margin-bottom: 6px;
          }}
          .metric .value {{
            font-size: 1.05rem;
            font-weight: 700;
          }}
          .lead, p, li {{
            color: #42526e;
            line-height: 1.6;
          }}
          .priority {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 700;
            margin-bottom: 10px;
          }}
          .priority-high {{ background: #fdecea; color: #ae2a19; }}
          .priority-medium {{ background: #fff3db; color: #9f6b00; }}
          .priority-low {{ background: #dcfff1; color: #216e4e; }}
          .action {{
            color: #172b4d;
            font-weight: 700;
          }}
          .meta strong {{
            color: #172b4d;
          }}
          .executive {{
            background: linear-gradient(180deg, #ffffff, #f7f9fc);
          }}
          .executive-copy {{
            color: #172b4d;
            font-size: 1.05rem;
            line-height: 1.65;
          }}
          .summary-card {{
            border: 1px solid #dfe1e6;
            border-radius: 14px;
            padding: 14px;
            background: #f8fafc;
          }}
          .summary-card h3 {{
            margin: 0 0 8px;
            font-size: 1rem;
          }}
          ul {{
            margin: 10px 0 0;
            padding-left: 18px;
          }}
          @media (max-width: 860px) {{
            .grid, .grid-4 {{
              grid-template-columns: 1fr;
            }}
          }}
        </style>
      </head>
      <body>
        <div class="page">
          <section class="hero">
            <div class="eyebrow">Silicon Agents · Yield brief</div>
            <h1>{escape(request.lot_id)}</h1>
            <p class="lead">A sponsor-ready analysis brief for yield and process review. This document summarizes the ranked findings, benchmark posture, and reasoning trace from a single Agent 02 run.</p>
            <div class="grid">
              <div class="metric">
                <div class="label">Project</div>
                <div class="value">{escape(request.project_id)}</div>
              </div>
              <div class="metric">
                <div class="label">Workflow</div>
                <div class="value">{escape(workflow_label)}</div>
              </div>
              <div class="metric">
                <div class="label">Model source</div>
                <div class="value">{escape(request.provider)}</div>
              </div>
              <div class="metric">
                <div class="label">Artifact</div>
                <div class="value">{escape(artifact_label)}</div>
              </div>
              <div class="metric">
                <div class="label">Review time saved</div>
                <div class="value">{escape(request.review_time_saved or "Not estimated")}</div>
              </div>
              <div class="metric">
                <div class="label">Decisions</div>
                <div class="value">{len(request.decisions)}</div>
              </div>
            </div>
            <p><strong>Context:</strong> {escape(request.context or "Not provided")}</p>
          </section>
          <section class="card executive">
            <div class="eyebrow">Executive summary</div>
            <p class="executive-copy">{escape(executive_call)}</p>
            <div class="grid-4">
              <div class="metric">
                <div class="label">P1 findings</div>
                <div class="value">{high_count}</div>
              </div>
              <div class="metric">
                <div class="label">P2 findings</div>
                <div class="value">{medium_count}</div>
              </div>
              <div class="metric">
                <div class="label">Benchmark score</div>
                <div class="value">{escape(request.benchmark_score or "Not scored")}</div>
              </div>
              <div class="metric">
                <div class="label">Primary action owner</div>
                <div class="value">{escape(workflow_label)}</div>
              </div>
            </div>
            <div class="grid" style="margin-top: 16px;">
              <div class="summary-card">
                <div class="eyebrow">Business impact</div>
                <p>{escape(business_impact)}</p>
              </div>
              <div class="summary-card">
                <div class="eyebrow">Risk posture</div>
                <p>{escape(risk_posture)}</p>
              </div>
              <div class="summary-card">
                <div class="eyebrow">Recommended next pilot step</div>
                <p>{escape(pilot_next_step)}</p>
              </div>
            </div>
          </section>
          {benchmark_block}
          <section class="card">
            <div class="eyebrow">Ranked findings</div>
            {decisions_html or "<p>No decisions were generated for this run.</p>"}
          </section>
          <section class="card">
            <div class="eyebrow">Analysis trace</div>
            <ul>{analysis_html or "<li>No analysis trace captured.</li>"}</ul>
          </section>
        </div>
      </body>
    </html>
    """


def _extract_score(score_text: str | None) -> int | None:
    """Parse a benchmark score string like '92/100'."""

    if not score_text:
        return None
    try:
        return int(str(score_text).split("/", 1)[0])
    except (TypeError, ValueError):
        return None
