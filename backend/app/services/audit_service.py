import logging
import time
import json
from typing import Optional
from datetime import datetime
from uuid import uuid4

from openai import OpenAI
from app.config import settings
from app.core.cache import AuditCache
from app.core.cost_tracker import cost_tracker
from app.core.exceptions import ComplianceAuditError

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.cache = AuditCache(
            cache_dir="./data/cache",
            ttl_hours=settings.CACHE_TTL_HOURS
        )
        self.llm_model = settings.LLM_MODEL
        self.top_k = settings.RETRIEVAL_TOP_K
        self.budget_limit = settings.DAILY_BUDGET_LIMIT_USD
        
    def _estimate_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.3)
        
    def _check_budget(self) -> bool:
        stats = cost_tracker.get_today_stats()
        if stats["remaining_usd"] <= 0:
            logger.warning(f"Budget exceeded: ${stats['total_cost_usd']:.2f} / ${self.budget_limit:.2f}")
            return False
        return True
    
    def _call_llm(
        self, 
        prompt: str, 
        temperature: float = 0.1,
        clause_id: Optional[str] = None
    ) -> str:
        if not self._check_budget():
            raise ComplianceAuditError(
                code="BUDGET_EXCEEDED",
                detail=f"Daily budget limit of ${self.budget_limit} exceeded",
                status_code=429
            )
        
        estimated_tokens = self._estimate_tokens(prompt) + 1000
        
        try:
            response = self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "Anda adalah asisten audit kepatuhan regulasi. Analisis klausa SOP dan berikan verdict kepatuhan berdasarkan regulasi yang disediakan."},
                    {"role": "user", "content": prompt}
                ],
                temperature=temperature,
            )
            
            if response.usage:
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
            else:
                input_tokens = self._estimate_tokens(prompt)
                output_tokens = 500
            
            cost_tracker.record_usage(
                model=self.llm_model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                endpoint="chat.completions",
                clause_id=clause_id
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise ComplianceAuditError(
                code="LLM_ERROR",
                detail=f"LLM call failed: {str(e)}",
                status_code=500
            )
    
    async def analyze_sop(
        self,
        clause: str,
        regulator: str = "all",
        top_k: int = 5,
        clause_id: Optional[str] = None,
        context: Optional[str] = None,
        use_cache: bool = True,
        enable_tracking: bool = True
    ) -> dict:
        if use_cache and settings.ENABLE_CACHE:
            cached_result = self.cache.get(clause, regulator)
            if cached_result:
                logger.info(f"Cache HIT for clause: {clause[:50]}...")
                return cached_result
        
        request_id = str(uuid4())
        start_time = time.time()
        
        estimated_cost = cost_tracker.estimate_cost(
            self.llm_model,
            self._estimate_tokens(clause),
            1000
        )
        
        if not self._check_budget():
            raise ComplianceAuditError(
                code="BUDGET_EXCEEDED",
                detail=f"Estimated cost ${estimated_cost:.4f} exceeds remaining budget",
                status_code=429
            )
        
        prompt = f"""
Analisis klausa SOP berikut untuk kepatuhan regulasi:

Klausa: {clause}
Regulator: {regulator}
Konteks tambahan: {context or 'Tidak ada'}

Berikan:
1. Status kepatuhan (COMPLIANT / NON_COMPLIANT / PARTIALLY_COMPLIANT / UNCLEAR)
2. Tingkat kepercayaan (0.0 - 1.0)
3. Pasal regulasi yang relevan
4. Rekomendasi perbaikan
"""
        
        llm_response = self._call_llm(prompt, clause_id=clause_id or request_id)
        
        verdict = {
            "status": "UNCLEAR",
            "confidence": 0.7,
            "reasoning": llm_response,
            "relevant_articles": [],
            "recommendations": []
        }
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        result = {
            "request_id": request_id,
            "clause": clause,
            "clause_id": clause_id,
            "regulator": regulator,
            "final_status": verdict["status"],
            "overall_confidence": verdict["confidence"],
            "risk_score": 1 - verdict["confidence"],
            "bi_verdict": verdict if regulator in ["all", "BI"] else None,
            "ojk_verdict": verdict if regulator in ["all", "OJK"] else None,
            "violations": [],
            "recommendations": verdict["recommendations"],
            "evidence_trail": [],
            "latency_ms": latency_ms,
            "model_used": self.llm_model,
            "from_cache": False
        }
        
        if use_cache and settings.ENABLE_CACHE:
            self.cache.set(clause, regulator, result)
        
        logger.info(f"Audit completed: {request_id}, status={verdict['status']}, latency={latency_ms}ms")
        
        return result
        
    async def batch_analyze(
        self,
        clauses: list[dict],
        regulator: str = "all"
    ) -> list[dict]:
        results = []
        total_estimated_cost = 0
        
        for clause_data in clauses:
            estimated_tokens = self._estimate_tokens(clause_data.get("clause", ""))
            total_estimated_cost += cost_tracker.estimate_cost(
                self.llm_model, 
                estimated_tokens
            )
        
        stats = cost_tracker.get_today_stats()
        if stats["remaining_usd"] < total_estimated_cost:
            raise ComplianceAuditError(
                code="BUDGET_EXCEEDED",
                detail=f"Batch would cost ${total_estimated_cost:.4f}, but only ${stats['remaining_usd']:.4f} remaining",
                status_code=429
            )
        
        for clause_data in clauses:
            result = await self.analyze_sop(
                clause=clause_data.get("clause", ""),
                regulator=regulator,
                clause_id=clause_data.get("clause_id"),
                context=clause_data.get("context"),
                use_cache=True,
                enable_tracking=False
            )
            results.append(result)
        return results
    
    def get_usage_stats(self) -> dict:
        return {
            "today": cost_tracker.get_today_stats(),
            "monthly": cost_tracker.get_monthly_stats(),
            "cache_stats": self.cache.get_stats()
        }