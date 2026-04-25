"""
conflict_resolver.py — Conflict Resolution Agent
==================================================
Agent yang bertugas menyelesaikan konflik antara verdict dari berbagai
specialist agents dan menghasilkan keputusan final.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel
from enum import Enum


class ConflictType(str, Enum):
    DIRECT_CONFLICT = "DIRECT_CONFLICT"
    OVERLAP = "OVERLAP"
    GAP = "GAP"
    NO_CONFLICT = "NO_CONFLICT"


class ConflictedRegulation(BaseModel):
    type: str
    description: str
    bi_stance: str
    ojk_stance: str
    resolution: str
    resolution_basis: str


class FinalVerdict(BaseModel):
    final_status: str
    overall_confidence: float
    regulatory_conflicts: List[ConflictedRegulation]
    evidence_matrix: Dict
    risk_score: str
    recommendations: List[str]
    bi_verdict: Optional[Dict] = None
    ojk_verdict: Optional[Dict] = None


class ConflictResolverAgent:
    """
    Menyelesaikan konflik antar-regulator dan menghasilkan verdict final.
    
    Prinsip resolusi:
    1. Hierarki Peraturan: UU > PP > PBI/POJK > SE
    2. Perlindungan Konsumen: OJK diutamakan untuk hak konsumen
    3. Stabilitas Moneter: BI diutamakan untuk aspek transaksional
    4. Standar Ketat: Ambil standar yang lebih ketat jika overlap
    """
    
    HIERARCHY = {
        "UU": 1,
        "PP": 2,
        "PERATURAN_LENGKAP": 3,  
        "SE": 4  
    }
    
    RESOLUTION_PRINCIPLES = {
        "CONSUMER_PROTECTION": {
            "priority": "OJK over BI",
            "basis": "POJK No. 22/2023: Kepentingan konsumen diutamakan",
            "applies_to": ["KOMPLAIN", "PRIVACY", "KLAUSULA", "TRANSPARANSI"]
        },
        "FINANCIAL_STABILITY": {
            "priority": "BI over OJK",
            "basis": "BI sebagai otoritas moneter dan sistem pembayaran",
            "applies_to": ["SALDO", "TRANSAKSI", "KYC", "SETTLEMENT"]
        },
        "STRICHER_STANDARD": {
            "priority": "Apply stricter standard",
            "basis": "Principles of regulatory compliance",
            "applies_to": ["ALL"]
        }
    }
    
    def __init__(self):
        self.name = "CONFLICT_RESOLVER"
    
    def resolve(
        self,
        bi_verdict: Dict,
        ojk_verdict: Dict,
        clause_category: str = None
    ) -> FinalVerdict:
        """
        Main conflict resolution logic.
        
        Args:
            bi_verdict: Verdict dari BI Specialist Agent
            ojk_verdict: Verdict dari OJK Specialist Agent
            clause_category: Kategori klausa (untuk prioritas regulator)
        
        Returns:
            FinalVerdict dengan status final dan rekomendasi
        """
        
        def _norm(s):
            return str(s).upper().replace("-", "_").strip() if s else "UNCLEAR"

        all_statuses = [
            _norm(bi_verdict.get("verdict")),
            _norm(ojk_verdict.get("verdict")),
        ]

        if all(s == "COMPLIANT" for s in all_statuses):
            final_status = "COMPLIANT"
        elif "NON_COMPLIANT" in all_statuses:
            final_status = "NON_COMPLIANT"
        elif all(s in ("NOT_ADDRESSED", "UNCLEAR") for s in all_statuses):
            final_status = "NOT_ADDRESSED"
        elif "PARTIALLY_COMPLIANT" in all_statuses:
            final_status = "PARTIALLY_COMPLIANT"
        else:
            final_status = "NEEDS_REVIEW"
        
        conflicts = self._detect_conflicts(bi_verdict, ojk_verdict)
        
        if conflicts:
            final_status = self._apply_resolution(conflicts, final_status, clause_category)
        
        confidence = self._calculate_confidence(bi_verdict, ojk_verdict)
        
        recommendations = self._generate_recommendations(bi_verdict, ojk_verdict)
        
        risk_score = self._calculate_risk(bi_verdict, ojk_verdict, conflicts)
        
        evidence_matrix = self._build_evidence_matrix(bi_verdict, ojk_verdict)
        
        return FinalVerdict(
            final_status=final_status,
            overall_confidence=confidence,
            regulatory_conflicts=conflicts,
            evidence_matrix=evidence_matrix,
            risk_score=risk_score,
            recommendations=recommendations,
            bi_verdict=bi_verdict,
            ojk_verdict=ojk_verdict
        )
    
    def _detect_conflicts(self, bi_verdict: Dict, ojk_verdict: Dict) -> List[ConflictedRegulation]:
        """
        Detect conflicts between BI and OJK verdicts.
        """
        conflicts = []
        
        bi_status = bi_verdict.get("verdict", "")
        ojk_status = ojk_verdict.get("verdict", "")
        
        if bi_status == "NON_COMPLIANT" and ojk_status == "COMPLIANT":
            conflicts.append(ConflictedRegulation(
                type=ConflictType.OVERLAP.value,
                description="BI mendeteksi pelanggaran, namun OJK menganggap patuh",
                bi_stance=bi_status,
                ojk_stance=ojk_status,
                resolution="Verifikasi manual diperlukan",
                resolution_basis="Perbedaan fokus regulasi antar regulator"
            ))
        
        elif bi_status == "COMPLIANT" and ojk_status == "NON_COMPLIANT":
            conflicts.append(ConflictedRegulation(
                type=ConflictType.OVERLAP.value,
                description="OJK mendeteksi pelanggaran, namun BI menganggap patuh",
                bi_stance=bi_status,
                ojk_stance=ojk_status,
                resolution="Prioritas pada OJK untuk perlindungan konsumen",
                resolution_basis="POJK No. 22/2023: Kepentingan konsumen diutamakan"
            ))
        
        elif bi_status == "NON_COMPLIANT" and ojk_status == "NON_COMPLIANT":
            bi_articles = [v.get("article", "") for v in bi_verdict.get("violated_articles", [])]
            ojk_articles = [v.get("article", "") for v in ojk_verdict.get("violated_articles", [])]
            
            conflicts.append(ConflictedRegulation(
                type=ConflictType.DIRECT_CONFLICT.value,
                description="Kedua regulator mendeteksi pelanggaran dengan pasal berbeda",
                bi_stance=", ".join(bi_articles) if bi_articles else "NON_COMPLIANT",
                ojk_stance=", ".join(ojk_articles) if ojk_articles else "NON_COMPLIANT",
                resolution="Tindak lanjuti semua pelanggaran dari kedua regulator",
                resolution_basis="Compliance harus memenuhi semua regulasi"
            ))
        
        return conflicts
    
    def _apply_resolution(
        self,
        conflicts: List[ConflictedRegulation],
        current_status: str,
        clause_category: str
    ) -> str:
        """
        Apply resolution principles based on clause category.
        """
        if not conflicts:
            return current_status
        
        for conflict in conflicts:
            if conflict.type == ConflictType.OVERLAP.value:
                if "OJK mendeteksi pelanggaran" in conflict.description:
                    return "NON_COMPLIANT"
            
            if conflict.type == ConflictType.DIRECT_CONFLICT.value:
                return "NON_COMPLIANT"
        
        return current_status
    
    def _calculate_confidence(self, bi_verdict: Dict, ojk_verdict: Dict) -> float:
        """
        Calculate weighted average confidence.
        """
        bi_confidence = bi_verdict.get("confidence_score", 0.5)
        ojk_confidence = ojk_verdict.get("confidence_score", 0.5)
        
        weights = {"BI": 0.5, "OJK": 0.5}
        
        total = (bi_confidence * weights["BI"]) + (ojk_confidence * weights["OJK"])
        return round(total, 2)
    
    def _calculate_risk(
        self,
        bi_verdict: Dict,
        ojk_verdict: Dict,
        conflicts: List[ConflictedRegulation]
    ) -> str:
        """
        Calculate overall risk score.
        """
        violation_count = 0
        violation_count += len(bi_verdict.get("violated_articles", []))
        violation_count += len(ojk_verdict.get("violated_articles", []))
        
        has_conflict = len(conflicts) > 0
        
        bi_risk = bi_verdict.get("risk_level", "LOW")
        ojk_risk = ojk_verdict.get("risk_level", "LOW")
        
        risk_levels = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        max_risk = max(risk_levels.get(bi_risk, 1), risk_levels.get(ojk_risk, 1))
        
        if violation_count >= 3 or has_conflict:
            return "CRITICAL"
        elif violation_count >= 2 or max_risk >= 3:
            return "HIGH"
        elif violation_count == 1 or max_risk >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def _generate_recommendations(
        self,
        bi_verdict: Dict,
        ojk_verdict: Dict
    ) -> List[str]:
        """
        Generate actionable recommendations.
        """
        recommendations = []
        
        for violation in bi_verdict.get("violated_articles", []):
            article = violation.get("article", "Unknown")
            required = violation.get("required_value", "")
            actual = violation.get("actual_value", "")
            rec = f"[BI] {article}: Ubah '{actual}' menjadi '{required}'"
            recommendations.append(rec)
        
        for violation in ojk_verdict.get("violated_articles", []):
            article = violation.get("article", "Unknown")
            required = violation.get("required_value", "")
            actual = violation.get("actual_value", "")
            rec = f"[OJK] {article}: Ubah '{actual}' menjadi '{required}'"
            recommendations.append(rec)
        
        for rec in bi_verdict.get("recommendations", []):
            if rec not in recommendations:
                recommendations.append(f"[BI] {rec}")
        
        for rec in ojk_verdict.get("recommendations", []):
            if rec not in recommendations:
                recommendations.append(f"[OJK] {rec}")
        
        return recommendations
    
    def _build_evidence_matrix(
        self,
        bi_verdict: Dict,
        ojk_verdict: Dict
    ) -> Dict:
        """
        Build evidence matrix for transparency.
        """
        return {
            "BI": {
                "status": bi_verdict.get("verdict", "UNKNOWN"),
                "confidence": bi_verdict.get("confidence_score", 0.0),
                "violations": [
                    {
                        "article": v.get("article", ""),
                        "detail": v.get("violation_detail", "")
                    }
                    for v in bi_verdict.get("violated_articles", [])
                ],
                "reasoning": bi_verdict.get("reasoning_trace", "")[:500]
            },
            "OJK": {
                "status": ojk_verdict.get("verdict", "UNKNOWN"),
                "confidence": ojk_verdict.get("confidence_score", 0.0),
                "violations": [
                    {
                        "article": v.get("article", ""),
                        "detail": v.get("violation_detail", "")
                    }
                    for v in ojk_verdict.get("violated_articles", [])
                ],
                "reasoning": ojk_verdict.get("reasoning_trace", "")[:500]
            }
        }