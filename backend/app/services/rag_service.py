"""
rag_service.py — RAG Service for Multi-Agent Audit
===================================================
Service yang mengintegrasikan LlamaIndex RAG dengan multi-agent system
untuk audit kepatuhan regulasi.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from openai import OpenAI

from app.config import settings
from app.core.cache import AuditCache
from app.core.cost_tracker import cost_tracker
from app.core.exceptions import ComplianceAuditError

# Add src to path for imports (works in both local and Docker environments)
# In Docker: /app/src
# In local: project_root/src
_src_paths = [
    "/app/src",  # Docker path
    str(Path(__file__).parent.parent.parent.parent / "src"),  # Local dev path
]
for src_path in _src_paths:
    if Path(src_path).exists() and src_path not in sys.path:
        sys.path.insert(0, src_path)

logger = logging.getLogger(__name__)


class RAGAuditService:
    """
    RAG-powered audit service using multi-agent system.
    
    This service coordinates:
    1. Retrieval of relevant regulation articles from ChromaDB
    2. Multi-agent analysis (BI and OJK specialists)
    3. Conflict resolution between different regulators
    4. LLM-based verdict generation
    """
    
    def __init__(self):
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.llm_model = settings.LLM_MODEL
        self.embedding_model = settings.EMBEDDING_MODEL
        
        # Use ChromaDB path from settings (set via environment variable)
        # In Docker: CHROMADB_PERSIST_DIR=/app/data/processed/chroma_db
        # In local dev: uses default from config
        self.chroma_path = settings.CHROMADB_PERSIST_DIR
        
        # Cache path relative to ChromaDB path
        chroma_parent = Path(self.chroma_path).parent.parent
        self.cache = AuditCache(
            cache_dir=str(chroma_parent / "cache"),
            ttl_hours=settings.CACHE_TTL_HOURS
        )
        
        # Lazy load agents (only when needed)
        self._coordinator = None
        self._chroma_available = None
        
    def _check_chroma_available(self) -> bool:
        """Check if ChromaDB has data."""
        if self._chroma_available is not None:
            return self._chroma_available
        
        try:
            import chromadb
            db = chromadb.PersistentClient(path=self.chroma_path)
            
            # Check both collections
            bi_count = 0
            ojk_count = 0
            
            try:
                bi_collection = db.get_collection("bi_regulations")
                bi_count = bi_collection.count()
            except Exception:
                pass
            
            try:
                ojk_collection = db.get_collection("ojk_regulations")
                ojk_count = ojk_collection.count()
            except Exception:
                pass
            
            self._chroma_available = (bi_count > 0 or ojk_count > 0)
            
            if self._chroma_available:
                logger.info(f"ChromaDB available: BI={bi_count}, OJK={ojk_count} vectors")
            else:
                logger.warning("ChromaDB is empty. Falling back to LLM-only mode.")
            
            return self._chroma_available
            
        except Exception as e:
            logger.warning(f"ChromaDB not available: {e}. Falling back to LLM-only mode.")
            self._chroma_available = False
            return False
    
    def _get_coordinator(self):
        """Lazy load the coordinator agent."""
        if self._coordinator is None:
            try:
                from agents.coordinator import CoordinatorAgent
                self._coordinator = CoordinatorAgent()
                self._coordinator.initialize(
                    api_key=settings.OPENAI_API_KEY,
                    chroma_path=self.chroma_path
                )
                logger.info("Multi-agent coordinator initialized")
            except Exception as e:
                logger.warning(f"Could not initialize coordinator: {e}")
                raise
        return self._coordinator
    
    async def analyze_with_rag(
        self,
        clause: str,
        regulator: str = "all",
        top_k: int = 5,
        clause_id: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict:
        """
        Analyze clause using RAG with multi-agent system.
        
        Args:
            clause: SOP clause text to analyze
            regulator: "all", "BI", or "OJK"
            top_k: Number of articles to retrieve
            clause_id: Optional clause identifier
            use_cache: Whether to use cached results
            
        Returns:
            Audit result dict
        """
        import time
        start_time = time.time()
        request_id = clause_id or f"audit-{int(time.time()*1000)}"
        
        # Check cache
        if use_cache and settings.ENABLE_CACHE:
            cached = self.cache.get(clause, regulator)
            if cached:
                logger.info(f"Cache HIT: {request_id}")
                cached["from_cache"] = True
                return cached
        
        # Check budget
        estimated_cost = cost_tracker.estimate_cost(
            self.llm_model,
            len(clause.split()) * 1.5,
            1000
        )
        stats = cost_tracker.get_today_stats()
        if stats["remaining_usd"] < estimated_cost:
            raise ComplianceAuditError(
                code="BUDGET_EXCEEDED",
                detail=f"Estimated cost ${estimated_cost:.4f} exceeds remaining budget",
                status_code=429
            )
        
        # Try using multi-agent system with RAG
        if self._check_chroma_available():
            try:
                result = await self._analyze_with_multi_agent(
                    clause=clause,
                    regulator=regulator,
                    top_k=top_k,
                    request_id=request_id
                )
            except Exception as e:
                logger.error(f"Multi-agent analysis failed: {e}")
                # Fallback to LLM-only
                result = await self._analyze_llm_only(
                    clause=clause,
                    regulator=regulator,
                    request_id=request_id
                )
        else:
            # LLM-only mode (no ChromaDB data)
            result = await self._analyze_llm_only(
                clause=clause,
                regulator=regulator,
                request_id=request_id
            )
        
        # Add metadata
        result["request_id"] = request_id
        result["clause_id"] = clause_id
        result["clause"] = clause
        result["regulator"] = regulator
        result["latency_ms"] = int((time.time() - start_time) * 1000)
        result["model_used"] = self.llm_model
        result["from_cache"] = False
        
        # Cache the result
        if use_cache and settings.ENABLE_CACHE:
            self.cache.set(clause, regulator, result)
        
        return result
    
    async def _analyze_with_multi_agent(
        self,
        clause: str,
        regulator: str,
        top_k: int,
        request_id: str
    ) -> Dict:
        """
        Analyze using multi-agent system with RAG.
        
        This method uses the full multi-agent pipeline:
        1. Retrieve relevant articles from ChromaDB
        2. Run BI specialist agent
        3. Run OJK specialist agent
        4. Resolve conflicts between regulators
        """
        logger.info(f"[{request_id}] Running multi-agent analysis with RAG")
        
        coordinator = self._get_coordinator()
        
        # Run async audit using coordinator
        result = await coordinator.audit_clause_async(
            clause=clause,
            clause_id=request_id,
            context={"regulator": regulator, "top_k": top_k}
        )
        
        # Convert AuditResult to dict format
        return {
            "final_status": result.final_verdict.final_status if result.final_verdict else "UNCLEAR",
            "overall_confidence": result.final_verdict.overall_confidence if result.final_verdict else 0.5,
            "risk_score": self._calculate_risk_score(result),
            "bi_verdict": result.bi_verdict if regulator in ["all", "BI"] else None,
            "ojk_verdict": result.ojk_verdict if regulator in ["all", "OJK"] else None,
            "violations": self._extract_violations(result),
            "recommendations": result.final_verdict.recommendations if result.final_verdict else [],
            "evidence_trail": self._build_evidence_trail(result),
            "analysis_mode": "multi_agent_rag"
        }
    
    async def _analyze_llm_only(
        self,
        clause: str,
        regulator: str,
        request_id: str
    ) -> Dict:
        """
        Analyze using LLM only (fallback when ChromaDB is empty).
        
        This is a simplified analysis without RAG context.
        """
        logger.info(f"[{request_id}] Running LLM-only analysis (no RAG)")
        
        prompt = self._build_llm_prompt(clause, regulator)
        
        response = self.openai_client.chat.completions.create(
            model=self.llm_model,
            messages=[
                {
                    "role": "system",
                    "content": """Anda adalah asisten audit kepatuhan regulasi untuk sistem pembayaran digital di Indonesia.
                    Anda memiliki pengetahuan tentang regulasi BI dan OJK terkait e-wallet, termasuk:
                    - PBI No. 23/6/2021 tentang Penyelenggaraan Aktvitas Pembayaran
                    - POJK No. 22/POJK.05/2023 tentang Penyelenggaraan Aktivitas Jasa Keuangan Digital
                    
                    Berikan analisis yang akurat berdasarkan pengetahuan regulasi Anda."""
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        
        # Track token usage
        if response.usage:
            cost_tracker.record_usage(
                model=self.llm_model,
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                endpoint="chat.completions",
                clause_id=request_id
            )
        
        llm_response = response.choices[0].message.content or ""
        
        # Parse the LLM response to extract verdict
        verdict = self._parse_llm_response(llm_response, regulator)
        
        return {
            "final_status": verdict["status"],
            "overall_confidence": verdict["confidence"],
            "risk_score": 1 - verdict["confidence"],
            "bi_verdict": verdict if regulator in ["all", "BI"] else None,
            "ojk_verdict": verdict if regulator in ["all", "OJK"] else None,
            "violations": verdict.get("violations", []),
            "recommendations": verdict.get("recommendations", []),
            "evidence_trail": [],
            "reasoning": llm_response,
            "analysis_mode": "llm_only"
        }
    
    def _build_llm_prompt(self, clause: str, regulator: str) -> str:
        """Build prompt for LLM-only analysis."""
        regulator_context = {
            "BI": "Bank Indonesia (PBI, SEBI)",
            "OJK": "Otoritas Jasa Keuangan (POJK, SEOJK)",
            "all": "Bank Indonesia dan OJK"
        }.get(regulator, "Bank Indonesia dan OJK")
        
        return f"""Analisis klausa SOP berikut untuk kepatuhan regulasi {regulator_context}:

