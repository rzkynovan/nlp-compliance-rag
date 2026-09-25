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

    Fungsi resolusi (Persamaan 2.26 proposal):

        c_hat = Phi(v_BI, v_OJK) = v_BI                      jika v_BI == v_OJK
                                  = argmax_{v in {v_BI, v_OJK}} pi(v)   jika berbeda

    Fungsi prioritas ordinal pi (Subbab 3.5.5):
      1. Hierarki peraturan UU > PP > PBI/POJK > SE — PBI dan POJK setara,
         sehingga asas ini tidak membedakan kedua verdik pada korpus penelitian.
      2. Perlindungan konsumen: OJK diutamakan untuk aspek hak konsumen.
      3. Stabilitas moneter: BI diutamakan untuk aspek transaksional.
      4. Standar ketat: jika overlap, terapkan standar yang lebih ketat.

    Prinsip 4 dioperasionalkan sebagai urutan keparahan STATUS_PRIORITY
    (verdik yang lebih ketat menang). Prinsip 2 dan 3 menentukan regulator
    utama (primary_regulator) yang pasal & rekomendasinya didahulukan, karena
    status akhir sudah ditetapkan oleh prinsip 4.
    """

    # pi(v): semakin besar semakin ketat / berisiko
    STATUS_PRIORITY = {
        "NON_COMPLIANT":       6,
        "PARTIALLY_COMPLIANT": 5,
        "NEEDS_REVIEW":        4,
        "COMPLIANT":           3,
        "NOT_ADDRESSED":       2,
        "UNCLEAR":             1,
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
        "STRICTER_STANDARD": {
            "priority": "Apply stricter standard",
            "basis": "Principles of regulatory compliance",
            "applies_to": ["ALL"]
        }
    }

    def __init__(self):
        self.name = "CONFLICT_RESOLVER"

    @staticmethod
    def _norm(status) -> str:
        s = str(status).upper().replace("-", "_").strip() if status else "UNCLEAR"
        return s if s in ConflictResolverAgent.STATUS_PRIORITY else "NEEDS_REVIEW"

    def validate_verdict(self, verdict: Dict) -> str:
        """
        Validasi konsistensi keluaran agen sebelum Phi diterapkan:
        PARTIALLY_COMPLIANT tanpa pelanggaran DAN tanpa sub-elemen yang hilang
        tidak didukung bukti → diturunkan ke COMPLIANT.
        """
        status = self._norm(verdict.get("verdict"))
        if status == "PARTIALLY_COMPLIANT" and not verdict.get("violated_articles") \
                and not verdict.get("missing_elements"):
            return "COMPLIANT"
        return status

    def phi(self, v_bi: str, v_ojk: str) -> str:
        """Persamaan 2.26."""
        if v_bi == v_ojk:
            return v_bi
        return max((v_bi, v_ojk), key=lambda v: self.STATUS_PRIORITY[v])

    @staticmethod
    def primary_regulator(clause_category: Optional[str]) -> str:
        """Prinsip 2 & 3: regulator yang pasal/rekomendasinya didahulukan."""
        if clause_category == "OJK_PRIORITY":
            return "OJK"
        if clause_category == "BI_PRIORITY":
            return "BI"
        return "BALANCED"

    def resolve(
        self,
        bi_verdict: Dict,
        ojk_verdict: Dict,
        clause_category: str = None
    ) -> FinalVerdict:
        """
        Resolusi dua verdik (regulator = BI + OJK).

        Args:
            bi_verdict: Verdict dari BI Specialist Agent
            ojk_verdict: Verdict dari OJK Specialist Agent
            clause_category: "BI_PRIORITY" | "OJK_PRIORITY" | "BALANCED"

        Returns:
            FinalVerdict dengan status final dan rekomendasi
        """
        v_bi = self.validate_verdict(bi_verdict)
        v_ojk = self.validate_verdict(ojk_verdict)
        final_status = self.phi(v_bi, v_ojk)

        conflicts = self._detect_conflicts(bi_verdict, ojk_verdict)
        primary = self.primary_regulator(clause_category)
        confidence = self._calculate_confidence(bi_verdict, ojk_verdict)
        recommendations = self._generate_recommendations(bi_verdict, ojk_verdict, primary)
        risk_score = self._calculate_risk(bi_verdict, ojk_verdict, conflicts)
        evidence_matrix = self._build_evidence_matrix(bi_verdict, ojk_verdict)
        evidence_matrix["resolution"] = {
            "v_bi": v_bi, "v_ojk": v_ojk, "final": final_status,
            "primary_regulator": primary,
        }

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

    def resolve_single(self, verdict: Dict, regulator: str) -> FinalVerdict:
        """
        Regulator target tunggal (BI Only / OJK Only, Step 2 Subbab 3.5.4):
        hanya satu verdik sehingga Phi trivial (c_hat = v).
        """
        empty: Dict = {}
        is_bi = regulator.upper() == "BI"
        bi_verdict = verdict if is_bi else empty
        ojk_verdict = empty if is_bi else verdict
        status = self.validate_verdict(verdict)
        evidence_matrix = self._build_evidence_matrix(bi_verdict, ojk_verdict)
        evidence_matrix["resolution"] = {"single_regulator": regulator.upper(), "final": status}
        return FinalVerdict(
            final_status=status,
            overall_confidence=round(float(verdict.get("confidence_score", 0.5)), 2),
            regulatory_conflicts=[],
            evidence_matrix=evidence_matrix,
            risk_score=self._calculate_risk(bi_verdict, ojk_verdict, []),
            recommendations=self._generate_recommendations(bi_verdict, ojk_verdict, regulator.upper()),
            bi_verdict=bi_verdict or None,
            ojk_verdict=ojk_verdict or None,
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
        ojk_verdict: Dict,
        primary: str = "BALANCED",
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

        if primary == "OJK":
            recommendations.sort(key=lambda r: 0 if r.startswith("[OJK]") else 1)
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