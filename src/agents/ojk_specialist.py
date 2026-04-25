"""
ojk_specialist.py — OJK Specialist Agent
========================================
Agent spesialis untuk menganalisis kepatuhan terhadap regulasi OJK
(POJK, SEOJK) dengan fokus pada perlindungan konsumen dan dispute resolution.
"""

import os
import json
import sys
from typing import Dict, List, Optional
from pathlib import Path

from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

from .base_agent import BaseAgent, AgentVerdict, ViolatedArticle

# Tambahkan src ke path agar retrieval dapat diimport
_SRC_DIR = Path(__file__).resolve().parent.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from retrieval.bm25_retriever import BM25Retriever
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.query_analyzer import QueryAnalyzer


class OJKSpecialistAgent(BaseAgent):
    """
    Specialist Agent untuk regulasi Otoritas Jasa Keuangan.
    
    Fokus audit:
    - Penyelesaian pengaduan konsumen (SLA)
    - Hak-hak konsumen
    - Perlindungan data pribadi
    - Klausula baku yang dilarang
    - Transparansi informasi produk
    """
    
    REGULATORY_FOCUS = [
        "Penyelesaian pengaduan konsumen",
        "Hak-hak konsumen jasa keuangan",
        "Perlindungan data pribadi nasabah",
        "Klausula baku yang dilarang",
        "Transparansi informasi produk",
        "Keadilan perlakuan konsumen"
    ]
    
    COMPLIANCE_RULES = {
        "COMPLAINT_RESOLUTION": {
            "max_days": 20,
            "extension_allowed": True,
            "extension_days": 10,
            "description": "SLA penyelesaian pengaduan"
        },
        "CONSUMER_RIGHTS": [
            "Right to information",
            "Right to complaint",
            "Right to fair treatment",
            "Right to data privacy",
            "Right to compensation"
        ],
        "PROHIBITED_CLAUSES": [
            "Klausula yang membatasi tanggung jawab penyedia layanan",
            "Klausula yang menghapus hak konsumen",
            "Klausula yang memberatkan konsumen secara sepihak",
            "Klausula yang membenarkan penyedia layanan mengubah syarat sepihak"
        ]
    }
    
    def __init__(self):
        super().__init__(
            name="OJK_SPECIALIST",
            regulator="Otoritas Jasa Keuangan (OJK)",
            collection_name="ojk_regulations"
        )
    
    def initialize(self, api_key: str, chroma_path: Optional[str] = None):
        """
        Inisialisasi komponen untuk OJK Specialist.
        """
        if chroma_path is None:
            chroma_path = str(Path(__file__).parent.parent.parent / "data" / "processed" / "chroma_db")
        
        self.llm = OpenAI(
            model="gpt-4o",
            api_key=api_key,
            temperature=0.1
        )
        
        Settings.embed_model = OpenAIEmbedding(
            model="text-embedding-3-large",
            api_key=api_key
        )
        
        try:
            db = chromadb.PersistentClient(path=chroma_path)
            collection = db.get_collection(self.collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            self.index = VectorStoreIndex.from_vector_store(vector_store)
            print(f"[{self.name}] Collection '{self.collection_name}' loaded: {collection.count()} vectors")
        except Exception as e:
            print(f"[{self.name}] Warning: Could not load vector store: {e}")
            self.index = None

        # Inisialisasi hybrid retriever (BM25 + dense)
        bm25_path = str(
            Path(chroma_path).parent / "bm25_index" / self.collection_name
        )
        bm25 = BM25Retriever(index_path=bm25_path)
        if bm25.load_index() and self.index is not None:
            self.hybrid_retriever = HybridRetriever(self.index, bm25)
            print(f"[{self.name}] Hybrid retriever aktif (dense + BM25)")
        else:
            self.hybrid_retriever = None
            print(f"[{self.name}] Hybrid retriever tidak tersedia, menggunakan dense only")

        self.query_analyzer = QueryAnalyzer()

    def retrieve_relevant_articles(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Retrieve top-k articles. Gunakan hybrid (dense + BM25) jika query
        mengandung identifier spesifik (nomor pasal, kode regulasi).
        """
        if self.index is None:
            return []

        # Analisis intent query
        if self.query_analyzer and self.hybrid_retriever:
            intent = self.query_analyzer.analyze(query)
            if intent.is_specific:
                results = self.hybrid_retriever.retrieve(query, intent, top_k)
                return [
                    {
                        "content":  r["content"],
                        "metadata": r["metadata"],
                        "score":    r["score"],
                        "retrieval_source": r.get("source", "hybrid"),
                    }
                    for r in results
                ]

        # Fallback: dense only
        retriever = self.index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        return [
            {
                "content":  node.get_content(),
                "metadata": node.metadata,
                "score":    node.score if hasattr(node, 'score') else 1.0,
                "retrieval_source": "dense",
            }
            for node in nodes
        ]
    
    def analyze(self, clause: str, context: Optional[Dict] = None) -> AgentVerdict:
        """
        Main analysis pipeline for OJK regulations.
        """
        category = self.categorize_clause(clause)
        
        search_query = f"{category}: {clause}"
        
        articles = self.retrieve_relevant_articles(search_query)
        
        if not articles:
            return AgentVerdict(
                agent_id=self.name,
                regulator=self.regulator,
                verdict="NOT_ADDRESSED",
                confidence_score=0.3,
                violated_articles=[],
                retrieved_context="Tidak ada regulasi OJK yang relevan ditemukan.",
                reasoning_trace="Tidak dapat menemukan konteks regulasi untuk klausa ini.",
                risk_level="LOW",
                recommendations=["Perlu verifikasi manual oleh auditor OJK."]
            )
        
        prompt = self.build_prompt(clause, articles)
        response = self.llm.complete(prompt)
        parsed = self.parse_llm_response(response.text)
        
        violated_articles = []
        for v in parsed.get("violations", []):
            violated_articles.append(ViolatedArticle(
                article=v.get("article", "Unknown"),
                regulation=v.get("regulation", "POJK"),
                violation_detail=v.get("violation", ""),
                required_value=v.get("required"),
                actual_value=v.get("actual"),
                context=v.get("context")
            ))
        
        consumer_impact = self._assess_consumer_impact(clause, parsed)
        
        return AgentVerdict(
            agent_id=self.name,
            regulator=self.regulator,
            verdict=parsed.get("status", "NEEDS_REVIEW"),
            confidence_score=parsed.get("confidence", 0.5),
            violated_articles=violated_articles,
            retrieved_context="\n---\n".join([a["content"] for a in articles]),
            reasoning_trace=parsed.get("reasoning", ""),
            risk_level=parsed.get("risk_level", "MEDIUM"),
            recommendations=parsed.get("recommendations", [])
        )
    
    def build_prompt(self, clause: str, articles: List[Dict]) -> str:
        """
        Build structured prompt for OJK compliance check.
        """
        articles_text = "\n\n".join([
            f"[{a['metadata'].get('regulator', 'OJK')}] {a['content']}"
            for a in articles
        ])
        
        return f"""Kamu adalah Auditor Kepatuhan Regulasi Otoritas Jasa Keuangan (OJK Specialist).

PASAL-PASAL REGULASI OJK YANG RELEVAN (gunakan NAMA REGULASI dan NOMOR PASAL PERSIS dari dokumen ini):
{articles_text}

KLAUSA SOP/T&C YANG DIUJI:
"{clause}"

TUGAS:
1. Analisis apakah klausa SOP mematuhi regulasi OJK di atas
2. Perhatikan khususnya: perlindungan konsumen, SLA pengaduan, klausula baku
3. Evaluasi dampak terhadap hak-hak konsumen
4. Jika tidak patuh, identifikasi pasal yang dilanggar

PENTING untuk field "violations":
- "article": gunakan nomor pasal PERSIS seperti tertulis di dokumen (misal: "Pasal 5 Ayat 2 huruf a")
- "regulation": gunakan nama regulasi PERSIS seperti tertulis di dokumen (misal: "POJK No. 22/POJK.07/2023")
- JANGAN gunakan placeholder seperti "Pasal X" atau "POJK No. XX/XX"

OUTPUT (format JSON wajib, jelaskan dalam Bahasa Indonesia):
{{
    "status": "COMPLIANT/NON_COMPLIANT/PARTIALLY_COMPLIANT/NOT_ADDRESSED",
    "confidence": 0.0-1.0,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "violations": [
        {{
            "article": "[nomor pasal dari dokumen regulasi di atas]",
            "regulation": "[nama regulasi dari dokumen di atas]",
            "violation": "penjelasan detail mengapa klausa SOP melanggar pasal ini dan dampaknya ke konsumen",
            "required": "ketentuan yang diwajibkan oleh pasal tersebut",
            "actual": "kondisi aktual yang tertulis di klausa SOP"
        }}
    ],
    "reasoning": "langkah penalaran detail termasuk analisis dampak ke konsumen",
    "recommendations": ["rekomendasi perbaikan konkret dari sudut pandang perlindungan konsumen"]
}}\
"""
    
    def _assess_consumer_impact(self, clause: str, parsed: Dict) -> str:
        """
        Assess impact level on consumers.
        """
        high_impact_keywords = [
            "denda", "sanksi", "blokir", "batalkan", "hapus",
            "penalti", "kerugian", "tanpa pemberitahuan"
        ]
        
        clause_lower = clause.lower()
        impact_count = sum(1 for kw in high_impact_keywords if kw in clause_lower)
        
        if parsed.get("status") == "NON_COMPLIANT":
            if impact_count >= 2:
                return "HIGH"
            elif impact_count >= 1:
                return "MEDIUM"
        return "LOW"
    
    def categorize_clause(self, clause: str) -> str:
        """
        Override: OJK-specific categories.
        """
        categories = {
            "KOMPLAIN": ["keluhan", "pengaduan", "complain", "dispute", "sengketa", "penyelesaian"],
            "PRIVACY": ["data pribadi", "privasi", "persetujuan", "consent", "hapus data", "hak"],
            "KLAUSULA": ["klausula", "syarat", "ketentuan", "perjanjian", "kontrak"],
            "FEE": ["biaya", "fee", "charge", "potongan", "administrasi", "denda"],
            "TRANSPARANSI": ["informasi", "transparan", "pengungkapan", " disclosures"],
            "GENERAL": []
        }
        
        clause_lower = clause.lower()
        for category, keywords in categories.items():
            if any(kw in clause_lower for kw in keywords):
                return category
        return "GENERAL"