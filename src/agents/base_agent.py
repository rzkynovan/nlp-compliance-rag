"""
base_agent.py — Abstract Base Class untuk Specialist Agents
=============================================================
Mendefinisikan interface standar untuk semua agent specialist
yang akan mewarisi class ini.
"""

import os
import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class ComplianceStatus(str, Enum):
    """Enam kelas kepatuhan (Tabel 3.6 proposal)."""
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    PARTIALLY_COMPLIANT = "PARTIALLY_COMPLIANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_ADDRESSED = "NOT_ADDRESSED"
    UNCLEAR = "UNCLEAR"


VALID_STATUSES = {s.value for s in ComplianceStatus}

# Bobot sparse boost alpha (Persamaan 3.1 proposal)
SPARSE_BOOST_SPECIFIC = 0.7   # klausul menyebut identifikasi regulasi (PBI/POJK/Pasal)
SPARSE_BOOST_SEMANTIC = 0.3   # klausul konseptual

# Strategi retrieval untuk ablation (env RETRIEVAL_STRATEGY):
#   query_aware (default, proposal Pers. 3.1–3.2) | rrf_equal (alpha=0,5) | dense (tanpa BM25)
RETRIEVAL_STRATEGIES = ("query_aware", "rrf_equal", "dense")


def retrieval_strategy() -> str:
    value = os.getenv("RETRIEVAL_STRATEGY", "query_aware").strip().lower()
    return value if value in RETRIEVAL_STRATEGIES else "query_aware"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ViolatedArticle(BaseModel):
    article: str
    regulation: str
    violation_detail: str
    required_value: Optional[str] = None
    actual_value: Optional[str] = None
    context: Optional[str] = None
    # True jika pasal yang dikutip LLM ada di Top-K chunk hasil retrieval
    # (evidence trail ⊆ Top-K(R, q), Subbab 3.2.4). None = tidak dapat diperiksa.
    grounded: Optional[bool] = None


class AgentVerdict(BaseModel):
    agent_id: str
    regulator: str
    verdict: str
    confidence_score: float
    violated_articles: List[ViolatedArticle]
    retrieved_context: str
    reasoning_trace: str
    risk_level: str = "MEDIUM"
    recommendations: List[str] = []
    # Checklist fields — populated when PARTIALLY_COMPLIANT via coverage gap
    checklist_topic: Optional[str] = None
    checklist_covered: List[str] = []
    missing_elements: List[str] = []
    # Evidence trail — chunk Top-K beserta posisi hierarki & relevance_score (Subbab 3.3.3)
    evidence: List[Dict] = []
    retrieval_mode: str = "dense"            # "hybrid" (RRF berbobot) | "dense" (tanpa BM25 index)
    sparse_boost: Optional[float] = None     # alpha yang dipakai (Persamaan 3.1)


