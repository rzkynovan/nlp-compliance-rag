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


class _AnthropicLLM:
    """Lightweight wrapper agar Anthropic SDK kompatibel dengan llm.complete(prompt).text."""
    def __init__(self, api_key: str, model: str, max_tokens: int = 4096):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model  = model
        self._max_tokens = max_tokens

    def complete(self, prompt: str):
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text

        class _Resp:
            pass
        r = _Resp()
        r.text = text
        return r

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

        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        model    = os.getenv("LLM_MODEL", "gpt-5.4-mini")

        if provider == "anthropic":
            self.llm = _AnthropicLLM(
                api_key=os.getenv("ANTHROPIC_API_KEY", ""),
                model=model,
            )
        else:
            self.llm = OpenAI(
                model=model,
                api_key=api_key,
                temperature=0.1,
            )

        # Embedding selalu pakai OpenAI (ChromaDB dibangun dengan text-embedding-3-large)
        openai_key = api_key if provider != "anthropic" else os.getenv("OPENAI_API_KEY", api_key)
        Settings.embed_model = OpenAIEmbedding(
            model="text-embedding-3-large",
            api_key=openai_key
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
1. Analisis apakah klausa SOP SECARA EKSPLISIT mengatur topik yang dibahas pasal regulasi di atas
2. Perhatikan khususnya: perlindungan konsumen, SLA pengaduan, klausula baku
3. Evaluasi dampak terhadap hak-hak konsumen HANYA jika klausa relevan dengan topik tersebut
4. Jika tidak patuh, identifikasi pasal yang dilanggar

ATURAN PENTING — BACA SEBELUM MENJAWAB:
a) LANGKAH PERTAMA: Tentukan apakah topik klausa SOP relevan dengan fokus OJK. Topik yang relevan: SLA pengaduan, perlindungan konsumen, klausula baku eksonerasi, transparansi informasi, persetujuan konsumen, data privasi. Topik TIDAK relevan untuk OJK: batas saldo teknis, batas transaksi teknis, KYC teknis — ini domain BI.
b) Gunakan "NOT_ADDRESSED" jika klausa SOP TIDAK MEMBAHAS topik yang diatur pasal OJK yang ditemukan. Jangan paksa relevansi hanya karena retrieval mengambil pasal tertentu.
c) Gunakan "NON_COMPLIANT" HANYA jika klausa SOP secara AKTIF menetapkan aturan yang BERTENTANGAN dengan pasal regulasi (misal: SOP menetapkan SLA 60 hari padahal OJK menetapkan maksimal 10 hari kerja).
d) Gunakan "COMPLIANT" jika klausa mengatur topik yang sama dan nilainya SESUAI regulasi.
e) Gunakan "PARTIALLY_COMPLIANT" jika sebagian sesuai, sebagian melanggar — HANYA jika ada ketentuan konkret yang bisa dibandingkan.
f) JANGAN laporkan violation karena klausa "tidak menyebutkan" sesuatu — absence of mention ≠ violation. Aturan ini berlaku bahkan jika klausa SOP membahas topik yang SAMA dengan pasal regulasi. Contoh-contoh BUKAN violation:
   - SOP mengatur prosedur pengaduan tapi tidak menyebutkan "jangka waktu 10 hari melengkapi dokumen" → BUKAN pelanggaran Pasal 71 (SOP tidak melarang pemberian waktu, hanya tidak menyebutkannya). PENGECUALIAN: jika SOP secara eksplisit menyatakan "kami berhak menolak langsung" tanpa memberi kesempatan melengkapi → itu baru konflik aktif.
   - SOP mengatur koreksi saldo tapi tidak menyebutkan "penawaran permintaan maaf atau ganti rugi" → BUKAN pelanggaran Pasal 78 (SOP tidak melarang kompensasi, hanya tidak menyebutkan)
   - SOP mengatur penanganan keluhan tapi tidak menyebutkan "sanksi administratif" → BUKAN violation (sanksi adalah urusan regulator, bukan kewajiban yang harus ditulis di SOP konsumen)
   Violation AKTIF = SOP menetapkan aturan yang BERLAWANAN dengan regulasi: misal SOP menetapkan "SLA pengaduan 60 hari" padahal regulasi menetapkan maksimal 20 hari kerja — ini baru NON_COMPLIANT.
g) JANGAN gunakan placeholder seperti "Pasal X" atau "POJK No. XX/XX".
h) Untuk klausula "kuasa yang tidak dapat ditarik kembali" (irrevocable authority): ini tergolong klausula baku yang dilarang — gunakan Pasal 46 Ayat 2 (bukan Pasal 44 Ayat 3) karena Pasal 46 Ayat 2 secara eksplisit melarang klausula eksonerasi/baku yang memberikan kewenangan sepihak kepada PUJK.
i) JANGAN laporkan violation karena SOP "tidak mencantumkan" kewajiban atau sanksi yang ditujukan kepada PUJK/regulator sendiri. Pasal yang mengatur kewajiban internal PUJK (misal: "PUJK wajib menjaga kerahasiaan data", "sanksi administratif bagi PUJK yang melanggar") BUKAN kewajiban yang harus ditulis ulang di SOP konsumen — SOP tidak harus memuat ulang seluruh isi regulasi. Violation hanya terjadi jika SOP SECARA AKTIF bertentangan, bukan karena tidak meng-copy pasal regulasi.
j) Bedakan antara "klausa tanggung jawab user" dengan "klausula eksonerasi yang dilarang". Klausa yang mewajibkan user menjaga PIN/OTP/keamanan akun sendiri adalah tanggung jawab user yang wajar — ini BUKAN klausula eksonerasi. Klausula eksonerasi yang dilarang adalah klausa yang mengalihkan tanggung jawab PUJK atas kesalahannya sendiri kepada konsumen (misal: "kami tidak bertanggung jawab atas kerugian akibat kelalaian kami").
k) Jika status adalah NOT_ADDRESSED, field "violations" HARUS [] dan field "recommendations" HARUS [] — jangan isi rekomendasi generik seperti "tambahkan prosedur pengaduan" atau "tambahkan perlindungan konsumen" untuk klausa yang tidak relevan dengan OJK.
l) Rekomendasi HANYA boleh diisi jika ada pelanggaran atau kekurangan KONKRET pada klausa yang RELEVAN dengan topik OJK. Rekomendasi harus spesifik terhadap isi klausa, bukan saran umum. Untuk PARTIALLY_COMPLIANT tanpa violations[], rekomendasi harus menjelaskan SECARA KONKRET apa yang perlu ditambahkan/diubah di klausa tersebut.

PENTING untuk field "violations":
- "article": gunakan nomor pasal PERSIS seperti tertulis di dokumen (misal: "Pasal 75 Ayat 1")
- "regulation": gunakan nama regulasi PERSIS seperti tertulis di dokumen (misal: "POJK No. 22/POJK.07/2023")
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
            "violation": "penjelasan detail mengapa klausa SOP melanggar pasal ini dan dampaknya ke konsumen",
            "required": "ketentuan yang diwajibkan oleh pasal tersebut",
            "actual": "kondisi aktual yang tertulis di klausa SOP"
        }}
    ],
    "reasoning": "langkah penalaran detail termasuk apakah klausa relevan dengan topik pasal, dan analisis dampak ke konsumen",
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