from pydantic import BaseModel, Field, computed_field
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


# Tingkat risiko ordinal (Subbab 3.2 variabel perantara) dan pemetaan numeriknya
RISK_SCORE_MAP = {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75, "CRITICAL": 1.0}
RISK_LEVEL_BY_SCORE = {v: k for k, v in RISK_SCORE_MAP.items()}


class ViolatedArticle(BaseModel):
    regulation: str = ""
    article: str = ""
    violation_detail: str = ""
    required_value: Optional[str] = None
    actual_value: Optional[str] = None
    # True = pasal yang dikutip ada di Top-K hasil retrieval; False = ungrounded;
    # None = tidak dapat diperiksa (Subbab 3.3.3)
    grounded: Optional[bool] = None


class AgentVerdict(BaseModel):
    agent_name: str = Field(..., description="Agent name (BI/OJK)")
    status: ComplianceStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    violations: List[str] = Field(default_factory=list)
    violated_articles: List[ViolatedArticle] = Field(default_factory=list, description="Pelanggaran per pasal beserta flag grounded")
    evidence: List[EvidenceItem] = Field(default_factory=list)
    reasoning: str = Field(..., description="Agent reasoning")
    checklist_topic: Optional[str] = Field(None, description="Regulatory checklist topic used")
    checklist_covered: List[str] = Field(default_factory=list, description="Sub-elements covered by clause")
    missing_elements: List[str] = Field(default_factory=list, description="Sub-elements missing from clause")


class AuditRequest(BaseModel):
    clause: str = Field(..., description="SOP clause to audit")
    clause_id: Optional[str] = Field(None, description="Optional clause identifier")
    context: Optional[str] = Field(None, description="Additional context")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of documents to retrieve")
    regulator: str = Field(default="all", description="Regulator to check (all, BI, OJK)")
    use_cache: bool = Field(default=True, description="Set to false to force re-run and skip cache")


class AuditResponse(BaseModel):
    request_id: str = Field(..., description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.now)
    clause: str
    clause_id: Optional[str] = None
    
    bi_verdict: AgentVerdict = Field(..., description="BI Agent verdict")
    ojk_verdict: AgentVerdict = Field(..., description="OJK Agent verdict")
    
    final_status: ComplianceStatus = Field(..., description="Final compliance status")
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Pemetaan numerik tingkat risiko (LOW 0,25 · MEDIUM 0,5 · HIGH 0,75 · CRITICAL 1,0); 0 = tidak dinilai")

    violations: List[str] = Field(default_factory=list, description="Pelanggaran pasal dari agen BI dan OJK")
    regulatory_conflicts: List[str] = Field(default_factory=list, description="Konflik antar-regulator yang dicatat Conflict Resolver")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations")
    
    latency_ms: float = Field(..., description="Processing time in milliseconds")
    model_used: str = Field(default="gpt-5.4-mini", description="LLM model used")
    tokens_used: int = Field(default=0, description="Total tokens used")

    # SOP Gate fields
    is_sop_clause: bool = Field(default=True, description="Whether input was classified as SOP clause by gate")
    gate_confidence: float = Field(default=1.0, description="Gate classifier confidence score")
    gate_model: str = Field(default="rule_based", description="Gate model used")
    gate_decision: str = Field(default="REGULATION_CLAUSE_VALID", description="REGULATION_CLAUSE_VALID | NOT_REGULATION_CLAUSE")

    # Struktur output Subbab 3.3.3 proposal
    evidence_trail: List[dict] = Field(default_factory=list, description="Rujukan pasal Top-K (regulator, dokumen, pasal, relevance_score)")
    analysis_mode: Optional[str] = Field(None, description="multi_agent_rag | llm_only | gate_rejected | noise_filtered | unclear_text | ...")
    retrieval_mode: Optional[str] = Field(None, description="hybrid | dense | none")

    @computed_field
    @property
    def risk_level(self) -> Optional[str]:
        """Tingkat risiko ordinal; None bila risiko tidak dinilai (gate menolak, mode LLM-only)."""
        return RISK_LEVEL_BY_SCORE.get(round(self.risk_score, 2))


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