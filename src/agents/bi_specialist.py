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
        # Gunakan api_key (OpenAI key) bukan Anthropic key
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
            recommendations=parsed.get("recommendations", []),
            checklist_topic=parsed.get("checklist_topic"),
            checklist_covered=parsed.get("checklist_covered", []),
            missing_elements=parsed.get("missing_elements", []),
        )
    
    # Sub-elemen wajib per topik regulasi — digunakan untuk deteksi PARTIALLY_COMPLIANT
    TOPIC_CHECKLISTS = {
        "BALANCE_LIMIT": {
            "label": "Batas Saldo E-Wallet",
            "trigger_keywords": [
                "saldo", "balance", "maksimal", "maksimum", "limit saldo",
                "unverified", "verified", "terverifikasi", "belum terverifikasi",
                "rekening dasar", "rekening premium"
            ],
            "elements": [
                "(A) Batas saldo akun UNVERIFIED: ≤ Rp 2.000.000 (sesuai PBI 23/6/2021 Pasal 160 Ayat 1)",
                "(B) Batas saldo akun VERIFIED: ≤ Rp 10.000.000 (sesuai PBI 23/6/2021 Pasal 160 Ayat 1)",
                "(C) Ketentuan peningkatan tier melalui verifikasi KYC yang jelas",
            ],
            "rule": (
                "Jika klausa MEMBAHAS batas saldo → periksa berapa sub-elemen (A–C) yang dicakup. "
                "Jika nilai yang disebutkan MELEBIHI batas → NON_COMPLIANT untuk tier tersebut. "
                "Jika hanya satu tier dicakup dan yang lain tidak → PARTIALLY_COMPLIANT. "
                "Jika semua tier disebutkan dengan nilai sesuai → COMPLIANT."
            ),
        },
        "TRANSACTION_LIMIT": {
            "label": "Batas Transaksi Bulanan",
            "trigger_keywords": [
                "transaksi", "transfer", "batas transaksi", "limit transaksi",
                "bulanan", "per bulan", "masuk", "keluar", "debit", "kredit",
                "unlimited", "tidak dibatasi", "tanpa batas"
            ],
            "elements": [
                "(A) Batas transaksi MASUK bulanan: ≤ Rp 20.000.000 (sesuai PBI 23/6/2021 Pasal 160 Ayat 2)",
                "(B) Batas transaksi KELUAR bulanan: ≤ Rp 20.000.000",
                "(C) Pemberlakuan limit untuk kedua tier (unverified dan verified)",
            ],
            "rule": (
                "Jika klausa MEMBAHAS batas transaksi → periksa sub-elemen (A–C). "
                "Jika menyebutkan 'unlimited' atau 'tanpa batas' → NON_COMPLIANT. "
                "Jika hanya arah masuk/keluar saja yang disebutkan → PARTIALLY_COMPLIANT. "
                "Jika semua limit sesuai → COMPLIANT."
            ),
        },
        "KYC_VERIFICATION": {
            "label": "KYC dan Verifikasi Identitas",
            "trigger_keywords": [
                "kyc", "verifikasi", "identitas", "nik", "ktp", "kartu tanda penduduk",
                "selfie", "liveness", "dokumen identitas", "pengenal diri"
            ],
            "elements": [
                "(A) Mekanisme verifikasi identitas pengguna (NIK/KTP/dokumen resmi)",
                "(B) Proses upgrade tier dari unverified ke verified",
                "(C) Konsekuensi KYC pada limit saldo dan transaksi yang berubah",
            ],
            "rule": (
                "Jika klausa MEMBAHAS KYC/verifikasi → periksa sub-elemen (A–C). "
                "Jika 1–2 terpenuhi → PARTIALLY_COMPLIANT. Jika semua terpenuhi → COMPLIANT."
            ),
        },
    }

    def _build_checklist_section(self, clause: str) -> str:
        """
        Bangun bagian CHECKLIST PARTIALLY_COMPLIANT untuk semua topik BI.
        """
        lines = [
            "",
            "MEKANISME CHECKLIST PARTIALLY_COMPLIANT:",
            "Gunakan checklist berikut untuk menentukan apakah klausa yang relevan",
            "mencakup SEMUA sub-elemen yang diwajibkan regulasi BI.",
            "",
        ]
        for topic_key, topic in self.TOPIC_CHECKLISTS.items():
            lines.append(f"[TOPIK: {topic['label']}]")
            lines.append("Sub-elemen yang diperiksa:")
            for elem in topic["elements"]:
                lines.append(f"  {elem}")
            lines.append(f"Aturan: {topic['rule']}")
            lines.append("")
        lines.append(
            "PENTING: Checklist HANYA berlaku jika klausa SECARA EKSPLISIT membahas topik tersebut. "
            "Jangan paksa checklist jika klausa tidak relevan dengan topik."
        )
        return "\n".join(lines)

    def build_prompt(self, clause: str, articles: List[Dict]) -> str:
        """
        Build structured prompt for BI compliance check with checklist mechanism.
        """
        articles_text = "\n\n".join([
            f"[{a['metadata'].get('regulator', 'BI')}] {a['content']}"
            for a in articles
        ])

        checklist_section = self._build_checklist_section(clause)

        return f"""Kamu adalah Auditor Kepatuhan Regulasi Bank Indonesia (BI Specialist).

PASAL-PASAL REGULASI BI YANG RELEVAN (gunakan NAMA REGULASI dan NOMOR PASAL PERSIS dari dokumen ini):
{articles_text}

KLAUSA SOP/T&C YANG DIUJI:
"{clause}"

ALUR WAJIB — IKUTI LANGKAH INI SECARA BERURUTAN:
Langkah 1: Tentukan apakah klausa relevan dengan topik BI (batas saldo, batas transaksi, KYC, settlement).
Langkah 2: Jika RELEVAN → identifikasi topik checklist yang berlaku dari MEKANISME CHECKLIST di bawah.
Langkah 3: Tandai setiap sub-elemen checklist sebagai "ADA" atau "TIDAK ADA" berdasarkan isi klausa.
Langkah 4: Hitung berapa sub-elemen yang ada vs total. Tentukan status berdasarkan aturan checklist.
Langkah 5: Isi output JSON dengan hasil analisis.
{checklist_section}

CONTOH WAJIB — BACA UNTUK MEMAHAMI CARA KERJA CHECKLIST:
Klausa contoh: "Saldo maksimum akun pengguna yang belum diverifikasi adalah Rp 2.000.000."
Langkah 1: Topik relevan BI? YA — membahas batas saldo.
Langkah 2: Topik checklist = BALANCE_LIMIT (Batas Saldo E-Wallet).
Langkah 3: Periksa 3 sub-elemen:
  (A) Batas saldo UNVERIFIED → ADA ✓ (Rp 2.000.000 sesuai regulasi)
  (B) Batas saldo VERIFIED → TIDAK ADA di klausa
  (C) Ketentuan upgrade KYC → TIDAK ADA di klausa
Langkah 4: 1 dari 3 sub-elemen terpenuhi.
Langkah 5: Status = PARTIALLY_COMPLIANT (bukan COMPLIANT — COMPLIANT butuh semua 3 sub-elemen)
  checklist_covered = ["(A) Batas saldo unverified Rp 2.000.000 sesuai regulasi"]
  missing_elements = ["(B) Batas saldo VERIFIED tidak disebutkan", "(C) Ketentuan upgrade KYC tidak disebutkan"]

ATURAN PENTING — BACA SEBELUM MENJAWAB:
a) Topik yang relevan BI: batas saldo, batas transaksi, KYC, settlement, penyelenggaraan pembayaran. Topik TIDAK relevan: penanganan keluhan/pengaduan, data privasi, klausula baku, perlindungan konsumen — ini domain OJK.
b) Gunakan "NOT_ADDRESSED" jika klausa SOP TIDAK MEMBAHAS topik yang diatur pasal BI.
c) Gunakan "NON_COMPLIANT" HANYA jika klausa SOP secara AKTIF menetapkan nilai/aturan yang BERTENTANGAN dengan pasal regulasi (nilai disebutkan dan melebihi batas yang diijinkan).
d) Gunakan "COMPLIANT" HANYA jika klausa mencakup SEMUA sub-elemen wajib dalam checklist DAN nilainya sesuai. Klausa yang hanya menyebut SATU elemen dari topik multi-elemen TIDAK boleh COMPLIANT.
e) Gunakan "PARTIALLY_COMPLIANT" dalam DUA skenario:
   SKENARIO 1 — KONFLIK PARSIAL: nilai sebagian sesuai dan sebagian bertentangan.
   SKENARIO 2 — CAKUPAN TIDAK LENGKAP: klausa membahas topik BI namun hanya mencakup SEBAGIAN sub-elemen checklist. Ini adalah kasus umum — klausa tentang saldo unverified saja, atau transaksi masuk saja → PARTIALLY_COMPLIANT, bukan COMPLIANT.
f) Absence of mention ≠ NON_COMPLIANT. Namun absence of mention ADALAH dasar PARTIALLY_COMPLIANT jika klausa membahas topik yang sama tapi tidak mencakup semua sub-elemen.
g) JANGAN gunakan placeholder seperti "Pasal X" atau "PBI No. XX/XX".
h) Jika status adalah NOT_ADDRESSED: "violations" HARUS [] dan "recommendations" HARUS [].
i) Rekomendasi HANYA diisi untuk klausa RELEVAN. Untuk PARTIALLY_COMPLIANT, sebutkan KONKRET sub-elemen yang perlu ditambahkan.

PENTING untuk field "violations":
- "article": gunakan nomor pasal PERSIS seperti tertulis di dokumen (misal: "Pasal 160 Ayat 1")
- "regulation": gunakan nama regulasi PERSIS seperti tertulis di dokumen (misal: "PBI No. 23/6/PBI/2021")
- Hanya isi violations[] jika ada pelanggaran AKTIF (nilai bertentangan), bukan karena tidak disebutkan
- Untuk PARTIALLY_COMPLIANT karena cakupan tidak lengkap: violations[] boleh kosong, gunakan missing_elements

OUTPUT (format JSON wajib, jelaskan dalam Bahasa Indonesia):
{{
    "status": "COMPLIANT/NON_COMPLIANT/PARTIALLY_COMPLIANT/NOT_ADDRESSED",
    "confidence": 0.0-1.0,
    "risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
    "checklist_topic": "nama topik checklist yang digunakan (jika ada), atau null",
    "checklist_covered": ["sub-elemen yang DICAKUP oleh klausa, misal: (A) Batas saldo unverified Rp 2jt"],
    "missing_elements": ["sub-elemen yang TIDAK dicakup klausa tapi wajib ada, misal: (B) Batas saldo verified, (C) Ketentuan upgrade KYC"],
    "violations": [
        {{
            "article": "[nomor pasal dari dokumen regulasi di atas]",
            "regulation": "[nama regulasi dari dokumen di atas]",
            "violation": "penjelasan detail mengapa klausa SOP melanggar pasal ini",
            "required": "nilai atau ketentuan yang diwajibkan oleh pasal tersebut",
            "actual": "nilai atau ketentuan aktual yang tertulis di klausa SOP"
        }}
    ],
    "reasoning": "langkah penalaran detail: (1) apakah klausa relevan, (2) topik checklist apa yang digunakan, (3) sub-elemen mana yang terpenuhi dan tidak, (4) kesimpulan status",
    "recommendations": ["rekomendasi perbaikan konkret — untuk PARTIALLY_COMPLIANT sebutkan sub-elemen spesifik yang harus ditambahkan"]
}}\
"""