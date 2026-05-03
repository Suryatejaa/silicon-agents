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
    RunHistoryRecord,
    RunHistorySummary,
)

try:
    import aiosqlite  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - fallback for fresh local envs
    aiosqlite = None


class FeedbackStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def init(self) -> None:
        if aiosqlite is None:
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
                    runtime_label TEXT NOT NULL,
                    run_profile_id TEXT NOT NULL,
                    run_profile_name TEXT NOT NULL,
                    chip_type TEXT NOT NULL,
                    client_profile TEXT NOT NULL,
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
            await db.commit()

    async def save_decisions(self, decisions: list[Decision]) -> None:
        if not decisions:
            return
        if aiosqlite is None:
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
        if aiosqlite is None:
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
        if aiosqlite is None:
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
        if aiosqlite is None:
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
        if aiosqlite is None:
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
        if aiosqlite is None:
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
        if aiosqlite is None:
            self._save_run_history_sync(record)
            return
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO run_history (
                    run_id, project_id, agent, mode, status, provider, model, artifact_name, runtime_label,
                    run_profile_id, run_profile_name, chip_type, client_profile, started_at, completed_at,
                    duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                    analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                    scorecard_mode, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        if aiosqlite is None:
            rows = self._get_run_history_sync(project_id, agent, limit)
        else:
            query = (
                "SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, runtime_label, "
                "run_profile_id, run_profile_name, started_at, duration_ms, total_decisions, high, medium, low, benchmark_title, benchmark_score, error_message "
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
        if aiosqlite is None:
            row = self._get_run_sync(run_id)
        else:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, runtime_label,
                           run_profile_id, run_profile_name, chip_type, client_profile, started_at, completed_at,
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
        if aiosqlite is None:
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
        if aiosqlite is None:
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

    def _connect_sync(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _init_sync(self) -> None:
        with self._connect_sync() as db:
            db.execute(
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
            db.execute(
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
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS enterprise_config (
                    agent TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            db.execute(
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
                    runtime_label TEXT NOT NULL,
                    run_profile_id TEXT NOT NULL,
                    run_profile_name TEXT NOT NULL,
                    chip_type TEXT NOT NULL,
                    client_profile TEXT NOT NULL,
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
            db.execute(
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
            db.commit()

    def _save_decisions_sync(self, decisions: list[Decision]) -> None:
        with self._connect_sync() as db:
            db.executemany(
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
            db.execute(
                """
                INSERT INTO feedback (decision_id, project_id, run_id, accepted, notes, engineer_id, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (decision_id, project_id, run_id, int(accepted), notes, engineer_id, timestamp),
            )
            db.execute(
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
            cursor = db.execute(query, tuple(params))
            return cursor.fetchall()

    def _get_decisions_sync(self, project_id: str):
        with self._connect_sync() as db:
            cursor = db.execute(
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
            db.execute(
                """
                INSERT OR REPLACE INTO enterprise_config (agent, payload, updated_at)
                VALUES (?, ?, ?)
                """,
                (agent, json.dumps(payload), timestamp),
            )
            db.commit()

    def _get_enterprise_config_sync(self, agent: str):
        with self._connect_sync() as db:
            cursor = db.execute(
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
            db.execute(
                """
                INSERT OR REPLACE INTO run_history (
                    run_id, project_id, agent, mode, status, provider, model, artifact_name, runtime_label,
                    run_profile_id, run_profile_name, chip_type, client_profile, started_at, completed_at,
                    duration_ms, total_decisions, high, medium, low, request_payload, orchestration,
                    analysis_log, decisions, observability, benchmark_title, benchmark_score, benchmark_notes,
                    scorecard_mode, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._run_history_params(record),
            )
            db.commit()

    def _get_run_history_sync(self, project_id: str | None, agent: str | None, limit: int):
        query = (
            "SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, runtime_label, "
            "run_profile_id, run_profile_name, started_at, duration_ms, total_decisions, high, medium, low, benchmark_title, benchmark_score, error_message "
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
            cursor = db.execute(query, tuple(params))
            return cursor.fetchall()

    def _get_run_sync(self, run_id: str):
        with self._connect_sync() as db:
            cursor = db.execute(
                """
                SELECT run_id, project_id, agent, mode, status, provider, model, artifact_name, runtime_label,
                       run_profile_id, run_profile_name, chip_type, client_profile, started_at, completed_at,
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
            db.execute(
                """
                INSERT INTO export_history (run_id, target, title, filename, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, target, title, filename, timestamp),
            )
            db.commit()

    def _get_export_history_sync(self, run_id: str):
        with self._connect_sync() as db:
            cursor = db.execute(
                """
                SELECT run_id, target, title, filename, created_at
                FROM export_history
                WHERE run_id = ?
                ORDER BY created_at DESC
                """,
                (run_id,),
            )
            return cursor.fetchall()

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
            record.runtime_label or "",
            record.run_profile_id or "",
            record.run_profile_name or "",
            record.chip_type or "",
            record.client_profile or "",
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
            runtime_label=row[8] or None,
            run_profile_id=row[9] or None,
            run_profile_name=row[10] or None,
            started_at=datetime.fromisoformat(row[11]),
            duration_ms=row[12],
            total_decisions=row[13],
            high=row[14],
            medium=row[15],
            low=row[16],
            benchmark_title=row[17] or None,
            benchmark_score=row[18] or None,
            feedback_summary=FeedbackSummary(),
            export_count=0,
            error_message=row[19] or None,
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
            runtime_label=row[8] or None,
            run_profile_id=row[9] or None,
            run_profile_name=row[10] or None,
            chip_type=row[11] or None,
            client_profile=row[12] or None,
            started_at=datetime.fromisoformat(row[13]),
            completed_at=datetime.fromisoformat(row[14]),
            duration_ms=row[15],
            total_decisions=row[16],
            high=row[17],
            medium=row[18],
            low=row[19],
            request_payload=json.loads(row[20]),
            orchestration=json.loads(row[21]),
            analysis_log=json.loads(row[22]),
            decisions=[Decision(**item) for item in json.loads(row[23])],
            observability=json.loads(row[24]),
            benchmark_title=row[25] or None,
            benchmark_score=row[26] or None,
            benchmark_notes=json.loads(row[27]),
            scorecard_mode=row[28] or "live",
            error_message=row[29] or None,
        )

    async def _ensure_async_column(self, db, table: str, column: str, definition: str) -> None:
        cursor = await db.execute(f"PRAGMA table_info({table})")
        rows = await cursor.fetchall()
        existing = {row[1] for row in rows}
        if column not in existing:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_sync_column(self, db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        cursor = db.execute(f"PRAGMA table_info({table})")
        rows = cursor.fetchall()
        existing = {row[1] for row in rows}
        if column not in existing:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

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
