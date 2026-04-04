from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_ADDRESSED = "NOT_ADDRESSED"
    UNCLEAR = "UNCLEAR"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"


class EvidenceItem(BaseModel):
    regulation: str = Field(..., description="Regulation source (e.g., 'PBI 23/6/2021')")
    article: str = Field(..., description="Article number")
    article_text: str = Field(..., description="Full article text")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")


class AgentVerdict(BaseModel):
    agent_name: str = Field(..., description="Agent name (BI/OJK)")
    status: ComplianceStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    violations: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    reasoning: str = Field(..., description="Agent reasoning")


class AuditRequest(BaseModel):
    clause: str = Field(..., description="SOP clause to audit")
    clause_id: Optional[str] = Field(None, description="Optional clause identifier")
    context: Optional[str] = Field(None, description="Additional context")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of documents to retrieve")
    regulator: str = Field(default="all", description="Regulator to check (all, BI, OJK)")


class AuditResponse(BaseModel):
    request_id: str = Field(..., description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    clause: str
    clause_id: Optional[str] = None
    
    bi_verdict: AgentVerdict = Field(..., description="BI Agent verdict")
    ojk_verdict: AgentVerdict = Field(..., description="OJK Agent verdict")
    
    final_status: ComplianceStatus = Field(..., description="Final compliance status")
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0=low, 1=high)")
    
    violations: List[str] = Field(default_factory=list, description="All violations found")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    latency_ms: float = Field(..., description="Processing time in milliseconds")
    model_used: str = Field(default="gpt-4o", description="LLM model used")
    tokens_used: int = Field(default=0, description="Total tokens used")


class AuditHistoryItem(BaseModel):
    request_id: str
    timestamp: datetime
    clause: str
    final_status: ComplianceStatus
    overall_confidence: float
    latency_ms: float


class BatchAuditRequest(BaseModel):
    clauses: List[AuditRequest] = Field(..., min_length=1, max_length=100)


class BatchAuditResponse(BaseModel):
    request_id: str
    timestamp: datetime
    total_clauses: int
    results: List[AuditResponse]
    summary: dict = Field(..., description="Summary statistics")