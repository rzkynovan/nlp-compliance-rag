from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class Regulator(str, Enum):
    BI = "BI"
    OJK = "OJK"


class RegulationMetadata(BaseModel):
    document_id: str
    document_name: str
    regulator: Regulator
    year: int
    effective_date: Optional[datetime] = None
    total_pages: int
    total_chunks: int
    status: str = "active"


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    regulator: Regulator
    chapter: Optional[str] = None
    article: str
    verse: Optional[str] = None
    content: str
    embedding_model: str = "text-embedding-3-large"
    created_at: datetime = Field(default_factory=datetime.now)


class RegulationListResponse(BaseModel):
    regulations: List[RegulationMetadata]
    total: int


class ChunkSearchRequest(BaseModel):
    query: str = Field(..., min_length=5, max_length=1000)
    regulator: Optional[Regulator] = None
    top_k: int = Field(default=5, ge=1, le=20)


class ChunkSearchResponse(BaseModel):
    query: str
    chunks: List[ChunkMetadata]
    total: int
    latency_ms: float