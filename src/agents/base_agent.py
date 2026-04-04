"""
base_agent.py — Abstract Base Class untuk Specialist Agents
=============================================================
Mendefinisikan interface standar untuk semua agent specialist
yang akan mewarisi class ini.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    NOT_ADDRESSED = "NOT_ADDRESSED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


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
    
    @abstractmethod
    def initialize(self, api_key: str, chroma_path: str):
        """
        Inisialisasi komponen: LLM, Embedding Model, dan Vector Store Index.
        Harus dipanggil sebelum analyze().
        """
        pass
    
    @abstractmethod
    def retrieve_relevant_articles(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve top-k most relevant articles from vector database.
        Mengembalikan list of dicts dengan: content, metadata, score.
        """
        pass
    
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
        Override this for agent-specific parsing.
        """
        import json
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        return {
            "status": "NEEDS_REVIEW",
            "confidence": 0.5,
            "violations": [],
            "reasoning": response,
            "risk_level": "MEDIUM"
        }
    
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