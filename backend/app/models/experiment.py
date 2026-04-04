from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ExperimentStatus(str, Enum):
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"
    KILLED = "KILLED"


class ExperimentParams(BaseModel):
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-4o"
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)
    top_k: int = Field(default=5, ge=1, le=20)
    chunking_strategy: str = "hierarchical"
    chunk_size: int = Field(default=512, ge=128, le=2048)


class ExperimentMetrics(BaseModel):
    precision: float = Field(..., ge=0.0, le=1.0)
    recall: float = Field(..., ge=0.0, le=1.0)
    f1_score: float = Field(..., ge=0.0, le=1.0)
    mrr: float = Field(..., ge=0.0, le=1.0, description="Mean Reciprocal Rank")
    hit_rate_at_k: Dict[int, float] = Field(default_factory=dict)
    avg_latency_ms: float
    total_tokens: int
    cost_usd: float


class ExperimentRun(BaseModel):
    run_id: str
    experiment_id: str
    experiment_name: str
    status: ExperimentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    params: ExperimentParams
    metrics: Optional[ExperimentMetrics] = None
    artifacts: List[str] = Field(default_factory=list)
    tags: Dict[str, str] = Field(default_factory=dict)


class ExperimentComparison(BaseModel):
    experiment_ids: List[str]
    comparison_table: List[Dict[str, Any]]
    best_run_id: str
    best_metric: str
    metric_value: float


class ExperimentCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = None
    params: ExperimentParams


class ExperimentListResponse(BaseModel):
    experiments: List[ExperimentRun]
    total: int