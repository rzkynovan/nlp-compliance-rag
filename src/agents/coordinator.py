"""
coordinator.py — Coordinator Agent
===================================
Agent yang mengkoordinasikan eksekusi paralel dari semua specialist agents
dan mengumpulkan hasil untuk dikirim ke Conflict Resolver.
"""

import asyncio
from typing import Dict, Optional
from pathlib import Path
from datetime import datetime

from .bi_specialist import BISpecialistAgent
from .ojk_specialist import OJKSpecialistAgent
from .conflict_resolver import ConflictResolverAgent, FinalVerdict


class AuditResult:
    """
    Container untuk hasil audit multi-agent.
    """
    def __init__(self):
        self.clause_id: str = ""
        self.clause_text: str = ""
        self.timestamp: str = ""
        self.bi_verdict: Dict = {}
        self.ojk_verdict: Dict = {}
        self.final_verdict: Optional[FinalVerdict] = None
        self.execution_time_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "clause_id": self.clause_id,
            "clause_text": self.clause_text,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
            "bi_verdict": self.bi_verdict,
            "ojk_verdict": self.ojk_verdict,
            "final_verdict": self.final_verdict.model_dump() if self.final_verdict else None
        }


class CoordinatorAgent:
    """
    Orchestrates multi-agent compliance audit workflow.
    
    Responsibilities:
    1. Initialize and manage specialist agents
    2. Distribute clause to all agents in parallel
    3. Collect verdicts from each agent
    4. Pass verdicts to Conflict Resolver
    5. Generate final consolidated report
    """
    
    def __init__(self):
        self.name = "COORDINATOR"
        self.bi_agent = BISpecialistAgent()
        self.ojk_agent = OJKSpecialistAgent()
        self.resolver = ConflictResolverAgent()
        self.initialized = False
    
    def initialize(self, api_key: str, chroma_path: Optional[str] = None):
        """
        Initialize all specialist agents.
        """
        if chroma_path is None:
            chroma_path = str(Path(__file__).parent.parent.parent / "data" / "processed" / "chroma_db")
        
        print(f"\n[{self.name}] Initializing specialist agents...")
        
        self.bi_agent.initialize(api_key, chroma_path)
        self.ojk_agent.initialize(api_key, chroma_path)
        
        self.initialized = True
        print(f"[{self.name}] All agents initialized successfully.")
    
    def preprocess_clause(self, clause: str) -> str:
        """
        Clean and preprocess clause text.
        """
        clause = clause.strip()
        
        if clause.startswith("#"):
            clause = clause.lstrip("# ")
        
        return clause
    
    async def _analyze_with_bi(self, clause: str) -> Dict:
        """
        Run BI agent analysis asynchronously.
        """
        return self.bi_agent.analyze(clause).model_dump()
    
    async def _analyze_with_ojk(self, clause: str) -> Dict:
        """
        Run OJK agent analysis asynchronously.
        """
        return self.ojk_agent.analyze(clause).model_dump()
    
    async def audit_clause_async(
        self,
        clause: str,
        clause_id: str = None,
        context: Dict = None
    ) -> AuditResult:
        """
        Run full audit workflow for a single clause asynchronously.
        
        Args:
            clause: Clause text to audit
            clause_id: Optional clause identifier
            context: Optional additional context
        
        Returns:
            AuditResult containing all verdicts and final decision
        """
        if not self.initialized:
            raise RuntimeError("Agents not initialized. Call initialize() first.")
        
        start_time = datetime.now()
        
        result = AuditResult()
        result.clause_text = clause
        result.clause_id = clause_id or f"CLAUSE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        result.timestamp = start_time.isoformat()
        
        processed_clause = self.preprocess_clause(clause)
        
        bi_task = asyncio.create_task(self._analyze_with_bi(processed_clause))
        ojk_task = asyncio.create_task(self._analyze_with_ojk(processed_clause))
        
        result.bi_verdict, result.ojk_verdict = await asyncio.gather(
            bi_task, ojk_task
        )
        
        result.final_verdict = self.resolver.resolve(
            bi_verdict=result.bi_verdict,
            ojk_verdict=result.ojk_verdict,
            clause_category=self._determine_category(clause)
        )
        
        end_time = datetime.now()
        result.execution_time_ms = (end_time - start_time).total_seconds() * 1000
        
        return result
    
    def audit_clause(
        self,
        clause: str,
        clause_id: str = None,
        context: Dict = None
    ) -> AuditResult:
        """
        Synchronous wrapper for audit_clause_async.
        """
        return asyncio.run(self.audit_clause_async(clause, clause_id, context))
    
    async def audit_document_async(
        self,
        clauses: list,
        output_path: str = None
    ) -> list:
        """
        Audit multiple clauses in batch asynchronously.
        
        Args:
            clauses: List of clause dicts with 'text' and optionally 'id'
            output_path: Optional path to save results
        
        Returns:
            List of AuditResult objects
        """
        if not self.initialized:
            raise RuntimeError("Agents not initialized. Call initialize() first.")
        
        results = []
        
        print(f"\n[{self.name}] Starting audit for {len(clauses)} clauses...")
        
        for i, clause_data in enumerate(clauses, 1):
            clause_text = clause_data.get("text", str(clause_data))
            clause_id = clause_data.get("id", f"CLAUSE-{i}")
            
            print(f"\n[{self.name}] Auditing [{i}/{len(clauses)}]: {clause_text[:60]}...")
            
            result = await self.audit_clause_async(clause_text, clause_id)
            results.append(result)
            
            self._print_result_summary(result)
        
        if output_path:
            self._save_results(results, output_path)
        
        print(f"\n[{self.name}] Audit complete. {len(results)} clauses processed.")
        
        return results
    
    def _determine_category(self, clause: str) -> str:
        """
        Determine clause category for conflict resolution priority.
        """
        bi_keywords = ["saldo", "limit", "batas", "transaksi", "settlement", "kyc"]
        ojk_keywords = ["keluhan", "pengaduan", "data pribadi", "hak", "klausula"]
        
        clause_lower = clause.lower()
        
        bi_score = sum(1 for kw in bi_keywords if kw in clause_lower)
        ojk_score = sum(1 for kw in ojk_keywords if kw in clause_lower)
        
        if bi_score > ojk_score:
            return "BI_PRIORITY"
        elif ojk_score > bi_score:
            return "OJK_PRIORITY"
        else:
            return "BALANCED"
    
    def _print_result_summary(self, result: AuditResult):
        """
        Print summary of audit result.
        """
        print(f"   Status: {result.final_verdict.final_status}")
        print(f"   Risk: {result.final_verdict.risk_score}")
        print(f"   Confidence: {result.final_verdict.overall_confidence:.2f}")
        
        if result.final_verdict.violated_articles:
            print(f"   Violations: {len(result.final_verdict.violated_articles)} found")
    
    def _save_results(self, results: list, output_path: str):
        """
        Save results to file.
        """
        import json
        
        output_data = {
            "audit_summary": {
                "total_clauses": len(results),
                "compliant": sum(1 for r in results if r.final_verdict.final_status == "COMPLIANT"),
                "non_compliant": sum(1 for r in results if r.final_verdict.final_status == "NON_COMPLIANT"),
                "needs_review": sum(1 for r in results if r.final_verdict.final_status == "NEEDS_HUMAN_REVIEW"),
                "not_addressed": sum(1 for r in results if r.final_verdict.final_status == "NOT_ADDRESSED"),
            },
            "results": [r.to_dict() for r in results]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[{self.name}] Results saved to: {output_path}")
    
    def generate_report(self, results: list) -> str:
        """
        Generate human-readable report from results.
        """
        report_lines = [
            "=" *60,
            "LAPORAN AUDIT KEPATUHAN REGULASI (MULTI-AGENT)",
            "=" * 60,
            f"Tanggal: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Klausa Diaudit: {len(results)}",
            "",
        ]
        
        compliant = sum(1 for r in results if r.final_verdict.final_status == "COMPLIANT")
        non_compliant = sum(1 for r in results if r.final_verdict.final_status == "NON_COMPLIANT")
        
        report_lines.extend([
            "RINGKASAN:",
            f"   COMPLIANT: {compliant}",
            f"   NON-COMPLIANT: {non_compliant}",
            f"   NEEDS_REVIEW: {len(results) - compliant - non_compliant}",
            "",
            "-" * 60,
            "",
        ])
        
        for i, result in enumerate(results, 1):
            report_lines.extend([
                f"KLAUSA [{i}]: {result.clause_id}",
                f"Teks: {result.clause_text[:100]}...",
                "",
                "HASIL ANALISIS:",
                f"   Status Final: {result.final_verdict.final_status}",
                f"   Confidence: {result.final_verdict.overall_confidence:.2f}",
                f"   Risk Score: {result.final_verdict.risk_score}",
                "",
                "EVIDENCE:",
                f"   [BI] {result.bi_verdict.get('verdict', 'N/A')} ({result.bi_verdict.get('confidence_score', 0):.2f})",
                f"   [OJK] {result.ojk_verdict.get('verdict', 'N/A')} ({result.ojk_verdict.get('confidence_score', 0):.2f})",
                "",
            ])
            
            if result.final_verdict.recommendations:
                report_lines.append("REKOMENDASI:")
                for rec in result.final_verdict.recommendations:
                    report_lines.append(f"   - {rec}")
            
            report_lines.extend(["-" * 60, ""])
        
        return "\n".join(report_lines)