class BaseAgent(ABC):
    """
    Abstract base class untuk semua specialist agent.
    Setiap agent harus mengimplementasikan metode analyze() dan retrieve_relevant_articles().
    """
    
    def __init__(self, name: str, regulator: str, collection_name: str):
        self.name = name
        self.regulator = regulator
        self.collection_name = collection_name
        self.llm = None
        self.embed_model = None
        self.index = None
        # Hybrid retrieval — diinisialisasi di subclass jika BM25 index tersedia
        self.hybrid_retriever = None
        self.query_analyzer   = None
    
    @abstractmethod
    def initialize(self, api_key: str, chroma_path: str):
        """
        Inisialisasi komponen: LLM, Embedding Model, dan Vector Store Index.
        Harus dipanggil sebelum analyze().
        """
        pass
    
    def select_sparse_boost(self, query: str) -> float:
        """Persamaan 3.1: alpha = 0,7 jika ada identifikasi regulasi, 0,3 jika tidak."""
        if retrieval_strategy() == "rrf_equal":
            return 0.5
        if self.query_analyzer is not None and self.query_analyzer.analyze(query).is_specific:
            return SPARSE_BOOST_SPECIFIC
        return SPARSE_BOOST_SEMANTIC

    def retrieve_relevant_articles(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve Top-K(R_regulator, q).

        Jika BM25 index tersedia → weighted RRF (Persamaan 3.2) SELALU dijalankan,
        dengan alpha dari select_sparse_boost(). Jika tidak → dense-only.
        Mengembalikan list of dicts: content, metadata, score, relevance_score,
        retrieval_source ("hybrid" | "dense"), found_in, alpha.
        """
        if self.index is None:
            return []

        if self.hybrid_retriever is not None and retrieval_strategy() != "dense":
            alpha = self.select_sparse_boost(query)
            results = self.hybrid_retriever.retrieve_weighted(query, alpha=alpha, top_k=top_k)
            return [
                {
                    "content":          r["content"],
                    "metadata":         r["metadata"],
                    "score":            r["score"],
                    "relevance_score":  r.get("relevance_score", 0.0),
                    "retrieval_source": "hybrid",
                    "found_in":         r.get("source", "hybrid"),
                    "alpha":            alpha,
                }
                for r in results
            ]

        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        results = []
        for node in nodes:
            score = float(node.score) if getattr(node, "score", None) is not None else 0.0
            results.append({
                "content":          node.get_content(),
                "metadata":         node.metadata,
                "score":            score,
                "relevance_score":  round(max(0.0, min(1.0, score)), 4),
                "retrieval_source": "dense",
                "found_in":         "dense",
                "alpha":            None,
            })
        return results

    @staticmethod
    def build_evidence(articles: List[Dict], snippet_chars: int = 400) -> List[Dict]:
        """Bangun evidence trail dari chunk Top-K (struktur Subbab 3.3.3)."""
        evidence = []
        for rank, a in enumerate(articles, start=1):
            md = a.get("metadata", {}) or {}
            pasal = md.get("pasal") or (f"Pasal {md['pasal_number']}" if md.get("pasal_number") else "")
            ayat = md.get("ayat") or (f"Ayat {md['ayat_number']}" if md.get("ayat_number") else "")
            evidence.append({
                "rank":            rank,
                "regulator":       md.get("regulation_type") or md.get("regulator", ""),
                "regulation":      md.get("document") or md.get("regulation_code", ""),
                "bab":             md.get("bab", ""),
                "bagian":          md.get("bagian", ""),
                "article":         " ".join(x for x in (pasal, ayat) if x),
                "pasal_number":    str(md.get("pasal_number", "") or ""),
                "article_text":    (a.get("content") or "")[:snippet_chars],
                "relevance_score": float(a.get("relevance_score", 0.0) or 0.0),
                "found_in":        a.get("found_in", a.get("retrieval_source", "")),
            })
        return evidence

    @staticmethod
    def verify_citations(violations: List["ViolatedArticle"], evidence: List[Dict]) -> List["ViolatedArticle"]:
        """
        Tandai setiap pelanggaran: apakah nomor pasal yang dikutip LLM ada di
        Top-K chunk hasil retrieval. Pasal yang tidak ada → grounded=False
        (indikasi halusinasi sitasi).
        """
        retrieved = {e["pasal_number"] for e in evidence if e.get("pasal_number")}
        for v in violations:
            m = re.search(r"Pasal\s+(\d+[A-Z]?)", v.article or "", re.IGNORECASE)
            if not m or not retrieved:
                v.grounded = None
            else:
                v.grounded = m.group(1) in retrieved
        return violations

    @staticmethod
    def normalize_status(status) -> str:
        s = str(status or "").upper().replace("-", "_").strip()
        return s if s in VALID_STATUSES else "NEEDS_REVIEW"
    
    @abstractmethod
    def analyze(self, clause: str, context: Optional[Dict] = None) -> AgentVerdict:
        """
        Analyze a clause and return compliance verdict.
        Main pipeline: retrieve -> reason -> verdict.
        """
        pass
    
    @abstractmethod
    def build_prompt(self, clause: str, articles: List[Dict]) -> str:
        """
        Build structured prompt for LLM based on retrieved articles.
        """
        pass
    
    def parse_llm_response(self, response: str) -> Dict:
        """
        Parse LLM JSON response into structured dict.
        Normalises field types: reasoning must be str, list fields must be list.
        """
        import json
        parsed = None
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                parsed = json.loads(json_str)
        except json.JSONDecodeError:
            pass

        if parsed is None:
            return {
                "status": "NEEDS_REVIEW",
                "confidence": 0.5,
                "violations": [],
                "reasoning": response,
                "risk_level": "MEDIUM",
                "checklist_topic": None,
                "checklist_covered": [],
                "missing_elements": [],
            }

        # Normalise: reasoning must be a plain string (model sometimes returns list)
        for key in ("reasoning", "reasoning_trace"):
            if key in parsed and not isinstance(parsed[key], str):
                val = parsed[key]
                parsed[key] = " ".join(val) if isinstance(val, list) else str(val)

        # Normalise: list fields must actually be lists
        for key in ("violations", "recommendations", "checklist_covered", "missing_elements"):
            if key in parsed and not isinstance(parsed[key], list):
                parsed[key] = [parsed[key]] if parsed[key] else []

        return parsed
    
    def categorize_clause(self, clause: str) -> str:
        """
        Classify clause category based on keywords.
        Override this for agent-specific categories.
        """
        categories = {
            "SALDO": ["saldo", "limit", "batas", "maksimal", "minimum"],
            "TRANSAKSI": ["transaksi", "transfer", "tarik", "setor", "pembayaran"],
            "KYC": ["kyc", "verifikasi", "identitas", "ktp", "ektp", "data diri"],
            "KOMPLAIN": ["keluhan", "pengaduan", "complain", "dispute", "sengketa"],
            "PRIVACY": ["data pribadi", "privasi", "persetujuan", "consent", "hapusk data"],
            "FEE": ["biaya", "fee", "charge", "potongan", "administrasi"],
            "GENERAL": []
        }
        
        clause_lower = clause.lower()
        for category, keywords in categories.items():
            if any(kw in clause_lower for kw in keywords):
                return category
        return "GENERAL"
    
    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}' regulator='{self.regulator}'>"