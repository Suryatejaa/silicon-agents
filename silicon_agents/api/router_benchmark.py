"""Routes for benchmark scorecards."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from silicon_agents.benchmarks.agent01_scorecard import (
    evaluate_agent01_benchmark,
    list_agent01_benchmarks,
)
from silicon_agents.benchmarks.agent02_scorecard import (
    evaluate_agent02_benchmark,
    list_agent02_benchmarks,
)
from silicon_agents.core.schemas import (
    BenchmarkDefinitionResponse,
    BenchmarkEvaluationRequest,
    BenchmarkEvaluationResponse,
)


router = APIRouter(prefix="/api/v1/benchmarks", tags=["benchmarks"])


@router.get("/agent01", response_model=list[BenchmarkDefinitionResponse])
async def list_benchmarks() -> list[BenchmarkDefinitionResponse]:
    return [BenchmarkDefinitionResponse(**item) for item in list_agent01_benchmarks()]


@router.post("/agent01/evaluate", response_model=BenchmarkEvaluationResponse)
async def evaluate_benchmark(request: BenchmarkEvaluationRequest) -> BenchmarkEvaluationResponse:
    try:
        result = evaluate_agent01_benchmark(request.benchmark_id, request.decisions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BenchmarkEvaluationResponse(**result)


@router.get("/agent02", response_model=list[BenchmarkDefinitionResponse])
async def list_agent02() -> list[BenchmarkDefinitionResponse]:
    return [BenchmarkDefinitionResponse(**item) for item in list_agent02_benchmarks()]


@router.post("/agent02/evaluate", response_model=BenchmarkEvaluationResponse)
async def evaluate_agent02(request: BenchmarkEvaluationRequest) -> BenchmarkEvaluationResponse:
    try:
        result = evaluate_agent02_benchmark(request.benchmark_id, request.decisions)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return BenchmarkEvaluationResponse(**result)
