"""
bi_specialist.py — Bank Indonesia Specialist Agent
===================================================
Agent spesialis untuk menganalisis kepatuhan terhadap regulasi BI
(PBI, SEBI) dengan fokus pada aspek transaksional dan moneter.
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


class BISpecialistAgent(BaseAgent):
    """
    Specialist Agent untuk regulasi Bank Indonesia.
    
    Fokus audit:
    - Batas saldo e-wallet (minimum/maximum)
    - Batas transaksi masuk/keluar
    - KYC dan verifikasi identitas
    - Settlement dana
    - Anti-money laundering (AML)
    """
    
    REGULATORY_FOCUS = [
        "Batas saldo e-wallet",
        "Batas transaksi",
        "KYC dan verifikasi",
        "Settlement dana",
        "Anti-money laundering",
        "Penyelenggaraan pembayaran"
    ]
    
    COMPLIANCE_RULES = {
        "SALDO_MAXIMUM": {
            "unverified": {
                "required": 2_000_000,  
                "description": "Saldo maksimal akun unverified (belum KYC)"
            },
            "verified": {
                "required": 10_000_000,  
                "description": "Saldo maksimal akun verified (sudah KYC)"
            }
        },
        "TRANSACTION_LIMITS": {
            "monthly_in": {
                "unverified": 20_000_000,
                "verified": 20_000_000,
                "description": "Batas transaksi masuk bulanan"
            },
            "monthly_out": {
                "unverified": 20_000_000,
                "verified": 20_000_000,
                "description": "Batas transaksi keluar bulanan"
            }
        }
    }
    
    def __init__(self):
        super().__init__(
            name="BI_SPECIALIST",
            regulator="Bank Indonesia (BI)",
            collection_name="bi_regulations"
        )
    
    def initialize(self, api_key: str, chroma_path: Optional[str] = None):
        """
        Inisialisasi komponen untuk BI Specialist.
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
        Main analysis pipeline for BI regulations.
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
                retrieved_context="Tidak ada regulasi BI yang relevan ditemukan.",
                reasoning_trace="Tidak dapat menemukan konteks regulasi untuk klausa ini.",
                risk_level="LOW",
                recommendations=["Perlu verifikasi manual oleh auditor BI."]
            )
        
        prompt = self.build_prompt(clause, articles)
        response = self.llm.complete(prompt)
        parsed = self.parse_llm_response(response.text)
        
        violated_articles = []
        for v in parsed.get("violations", []):
            violated_articles.append(ViolatedArticle(
                article=v.get("article", "Unknown"),
                regulation=v.get("regulation", "PBI"),
                violation_detail=v.get("violation", ""),
                required_value=v.get("required"),
                actual_value=v.get("actual"),
                context=v.get("context")
            ))
        
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
        Build structured prompt for BI compliance check.
        """
        articles_text = "\n\n".join([
            f"[{a['metadata'].get('regulator', 'BI')}] {a['content']}"
            for a in articles
        ])
        
        return f"""Kamu adalah Auditor Kepatuhan Regulasi Bank Indonesia (BI Specialist).

PASAL-PASAL REGULASI BI YANG RELEVAN (gunakan NAMA REGULASI dan NOMOR PASAL PERSIS dari dokumen ini):
{articles_text}

KLAUSA SOP/T&C YANG DIUJI:
"{clause}"

TUGAS:
1. Analisis apakah klausa SOP SECARA EKSPLISIT mengatur topik yang dibahas pasal regulasi di atas
2. Perhatikan khususnya aspek: batas saldo, batas transaksi, KYC, settlement
3. Jika tidak patuh, identifikasi pasal yang dilanggar dengan nomor PERSIS dari dokumen di atas

ATURAN PENTING — BACA SEBELUM MENJAWAB:
a) Gunakan "NOT_ADDRESSED" jika klausa SOP TIDAK MEMBAHAS topik yang diatur pasal BI (misal: klausa tentang data privasi tidak perlu dievaluasi terhadap pasal limit saldo).
b) Gunakan "NON_COMPLIANT" HANYA jika klausa SOP secara AKTIF menetapkan nilai/aturan yang BERTENTANGAN dengan pasal regulasi (misal: SOP menetapkan saldo Rp 10jt padahal BI menetapkan Rp 2jt).
c) Gunakan "COMPLIANT" jika klausa SOP mengatur topik yang sama dan nilainya SESUAI regulasi.
d) Gunakan "PARTIALLY_COMPLIANT" jika sebagian sesuai, sebagian lain melanggar — HANYA jika ada nilai konkret yang bisa dibandingkan.
e) JANGAN laporkan violation karena klausa "tidak menyebutkan" sesuatu — absence of mention ≠ violation.
f) JANGAN gunakan placeholder seperti "Pasal X" atau "PBI No. XX/XX".

PENTING untuk field "violations":
- "article": gunakan nomor pasal PERSIS seperti tertulis di dokumen (misal: "Pasal 160 Ayat 1")
- "regulation": gunakan nama regulasi PERSIS seperti tertulis di dokumen (misal: "PBI No. 23/6/PBI/2021")
- Hanya isi violations[] jika ada pelanggaran AKTIF (nilai/aturan bertentangan), bukan karena tidak disebutkan

OUTPUT (format JSON wajib, jelaskan dalam Bahasa Indonesia):
{{
    "status": "COMPLIANT/NON_COMPLIANT/PARTIALLY_COMPLIANT/NOT_ADDRESSED",
    "confidence": 0.0-1.0,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "violations": [
        {{
            "article": "[nomor pasal dari dokumen regulasi di atas]",
            "regulation": "[nama regulasi dari dokumen di atas]",
            "violation": "penjelasan detail mengapa klausa SOP melanggar pasal ini",
            "required": "nilai atau ketentuan yang diwajibkan oleh pasal tersebut",
            "actual": "nilai atau ketentuan aktual yang tertulis di klausa SOP"
        }}
    ],
    "reasoning": "langkah penalaran detail step-by-step, termasuk apakah klausa relevan dengan topik pasal",
    "recommendations": ["rekomendasi perbaikan konkret 1", "rekomendasi perbaikan konkret 2"]
}}\
"""