KLAUSA SOP:
{clause}

INSTRUKSI ANALISIS:
1. Tentukan status kepatuhan:
   - COMPLIANT: Klausa memenuhi semua regulasi yang berlaku
   - NON_COMPLIANT: Klausa melanggar regulasi
   - PARTIALLY_COMPLIANT: Sebagian memenuhi, ada aspek yang perlu diperbaiki
   - UNCLEAR: Tidak dapat ditentukan dari informasi yang ada

2. Jika NON_COMPLIANT atau PARTIALLY_COMPLIANT:
   - Identifikasi pasal regulasi yang dilanggar
   - Jelaskan ketidaksesuaian
   - Berikan rekomendasi perbaikan

3. Berikan confidence score (0.0-1.0) berdasarkan kepastian analisis

4. Untuk e-wallet, perhatikan regulasi spesifik:
   - Saldo maksimal akun unverified: Rp 2.000.000 (BI)
   - Saldo maksimal akun verified: Rp 10.000.000 (BI)
   - Batas transaksi bulanan: Rp 20.000.000 (BI/OJK)
   - KYC dan verifikasi identitas (BI/OJK)
   - Perlindungan konsumen (OJK)

RESPON DALAM FORMAT JSON:
{{
    "status": "COMPLIANT|NON_COMPLIANT|PARTIALLY_COMPLIANT|UNCLEAR",
    "confidence": 0.0-1.0,
    "violations": ["..."],
    "recommendations": ["..."],
    "relevant_regulations": ["..."],
    "reasoning": "..."
}}"""
    
    def _parse_llm_response(self, response: str, regulator: str) -> Dict:
        """Parse LLM response to extract structured verdict."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return {
                    "status": data.get("status", "UNCLEAR"),
                    "confidence": float(data.get("confidence", 0.5)),
                    "violations": data.get("violations", []),
                    "recommendations": data.get("recommendations", []),
                    "reasoning": data.get("reasoning", response[:500]),
                    "relevant_articles": data.get("relevant_regulations", [])
                }
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Fallback: simple status detection
        response_lower = response.lower()
        
        if any(word in response_lower for word in ["melanggar", "tidak memenuhi", "non-compliant", "violates"]):
            status = "NON_COMPLIANT"
            confidence = 0.7
        elif any(word in response_lower for word in ["memenuhi", "sesuai", "compliant", "patuh"]):
            status = "COMPLIANT"
            confidence = 0.7
        elif any(word in response_lower for word in ["sebagian", "partial", "perlu perbaikan"]):
            status = "PARTIALLY_COMPLIANT"
            confidence = 0.6
        else:
            status = "UNCLEAR"
            confidence = 0.5
        
        return {
            "status": status,
            "confidence": confidence,
            "violations": [],
            "recommendations": [],
            "reasoning": response[:500],
            "relevant_articles": []
        }
    
    def _calculate_risk_score(self, result) -> str:
        """Calculate risk score from audit result."""
        if result.final_verdict:
            violations = len(result.final_verdict.regulatory_conflicts)
            status = result.final_verdict.final_status
            
            if status == "NON_COMPLIANT" or violations >= 2:
                return "HIGH"
            elif status == "PARTIALLY_COMPLIANT" or violations == 1:
                return "MEDIUM"
            elif status == "UNCLEAR":
                return "MEDIUM"
            else:
                return "LOW"
        return "LOW"
    
    def _extract_violations(self, result) -> List[str]:
        """Extract violations from audit result."""
        violations = []
        if result.final_verdict:
            for conflict in result.final_verdict.regulatory_conflicts:
                violations.append(f"{conflict.type}: {conflict.description}")
        return violations
    
    def _build_evidence_trail(self, result) -> List[Dict]:
        """Build evidence trail from audit result."""
        evidence = []
        
        if result.bi_verdict:
            evidence.append({
                "agent": "BI_SPECIALIST",
                "status": result.bi_verdict.get("verdict", "UNKNOWN"),
                "confidence": result.bi_verdict.get("confidence_score", 0),
                "reasoning": result.bi_verdict.get("reasoning_trace", "")[:200]
            })
        
        if result.ojk_verdict:
            evidence.append({
                "agent": "OJK_SPECIALIST",
                "status": result.ojk_verdict.get("verdict", "UNKNOWN"),
                "confidence": result.ojk_verdict.get("confidence_score", 0),
                "reasoning": result.ojk_verdict.get("reasoning_trace", "")[:200]
            })
        
        return evidence


# Singleton instance
_rag_service = None


def get_rag_service() -> RAGAuditService:
    """Get or create singleton RAG service."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGAuditService()
    return _rag_service