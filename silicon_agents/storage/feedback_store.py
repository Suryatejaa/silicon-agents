"""SQLite storage for decisions, feedback, enterprise configuration, and run history."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from silicon_agents.core.schemas import (
    Agent01EnterpriseConfig,
    Agent02EnterpriseConfig,
    Decision,
    ExportHistoryRecord,
    FeedbackRecord,
    FeedbackSummary,
    PilotBreakdownItem,
    PilotMetricsResponse,
    PilotParserWarningItem,
    RunHistoryRecord,
    RunHistorySummary,
)

try:
    import aiosqlite  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for fresh local envs
    aiosqlite = None

try:
    import psycopg  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - postgres support is optional in local dev
    psycopg = None


class FeedbackStore:
    def __init__(self, db_path: str) -> None:
        normalized = str(db_path or "").strip() or "./silicon_agents.db"
        if normalized.startswith("postgres://"):
            normalized = "postgresql://" + normalized[len("postgres://"):]
        self.db_path = normalized
        self.backend = "postgres" if self.db_path.startswith(("postgresql://", "postgres://")) else "sqlite"
        self._use_async_sqlite = self.backend == "sqlite" and aiosqlite is not None

    @property
    def is_postgres(self) -> bool:
        return self.backend == "postgres"

    async def init(self) -> None:
        if not self._use_async_sqlite:
            self._init_sync()
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    action TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    effort TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    decision_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    run_id TEXT NOT NULL DEFAULT '',
                    accepted INTEGER NOT NULL,
                    notes TEXT NOT NULL,
                    engineer_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS enterprise_config (
                    agent TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS run_history (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    artifact_name TEXT NOT NULL,
                    artifact_source TEXT NOT NULL DEFAULT 'unknown',
                    raw_artifact TEXT NOT NULL DEFAULT '',
                    runtime_label TEXT NOT NULL,
                    run_profile_id TEXT NOT NULL,
                    run_profile_name TEXT NOT NULL,
                    chip_type TEXT NOT NULL,
                    client_profile TEXT NOT NULL,
                    parser_format TEXT NOT NULL DEFAULT '',
                    parser_confidence REAL NOT NULL DEFAULT 0,
                    parser_warnings TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    total_decisions INTEGER NOT NULL,
                    high INTEGER NOT NULL,
                    medium INTEGER NOT NULL,
                    low INTEGER NOT NULL,
                    request_payload TEXT NOT NULL,
                    orchestration TEXT NOT NULL,
                    analysis_log TEXT NOT NULL,
                    decisions TEXT NOT NULL,
                    observability TEXT NOT NULL,
                    benchmark_title TEXT NOT NULL DEFAULT '',
                    benchmark_score TEXT NOT NULL DEFAULT '',
                    benchmark_notes TEXT NOT NULL DEFAULT '[]',
                    scorecard_mode TEXT NOT NULL DEFAULT 'live',
                    error_message TEXT NOT NULL
                )
                """
            )
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS export_history (
                    run_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_async_column(db, "feedback", "run_id", "TEXT NOT NULL DEFAULT ''")
            await self._ensure_async_column(db, "run_history", "benchmark_title", "TEXT NOT NULL DEFAULT ''")
            await self._ensure_async_column(db, "run_history", "benchmark_score", "TEXT NOT NULL DEFAULT ''")
            await self._ensure_async_column(db, "run_history", "benchmark_notes", "TEXT NOT NULL DEFAULT '[]'")
            await self._ensure_async_column(db, "run_history", "scorecard_mode", "TEXT NOT NULL DEFAULT 'live'")
            await self._ensure_async_column(db, "run_history", "raw_artifact", "TEXT NOT NULL DEFAULT ''")
            await self._ensure_async_column(db, "run_history", "artifact_source", "TEXT NOT NULL DEFAULT 'unknown'")
            await self._ensure_async_column(db, "run_history", "parser_format", "TEXT NOT NULL DEFAULT ''")
            await self._ensure_async_column(db, "run_history", "parser_confidence", "REAL NOT NULL DEFAULT 0")
            await self._ensure_async_column(db, "run_history", "parser_warnings", "TEXT NOT NULL DEFAULT '[]'")
            await db.commit()

    async def save_decisions(self, decisions: list[Decision]) -> None:
        if not decisions:
            return
        if not self._use_async_sqlite:
            self._save_decisions_sync(decisions)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.executemany(
                """
                INSERT OR REPLACE INTO decisions
                (id, project_id, type, target, action, rationale, priority, confidence, effort, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        decision.id,
                        decision.project_id,
                        decision.type,
                        decision.target,
                        decision.action,
                        decision.rationale,
                        decision.priority,
                        decision.confidence,
                        decision.effort,
                        decision.status,
                        json.dumps(decision.metadata),
                    )
                    for decision in decisions
                ],
            )
            await db.commit()

    async def record_feedback(
        self,
        decision_id: str,
        project_id: str,
        accepted: bool,
        notes: str,
        engineer_id: str,
        run_id: str = "",
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        if not self._use_async_sqlite:
            self._record_feedback_sync(decision_id, project_id, accepted, notes, engineer_id, timestamp, run_id)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO feedback (decision_id, project_id, run_id, accepted, notes, engineer_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (decision_id, project_id, run_id, int(accepted), notes, engineer_id, timestamp),
            )
            await db.execute(
                "UPDATE decisions SET status = ? WHERE id = ?",
                ("accepted" if accepted else "rejected", decision_id),
            )
            await db.commit()

    async def get_feedback(self, project_id: str, run_id: str | None = None) -> list[FeedbackRecord]:
        if not self._use_async_sqlite:
            rows = self._get_feedback_sync(project_id, run_id)
            return [
                FeedbackRecord(
                    decision_id=row[0],
                    project_id=row[1],
                    run_id=row[2] or None,
                    accepted=bool(row[3]),
                    notes=row[4],
                    engineer_id=row[5],
                    timestamp=datetime.fromisoformat(row[6]),
                )
                for row in rows
            ]
        async with aiosqlite.connect(self.db_path) as db:
            query = """
                SELECT decision_id, project_id, run_id, accepted, notes, engineer_id, timestamp
                FROM feedback
                WHERE project_id = ?
            """
            params: list[object] = [project_id]
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            query += " ORDER BY timestamp DESC"
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
        return [
            FeedbackRecord(
                decision_id=row[0],
                project_id=row[1],
                run_id=row[2] or None,
                accepted=bool(row[3]),
                notes=row[4],
                engineer_id=row[5],
                timestamp=datetime.fromisoformat(row[6]),
            )
            for row in rows
        ]

    async def get_decisions(self, project_id: str) -> list[Decision]:
        if not self._use_async_sqlite:
            rows = self._get_decisions_sync(project_id)
            return [
                Decision(
                    id=row[0],
                    project_id=row[1],
                    type=row[2],
                    target=row[3],
                    action=row[4],
                    rationale=row[5],
                    priority=row[6],
                    confidence=row[7],
                    effort=row[8],
                    status=row[9],
                    metadata=json.loads(row[10]),
                )
                for row in rows
            ]
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT id, project_id, type, target, action, rationale, priority, confidence, effort, status, metadata
                FROM decisions
                WHERE project_id = ?
                ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, confidence DESC
                """,
                (project_id,),
            )
            rows = await cursor.fetchall()
        return [
            Decision(
                id=row[0],
                project_id=row[1],
                type=row[2],
                target=row[3],
                action=row[4],
                rationale=row[5],
                priority=row[6],
                confidence=row[7],
                effort=row[8],
                status=row[9],
                metadata=json.loads(row[10]),
            )
            for row in rows
        ]

    async def save_enterprise_config(self, agent: str, payload: dict[str, object]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        if not self._use_async_sqlite:
            self._save_enterprise_config_sync(agent, payload, timestamp)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO enterprise_config (agent, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (agent, json.dumps(payload), timestamp),
            )
            await db.commit()

    async def get_enterprise_config(self, agent: str) -> dict[str, object]:
        if not self._use_async_sqlite:
            payload = self._get_enterprise_config_sync(agent)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT payload FROM enterprise_config
                    WHERE agent = ?
                    """,
                    (agent,),
                )
                row = await cursor.fetchone()
            payload = json.loads(row[0]) if row else None
        if payload:
            return payload
        return self._default_enterprise_config(agent)

    async def save_run_history(self, record: RunHistoryRecord) -> None:
        if not self._use_async_sqlite:
            self._save_run_history_sync(record)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO run_history (
                    run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, raw_artifact, runtime_label,
                    run_profile_id, run_profile_name, chip_type, client_profile, parser_format, parser_confidence, parser_warnings, started_at, completed_at,
                    duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                    analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                    scorecard_mode, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._run_history_params(record),
            )
            await db.commit()

    async def get_run_history(
        self,
        project_id: str | None = None,
        agent: str | None = None,
        limit: int = 50,
    ) -> list[RunHistorySummary]:
        if not self._use_async_sqlite:
            rows = self._get_run_history_sync(project_id, agent, limit)
        else:
            query = (
                "SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, runtime_label, "
                "run_profile_id, run_profile_name, parser_format, parser_confidence, started_at, duration_ms, total_decisions, high, medium, low, benchmark_title, benchmark_score, error_message "
                "FROM run_history"
            )
            clauses = []
            params: list[object] = []
            if project_id:
                clauses.append("project_id = ?")
                params.append(project_id)
            if agent:
                clauses.append("agent = ?")
                params.append(agent)
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY started_at DESC LIMIT ?"
            params.append(limit)
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(query, tuple(params))
                rows = await cursor.fetchall()
        summaries: list[RunHistorySummary] = []
        for row in rows:
            summary = self._run_history_summary_from_row(row)
            feedback = await self.get_feedback(summary.project_id, summary.run_id)
            summary.feedback_summary = self._feedback_summary(feedback)
            summary.export_count = len(await self.get_export_history(summary.run_id))
            summaries.append(summary)
        return summaries

    async def get_run(self, run_id: str) -> RunHistoryRecord | None:
        if not self._use_async_sqlite:
            row = self._get_run_sync(run_id)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, raw_artifact, runtime_label,
                           run_profile_id, run_profile_name, chip_type, client_profile, parser_format, parser_confidence, parser_warnings, started_at, completed_at,
                           duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                           analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                           scorecard_mode, error_message
                    FROM run_history
                    WHERE run_id = ?
                    """,
                    (run_id,),
                )
                row = await cursor.fetchone()
        if not row:
            return None
        record = self._run_history_record_from_row(row)
        record.feedback = await self.get_feedback(record.project_id, run_id)
        record.feedback_summary = self._feedback_summary(record.feedback)
        record.export_history = await self.get_export_history(run_id)
        return record

    async def record_export(self, run_id: str, target: str, title: str, filename: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        if not self._use_async_sqlite:
            self._record_export_sync(run_id, target, title, filename, timestamp)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO export_history (run_id, target, title, filename, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, target, title, filename, timestamp),
            )
            await db.commit()

    async def get_export_history(self, run_id: str) -> list[ExportHistoryRecord]:
        if not self._use_async_sqlite:
            rows = self._get_export_history_sync(run_id)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT run_id, target, title, filename, created_at
                    FROM export_history
                    WHERE run_id = ?
                    ORDER BY created_at DESC
                    """,
                    (run_id,),
                )
                rows = await cursor.fetchall()
        return [
            ExportHistoryRecord(
                run_id=row[0],
                target=row[1],
                title=row[2],
                filename=row[3],
                created_at=datetime.fromisoformat(row[4]),
            )
            for row in rows
        ]

    async def get_pilot_metrics(self, access_enabled: bool = False, recent_limit: int = 6) -> PilotMetricsResponse:
        if not self._use_async_sqlite:
            return self._get_pilot_metrics_sync(access_enabled=access_enabled, recent_limit=recent_limit)

        async with aiosqlite.connect(self.db_path) as db:
            run_cursor = await db.execute(
                """
                SELECT run_id, project_id, agent, status, provider, artifact_source, run_profile_name,
                       parser_confidence, parser_warnings, duration_ms, total_decisions, benchmark_score, scorecard_mode
                FROM run_history
                ORDER BY started_at DESC
                """
            )
            run_rows = await run_cursor.fetchall()
            feedback_cursor = await db.execute("SELECT accepted FROM feedback")
            feedback_rows = await feedback_cursor.fetchall()
            export_cursor = await db.execute("SELECT COUNT(*) FROM export_history")
            export_count_row = await export_cursor.fetchone()

        recent_runs = await self.get_run_history(limit=max(1, min(recent_limit, 12)))
        return self._build_pilot_metrics(
            run_rows=run_rows,
            feedback_rows=feedback_rows,
            export_count=int(export_count_row[0] or 0) if export_count_row else 0,
            recent_runs=recent_runs,
            access_enabled=access_enabled,
        )

    def _connect_sync(self) -> sqlite3.Connection:
        if self.is_postgres:
            if psycopg is None:
                raise RuntimeError("PostgreSQL support requires the optional 'psycopg' package.")
            return psycopg.connect(self.db_path)
        return sqlite3.connect(self.db_path)

    def _db_execute(self, db, query: str, params: tuple[object, ...] | list[object] | None = None):
        sql = query if not self.is_postgres else query.replace("?", "%s")
        if params is None:
            return db.execute(sql)
        return db.execute(sql, tuple(params))

    def _db_executemany(self, db, query: str, params_seq):
        sql = query if not self.is_postgres else query.replace("?", "%s")
        if self.is_postgres:
            with db.cursor() as cursor:
                cursor.executemany(sql, params_seq)
                return cursor
        return db.executemany(sql, params_seq)

    def _init_sync(self) -> None:
        with self._connect_sync() as db:
            self._db_execute(
                db,
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target TEXT NOT NULL,
                    action TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    effort TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata TEXT NOT NULL
                )
                """
            )
            self._db_execute(
                db,
                """
                CREATE TABLE IF NOT EXISTS feedback (
                    decision_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    run_id TEXT NOT NULL DEFAULT '',
                    accepted INTEGER NOT NULL,
                    notes TEXT NOT NULL,
                    engineer_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            self._db_execute(
                db,
                """
                CREATE TABLE IF NOT EXISTS enterprise_config (
                    agent TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._db_execute(
                db,
                """
                CREATE TABLE IF NOT EXISTS run_history (
                    run_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    artifact_name TEXT NOT NULL,
                    artifact_source TEXT NOT NULL DEFAULT 'unknown',
                    raw_artifact TEXT NOT NULL DEFAULT '',
                    runtime_label TEXT NOT NULL,
                    run_profile_id TEXT NOT NULL,
                    run_profile_name TEXT NOT NULL,
                    chip_type TEXT NOT NULL,
                    client_profile TEXT NOT NULL,
                    parser_format TEXT NOT NULL DEFAULT '',
                    parser_confidence REAL NOT NULL DEFAULT 0,
                    parser_warnings TEXT NOT NULL DEFAULT '[]',
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    total_decisions INTEGER NOT NULL,
                    high INTEGER NOT NULL,
                    medium INTEGER NOT NULL,
                    low INTEGER NOT NULL,
                    request_payload TEXT NOT NULL,
                    orchestration TEXT NOT NULL,
                    analysis_log TEXT NOT NULL,
                    decisions TEXT NOT NULL,
                    observability TEXT NOT NULL,
                    benchmark_title TEXT NOT NULL DEFAULT '',
                    benchmark_score TEXT NOT NULL DEFAULT '',
                    benchmark_notes TEXT NOT NULL DEFAULT '[]',
                    scorecard_mode TEXT NOT NULL DEFAULT 'live',
                    error_message TEXT NOT NULL
                )
                """
            )
            self._db_execute(
                db,
                """
                CREATE TABLE IF NOT EXISTS export_history (
                    run_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            self._ensure_sync_column(db, "feedback", "run_id", "TEXT NOT NULL DEFAULT ''")
            self._ensure_sync_column(db, "run_history", "benchmark_title", "TEXT NOT NULL DEFAULT ''")
            self._ensure_sync_column(db, "run_history", "benchmark_score", "TEXT NOT NULL DEFAULT ''")
            self._ensure_sync_column(db, "run_history", "benchmark_notes", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_sync_column(db, "run_history", "scorecard_mode", "TEXT NOT NULL DEFAULT 'live'")
            self._ensure_sync_column(db, "run_history", "raw_artifact", "TEXT NOT NULL DEFAULT ''")
            self._ensure_sync_column(db, "run_history", "artifact_source", "TEXT NOT NULL DEFAULT 'unknown'")
            self._ensure_sync_column(db, "run_history", "parser_format", "TEXT NOT NULL DEFAULT ''")
            self._ensure_sync_column(db, "run_history", "parser_confidence", "REAL NOT NULL DEFAULT 0")
            self._ensure_sync_column(db, "run_history", "parser_warnings", "TEXT NOT NULL DEFAULT '[]'")
            db.commit()

    def _save_decisions_sync(self, decisions: list[Decision]) -> None:
        with self._connect_sync() as db:
            params = [
                (
                    decision.id,
                    decision.project_id,
                    decision.type,
                    decision.target,
                    decision.action,
                    decision.rationale,
                    decision.priority,
                    decision.confidence,
                    decision.effort,
                    decision.status,
                    json.dumps(decision.metadata),
                )
                for decision in decisions
            ]
            if self.is_postgres:
                self._db_executemany(
                    db,
                    """
                    INSERT INTO decisions
                    (id, project_id, type, target, action, rationale, priority, confidence, effort, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO UPDATE SET
                        project_id = EXCLUDED.project_id,
                        type = EXCLUDED.type,
                        target = EXCLUDED.target,
                        action = EXCLUDED.action,
                        rationale = EXCLUDED.rationale,
                        priority = EXCLUDED.priority,
                        confidence = EXCLUDED.confidence,
                        effort = EXCLUDED.effort,
                        status = EXCLUDED.status,
                        metadata = EXCLUDED.metadata
                    """,
                    params,
                )
            else:
                self._db_executemany(
                    db,
                    """
                    INSERT OR REPLACE INTO decisions
                    (id, project_id, type, target, action, rationale, priority, confidence, effort, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )
            db.commit()

    def _record_feedback_sync(
        self,
        decision_id: str,
        project_id: str,
        accepted: bool,
        notes: str,
        engineer_id: str,
        timestamp: str,
        run_id: str,
    ) -> None:
        with self._connect_sync() as db:
            self._db_execute(
                db,
                """
                INSERT INTO feedback (decision_id, project_id, run_id, accepted, notes, engineer_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (decision_id, project_id, run_id, int(accepted), notes, engineer_id, timestamp),
            )
            self._db_execute(
                db,
                "UPDATE decisions SET status = ? WHERE id = ?",
                ("accepted" if accepted else "rejected", decision_id),
            )
            db.commit()

    def _get_feedback_sync(self, project_id: str, run_id: str | None):
        with self._connect_sync() as db:
            query = """
                SELECT decision_id, project_id, run_id, accepted, notes, engineer_id, timestamp
                FROM feedback
                WHERE project_id = ?
            """
            params: list[object] = [project_id]
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            query += " ORDER BY timestamp DESC"
            cursor = self._db_execute(db, query, tuple(params))
            return cursor.fetchall()

    def _get_decisions_sync(self, project_id: str):
        with self._connect_sync() as db:
            cursor = self._db_execute(
                db,
                """
                SELECT id, project_id, type, target, action, rationale, priority, confidence, effort, status, metadata
                FROM decisions
                WHERE project_id = ?
                ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, confidence DESC
                """,
                (project_id,),
            )
            return cursor.fetchall()

    def _save_enterprise_config_sync(self, agent: str, payload: dict[str, object], timestamp: str) -> None:
        with self._connect_sync() as db:
            if self.is_postgres:
                self._db_execute(
                    db,
                    """
                    INSERT INTO enterprise_config (agent, payload, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT (agent) DO UPDATE SET
                        payload = EXCLUDED.payload,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (agent, json.dumps(payload), timestamp),
                )
            else:
                self._db_execute(
                    db,
                    """
                    INSERT OR REPLACE INTO enterprise_config (agent, payload, updated_at)
                    VALUES (?, ?, ?)
                    """,
                    (agent, json.dumps(payload), timestamp),
                )
            db.commit()

    def _get_enterprise_config_sync(self, agent: str):
        with self._connect_sync() as db:
            cursor = self._db_execute(
                db,
                """
                SELECT payload FROM enterprise_config
                WHERE agent = ?
                """,
                (agent,),
            )
            row = cursor.fetchone()
            return json.loads(row[0]) if row else None

    def _save_run_history_sync(self, record: RunHistoryRecord) -> None:
        with self._connect_sync() as db:
            if self.is_postgres:
                self._db_execute(
                    db,
                    """
                    INSERT INTO run_history (
                        run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, raw_artifact, runtime_label,
                        run_profile_id, run_profile_name, chip_type, client_profile, parser_format, parser_confidence, parser_warnings, started_at, completed_at,
                        duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                        analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                        scorecard_mode, error_message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (run_id) DO UPDATE SET
                        project_id = EXCLUDED.project_id,
                        agent = EXCLUDED.agent,
                        mode = EXCLUDED.mode,
                        status = EXCLUDED.status,
                        provider = EXCLUDED.provider,
                        model = EXCLUDED.model,
                        artifact_name = EXCLUDED.artifact_name,
                        artifact_source = EXCLUDED.artifact_source,
                        raw_artifact = EXCLUDED.raw_artifact,
                        runtime_label = EXCLUDED.runtime_label,
                        run_profile_id = EXCLUDED.run_profile_id,
                        run_profile_name = EXCLUDED.run_profile_name,
                        chip_type = EXCLUDED.chip_type,
                        client_profile = EXCLUDED.client_profile,
                        parser_format = EXCLUDED.parser_format,
                        parser_confidence = EXCLUDED.parser_confidence,
                        parser_warnings = EXCLUDED.parser_warnings,
                        started_at = EXCLUDED.started_at,
                        completed_at = EXCLUDED.completed_at,
                        duration_ms = EXCLUDED.duration_ms,
                        total_decisions = EXCLUDED.total_decisions,
                        high = EXCLUDED.high,
                        medium = EXCLUDED.medium,
                        low = EXCLUDED.low,
                        request_payload = EXCLUDED.request_payload,
                        orchestration = EXCLUDED.orchestration,
                        analysis_log = EXCLUDED.analysis_log,
                        decisions = EXCLUDED.decisions,
                        observability = EXCLUDED.observability,
                        benchmark_title = EXCLUDED.benchmark_title,
                        benchmark_score = EXCLUDED.benchmark_score,
                        benchmark_notes = EXCLUDED.benchmark_notes,
                        scorecard_mode = EXCLUDED.scorecard_mode,
                        error_message = EXCLUDED.error_message
                    """,
                    self._run_history_params(record),
                )
            else:
                self._db_execute(
                    db,
                    """
                    INSERT OR REPLACE INTO run_history (
                        run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, raw_artifact, runtime_label,
                        run_profile_id, run_profile_name, chip_type, client_profile, parser_format, parser_confidence, parser_warnings, started_at, completed_at,
                        duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                        analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                        scorecard_mode, error_message
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._run_history_params(record),
                )
            db.commit()

    def _get_run_history_sync(self, project_id: str | None, agent: str | None, limit: int):
        query = (
            "SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, runtime_label, "
            "run_profile_id, run_profile_name, parser_format, parser_confidence, started_at, duration_ms, total_decisions, high, medium, low, benchmark_title, benchmark_score, error_message "
            "FROM run_history"
        )
        clauses = []
        params: list[object] = []
        if project_id:
            clauses.append("project_id = ?")
            params.append(project_id)
        if agent:
            clauses.append("agent = ?")
            params.append(agent)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        with self._connect_sync() as db:
            cursor = self._db_execute(db, query, tuple(params))
            return cursor.fetchall()

    def _get_run_sync(self, run_id: str):
        with self._connect_sync() as db:
            cursor = self._db_execute(
                db,
                """
                SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, artifact_source, raw_artifact, runtime_label,
                       run_profile_id, run_profile_name, chip_type, client_profile, parser_format, parser_confidence, parser_warnings, started_at, completed_at,
                       duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                       analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                       scorecard_mode, error_message
                FROM run_history
                WHERE run_id = ?
                """,
                (run_id,),
            )
            return cursor.fetchone()

    def _record_export_sync(self, run_id: str, target: str, title: str, filename: str, timestamp: str) -> None:
        with self._connect_sync() as db:
            self._db_execute(
                db,
                """
                INSERT INTO export_history (run_id, target, title, filename, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, target, title, filename, timestamp),
            )
            db.commit()

    def _get_export_history_sync(self, run_id: str):
        with self._connect_sync() as db:
            cursor = self._db_execute(
                db,
                """
                SELECT run_id, target, title, filename, created_at
                FROM export_history
                WHERE run_id = ?
                ORDER BY created_at DESC
                """,
                (run_id,),
            )
            return cursor.fetchall()

    def _get_pilot_metrics_sync(self, access_enabled: bool = False, recent_limit: int = 6) -> PilotMetricsResponse:
        with self._connect_sync() as db:
            run_rows = db.execute(
                """
                SELECT run_id, project_id, agent, status, provider, artifact_source, run_profile_name,
                       parser_confidence, parser_warnings, duration_ms, total_decisions, benchmark_score, scorecard_mode
                FROM run_history
                ORDER BY started_at DESC
                """
            ).fetchall()
            feedback_rows = db.execute("SELECT accepted FROM feedback").fetchall()
            export_count = int(db.execute("SELECT COUNT(*) FROM export_history").fetchone()[0] or 0)
        recent_rows = self._get_run_history_sync(None, None, max(1, min(recent_limit, 12)))
        recent_runs = [self._run_history_summary_from_row(row) for row in recent_rows]
        return self._build_pilot_metrics(
            run_rows=run_rows,
            feedback_rows=feedback_rows,
            export_count=export_count,
            recent_runs=recent_runs,
            access_enabled=access_enabled,
        )

    def _default_enterprise_config(self, agent: str) -> dict[str, object]:
        if agent == "agent01":
            return Agent01EnterpriseConfig().model_dump()
        if agent == "agent02":
            return Agent02EnterpriseConfig().model_dump()
        raise ValueError(f"Unsupported agent config key: {agent}")

    def _run_history_params(self, record: RunHistoryRecord) -> tuple[object, ...]:
        return (
            record.run_id,
            record.project_id,
            record.agent,
            record.mode,
            record.status,
            record.provider,
            record.model or "",
            record.artifact_name or "",
            record.artifact_source or "unknown",
            record.raw_artifact or "",
            record.runtime_label or "",
            record.run_profile_id or "",
            record.run_profile_name or "",
            record.chip_type or "",
            record.client_profile or "",
            record.parser_format or "",
            record.parser_confidence or 0.0,
            json.dumps(record.parser_warnings),
            record.started_at.isoformat(),
            record.completed_at.isoformat(),
            record.duration_ms,
            record.total_decisions,
            record.high,
            record.medium,
            record.low,
            json.dumps(record.request_payload),
            json.dumps(record.orchestration),
            json.dumps(record.analysis_log),
            json.dumps([decision.model_dump() for decision in record.decisions]),
            json.dumps(record.observability),
            record.benchmark_title or "",
            record.benchmark_score or "",
            json.dumps(record.benchmark_notes),
            record.scorecard_mode,
            record.error_message or "",
        )

    def _run_history_summary_from_row(self, row) -> RunHistorySummary:
        return RunHistorySummary(
            run_id=row[0],
            project_id=row[1],
            agent=row[2],
            mode=row[3],
            status=row[4],
            provider=row[5],
            model=row[6] or None,
            artifact_name=row[7] or None,
            artifact_source=row[8] or "unknown",
            runtime_label=row[9] or None,
            run_profile_id=row[10] or None,
            run_profile_name=row[11] or None,
            parser_format=row[12] or None,
            parser_confidence=row[13],
            started_at=datetime.fromisoformat(row[14]),
            duration_ms=row[15],
            total_decisions=row[16],
            high=row[17],
            medium=row[18],
            low=row[19],
            benchmark_title=row[20] or None,
            benchmark_score=row[21] or None,
            feedback_summary=FeedbackSummary(),
            export_count=0,
            error_message=row[22] or None,
        )

    def _run_history_record_from_row(self, row) -> RunHistoryRecord:
        return RunHistoryRecord(
            run_id=row[0],
            project_id=row[1],
            agent=row[2],
            mode=row[3],
            status=row[4],
            provider=row[5],
            model=row[6] or None,
            artifact_name=row[7] or None,
            artifact_source=row[8] or "unknown",
            raw_artifact=row[9] or None,
            runtime_label=row[10] or None,
            run_profile_id=row[11] or None,
            run_profile_name=row[12] or None,
            chip_type=row[13] or None,
            client_profile=row[14] or None,
            parser_format=row[15] or None,
            parser_confidence=row[16],
            parser_warnings=json.loads(row[17] or "[]"),
            started_at=datetime.fromisoformat(row[18]),
            completed_at=datetime.fromisoformat(row[19]),
            duration_ms=row[20],
            total_decisions=row[21],
            high=row[22],
            medium=row[23],
            low=row[24],
            request_payload=json.loads(row[25]),
            orchestration=json.loads(row[26]),
            analysis_log=json.loads(row[27]),
            decisions=[Decision(**item) for item in json.loads(row[28])],
            observability=json.loads(row[29]),
            benchmark_title=row[30] or None,
            benchmark_score=row[31] or None,
            benchmark_notes=json.loads(row[32]),
            scorecard_mode=row[33] or "live",
            error_message=row[34] or None,
        )

    async def _ensure_async_column(self, db, table: str, column: str, definition: str) -> None:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        existing = {row[1] for row in rows}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_sync_column(self, db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        if self.is_postgres:
            cursor = self._db_execute(
                db,
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
                """,
                (table, column),
            )
            rows = cursor.fetchall()
            existing = {row[0] for row in rows}
        else:
            cursor = db.execute(f"PRAGMA table_info({table})")
            rows = cursor.fetchall()
            existing = {row[1] for row in rows}
        if column not in existing:
            self._db_execute(db, f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _feedback_summary(self, feedback: list[FeedbackRecord]) -> FeedbackSummary:
        if not feedback:
            return FeedbackSummary()
        accepted = sum(1 for item in feedback if item.accepted)
        rejected = sum(1 for item in feedback if not item.accepted)
        latest = max(item.timestamp for item in feedback)
        return FeedbackSummary(
            total=len(feedback),
            accepted=accepted,
            rejected=rejected,
            latest_timestamp=latest,
        )

    def _build_pilot_metrics(
        self,
        run_rows,
        feedback_rows,
        export_count: int,
        recent_runs: list[RunHistorySummary],
        access_enabled: bool,
    ) -> PilotMetricsResponse:
        total_runs = len(run_rows)
        completed_runs = sum(1 for row in run_rows if row[3] == "completed")
        failed_runs = sum(1 for row in run_rows if row[3] == "failed")
        benchmark_runs = sum(1 for row in run_rows if (row[12] or "live") == "benchmark")
        live_runs = sum(1 for row in run_rows if (row[12] or "live") != "benchmark")
        total_decisions = sum(int(row[10] or 0) for row in run_rows)
        accepted_decisions = sum(1 for row in feedback_rows if bool(row[0]))
        rejected_decisions = sum(1 for row in feedback_rows if not bool(row[0]))
        avg_duration_ms = round(sum(int(row[9] or 0) for row in run_rows) / total_runs) if total_runs else 0
        parser_confidences = [float(row[7]) for row in run_rows if row[7] is not None]
        avg_parser_confidence = round(sum(parser_confidences) / len(parser_confidences), 2) if parser_confidences else 0.0

        benchmark_scores = []
        artifact_source_counts: dict[str, int] = {}
        agent_counts: dict[str, int] = {}
        provider_counts: dict[str, int] = {}
        profile_counts: dict[str, int] = {}
        warning_counts: dict[str, int] = {}

        for row in run_rows:
            score_value = self._extract_score_value(row[11])
            if score_value is not None and (row[12] or "live") == "benchmark":
                benchmark_scores.append(score_value)
            artifact_source_counts[row[5] or "unknown"] = artifact_source_counts.get(row[5] or "unknown", 0) + 1
            agent_counts[row[2] or "unknown"] = agent_counts.get(row[2] or "unknown", 0) + 1
            provider_key = row[4] or "unknown"
            provider_counts[provider_key] = provider_counts.get(provider_key, 0) + 1
            profile_key = row[6] or "Custom run"
            profile_counts[profile_key] = profile_counts.get(profile_key, 0) + 1
            for warning in json.loads(row[8] or "[]"):
                text = str(warning).strip()
                if text:
                    warning_counts[text] = warning_counts.get(text, 0) + 1

        avg_benchmark_score = round(sum(benchmark_scores) / len(benchmark_scores), 1) if benchmark_scores else 0.0
        feedback_total = accepted_decisions + rejected_decisions
        acceptance_rate = round((accepted_decisions / feedback_total) * 100, 1) if feedback_total else 0.0

        return PilotMetricsResponse(
            generated_at=datetime.now(timezone.utc),
            pilot_access_enabled=access_enabled,
            total_runs=total_runs,
            completed_runs=completed_runs,
            failed_runs=failed_runs,
            benchmark_runs=benchmark_runs,
            live_runs=live_runs,
            total_decisions=total_decisions,
            accepted_decisions=accepted_decisions,
            rejected_decisions=rejected_decisions,
            acceptance_rate=acceptance_rate,
            avg_duration_ms=avg_duration_ms,
            avg_parser_confidence=avg_parser_confidence,
            avg_benchmark_score=avg_benchmark_score,
            total_exports=export_count,
            artifact_source_breakdown=self._breakdown_items(artifact_source_counts),
            agent_breakdown=self._breakdown_items(agent_counts),
            provider_breakdown=self._breakdown_items(provider_counts),
            run_profile_breakdown=self._breakdown_items(profile_counts, limit=6),
            parser_warning_breakdown=self._warning_items(warning_counts, limit=6),
            recent_runs=recent_runs,
        )

    def _breakdown_items(self, counts: dict[str, int], limit: int | None = None) -> list[PilotBreakdownItem]:
        items = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
        if limit is not None:
            items = items[:limit]
        return [PilotBreakdownItem(label=label, count=count) for label, count in items]

    def _warning_items(self, counts: dict[str, int], limit: int | None = None) -> list[PilotParserWarningItem]:
        items = sorted(counts.items(), key=lambda item: (-item[1], item[0].lower()))
        if limit is not None:
            items = items[:limit]
        return [PilotParserWarningItem(warning=warning, count=count) for warning, count in items]

    def _extract_score_value(self, score_text: str | None) -> float | None:
        text = str(score_text or "").strip()
        if not text:
            return None
        head = text.split("/", 1)[0].strip()
        try:
            return float(head)
        except ValueError:
            return None
