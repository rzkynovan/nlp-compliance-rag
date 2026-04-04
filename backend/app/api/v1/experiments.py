from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models.experiment import (
    ExperimentRun, ExperimentMetrics, ExperimentParams,
    ExperimentListResponse, ExperimentCreate, ExperimentComparison
)
from app.ml.tracking import ExperimentTracker
import os
from app.config import settings

router = APIRouter()

tracker = ExperimentTracker(tracking_uri=settings.MLFLOW_TRACKING_URI)


@router.get("/list", response_model=ExperimentListResponse)
async def list_experiments(skip: int = 0, limit: int = 20):
    experiments = tracker.list_experiments(skip=skip, limit=limit)
    
    return ExperimentListResponse(
        experiments=experiments,
        total=len(experiments)
    )


@router.post("/create", response_model=ExperimentRun)
async def create_experiment(request: ExperimentCreate):
    run_id = tracker.start_run(
        experiment_name=request.name,
        params=request.params.model_dump(),
        tags={"description": request.description or ""}
    )
    
    return ExperimentRun(
        run_id=run_id,
        experiment_id=run_id.split("_")[0] if "_" in run_id else run_id,
        experiment_name=request.name,
        status="RUNNING",
        start_time=tracker.get_run_start_time(run_id),
        params=request.params
    )


@router.post("/{run_id}/complete")
async def complete_experiment(run_id: str, metrics: ExperimentMetrics):
    tracker.log_metrics(run_id, metrics.model_dump())
    tracker.end_run(run_id)
    
    return {"status": "completed", "run_id": run_id}


@router.get("/{run_id}", response_model=ExperimentRun)
async def get_experiment(run_id: str):
    run = tracker.get_run(run_id)
    
    if not run:
        raise HTTPException(status_code=404, detail="Experiment run not found")
    
    return run


@router.post("/compare", response_model=ExperimentComparison)
async def compare_experiments(experiment_ids: List[str]):
    comparison = tracker.compare_runs(experiment_ids)
    
    return comparison


@router.get("/{run_id}/artifacts")
async def get_artifacts(run_id: str):
    artifacts = tracker.get_artifacts(run_id)
    
    return {"run_id": run_id, "artifacts": artifacts}