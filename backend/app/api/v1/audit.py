from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from typing import List
from datetime import datetime
import uuid
import time
import sys
import os

from app.models.audit import (
    AuditRequest, AuditResponse, BatchAuditRequest, BatchAuditResponse,
    ComplianceStatus, AgentVerdict, EvidenceItem, AuditHistoryItem
)
from app.services.rag_service import get_rag_service

router = APIRouter(prefix="/audit", tags=["audit"])

audit_history: List[AuditHistoryItem] = []

RISK_SCORE_MAP = {"LOW": 0.25, "MEDIUM": 0.5, "HIGH": 0.75}


def _map_status(status: str) -> ComplianceStatus:
    status_mapping = {
        "COMPLIANT": ComplianceStatus.COMPLIANT,
        "NON_COMPLIANT": ComplianceStatus.NON_COMPLIANT,
        "PARTIALLY_COMPLIANT": ComplianceStatus.PARTIALLY_COMPLIANT,
        "NEEDS_REVIEW": ComplianceStatus.NEEDS_REVIEW,
        "NOT_ADDRESSED": ComplianceStatus.NOT_ADDRESSED,
        "UNCLEAR": ComplianceStatus.UNCLEAR,
    }
    return status_mapping.get(status, ComplianceStatus.UNCLEAR)


def _map_risk_score(risk_score) -> float:
    if isinstance(risk_score, str):
        return RISK_SCORE_MAP.get(risk_score.upper(), 0.5)
    return float(risk_score) if risk_score is not None else 0.5


def _extract_verdict_data(verdict_data, agent_name: str) -> AgentVerdict:
    if not verdict_data:
        return AgentVerdict(
            agent_name=agent_name,
            status=ComplianceStatus.UNCLEAR,
            confidence=0.5,
            violations=[],
            evidence=[],
            reasoning="No verdict available"
        )
    
    # Extract violations - handle both dict and string formats
    raw_violations = verdict_data.get("violations", verdict_data.get("violated_articles", []))
    violations = []
    for v in raw_violations:
        if isinstance(v, dict):
            violations.append(f"{v.get('article', '')}: {v.get('description', '')}")
        else:
            violations.append(str(v))
    
    # Extract evidence
    evidence = []
    for e in verdict_data.get("evidence", []):
        if isinstance(e, dict):
            evidence.append(EvidenceItem(
                regulation=e.get("regulation", ""),
                article=e.get("article", ""),
                article_text=e.get("article_text", ""),
                relevance_score=e.get("relevance_score", 0.5)
            ))
    
    return AgentVerdict(
        agent_name=agent_name,
        status=_map_status(verdict_data.get("verdict", verdict_data.get("status", "UNCLEAR"))),
        confidence=verdict_data.get("confidence_score", verdict_data.get("confidence", 0.5)),
        violations=violations,
        evidence=evidence,
        reasoning=verdict_data.get("reasoning_trace", verdict_data.get("reasoning", ""))
    )


@router.post("/analyze", response_model=AuditResponse)
async def analyze_sop(request: AuditRequest):
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    try:
        service = get_rag_service()
        result = await service.analyze_with_rag(
            clause=request.clause,
            regulator=request.regulator,
            top_k=request.top_k,
            clause_id=request.clause_id,
            use_cache=True
        )
        
        latency_ms = (time.time() - start_time) * 1000
        
        bi_verdict = _extract_verdict_data(result.get("bi_verdict"), "BI_SPECIALIST")
        ojk_verdict = _extract_verdict_data(result.get("ojk_verdict"), "OJK_SPECIALIST")
        
        response = AuditResponse(
            request_id=request_id,
            timestamp=datetime.now(),
            clause=request.clause,
            clause_id=request.clause_id,
            bi_verdict=bi_verdict,
            ojk_verdict=ojk_verdict,
            final_status=_map_status(result.get("final_status", "UNCLEAR")),
            overall_confidence=result.get("overall_confidence", 0.5),
            risk_score=_map_risk_score(result.get("risk_score")),
            violations=result.get("violations", []),
            recommendations=result.get("recommendations", []),
            latency_ms=result.get("latency_ms", latency_ms),
            model_used=result.get("model_used", "gpt-4o-mini"),
            tokens_used=0
        )
        
        history_item = AuditHistoryItem(
            request_id=request_id,
            timestamp=datetime.now(),
            clause=request.clause,
            final_status=response.final_status,
            overall_confidence=response.overall_confidence,
            latency_ms=latency_ms
        )
        audit_history.append(history_item)
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@router.post("/batch", response_model=BatchAuditResponse)
async def batch_analyze(request: BatchAuditRequest, background_tasks: BackgroundTasks):
    results = []
    total_tokens = 0
    status_counts = {}
    
    for clause_request in request.clauses:
        response = await analyze_sop(clause_request)
        results.append(response)
        total_tokens += response.tokens_used
        
        status = response.final_status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    return BatchAuditResponse(
        request_id=str(uuid.uuid4()),
        timestamp=datetime.now(),
        total_clauses=len(results),
        results=results,
        summary={
            "total_tokens": total_tokens,
            "status_distribution": status_counts,
            "avg_latency_ms": sum(r.latency_ms for r in results) / len(results)
        }
    )


@router.get("/history", response_model=List[AuditHistoryItem])
async def get_audit_history(skip: int = 0, limit: int = 20):
    return audit_history[skip:skip + limit]


@router.get("/{request_id}", response_model=AuditResponse)
async def get_audit_detail(request_id: str):
    for item in audit_history:
        if item.request_id == request_id:
            return AuditResponse(
                request_id=request_id,
                timestamp=item.timestamp,
                clause=item.clause,
                clause_id=None,
                bi_verdict=AgentVerdict(
                    agent_name="BI_SPECIALIST",
                    status=item.final_status,
                    confidence=item.overall_confidence,
                    violations=[],
                    evidence=[],
                    reasoning="Cached result"
                ),
                ojk_verdict=AgentVerdict(
                    agent_name="OJK_SPECIALIST",
                    status=item.final_status,
                    confidence=item.overall_confidence,
                    violations=[],
                    evidence=[],
                    reasoning="Cached result"
                ),
                final_status=item.final_status,
                overall_confidence=item.overall_confidence,
                risk_score=0.5,
                violations=[],
                recommendations=[],
                latency_ms=item.latency_ms,
                model_used="gpt-4o",
                tokens_used=0
            )
    raise HTTPException(status_code=404, detail="Audit request not found")