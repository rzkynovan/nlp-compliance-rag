"""
query_analyzer.py — Deteksi intent query untuk menentukan strategi retrieval.

Tiga tipe query utama berdasarkan feedback dosen:

  Type 1 — EXACT_REGULATION:
    "Apa isi dari Peraturan OJK no. 22 tahun 2023?"
    → Identifier ada, topik semantik tidak ada → BM25 dominan (sparse_boost=1.0)

  Type 2 — HYBRID_REGULATION:
    "Apakah pinjol diatur di Peraturan OJK no. 22 tahun 2023?"
    → Identifier ada + topik semantik ada → BM25 + dense search (sparse_boost=0.7)

  Type 3 — SEMANTIC_COMPLIANCE:
    "Apa aturan tentang batas saldo e-wallet?"
    → Tidak ada identifier, query semantik compliance → dense only (sparse_boost=0.3)

  Type 4 — GREETING:
    "Halo", "Selamat pagi", "Terima kasih"
    → Sapaan, boleh direspons ramah, tidak perlu retrieval

  Type 5 — OUT_OF_SCOPE:
    "Cuaca hari ini gimana?", "Rekomendasikan film"
    → Di luar domain kepatuhan regulasi, harus ditolak
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List


class QueryType(Enum):
    EXACT_REGULATION  = "exact_regulation"   # Identifier ada, topik semantik minim
    HYBRID_REGULATION = "hybrid_regulation"  # Identifier ada + topik semantik ada
    SEMANTIC_COMPLIANCE = "semantic_compliance"  # Hanya semantic, tidak ada identifier
    GREETING          = "greeting"           # Sapaan — boleh, tidak perlu retrieval
    OUT_OF_SCOPE      = "out_of_scope"       # Di luar domain — tolak


@dataclass
class QueryIntent:
    original_query: str
    query_type: QueryType            = QueryType.SEMANTIC_COMPLIANCE
    is_specific: bool               = False   # True jika ada identifier regulasi/pasal
    regulation_codes: List[str]     = field(default_factory=list)
    pasal_numbers: List[str]        = field(default_factory=list)
    ayat_numbers: List[str]         = field(default_factory=list)
    years: List[str]                = field(default_factory=list)
    semantic_terms: List[str]       = field(default_factory=list)  # Topik di luar identifier
    retrieval_mode: str             = "dense_only"  # "exact" | "hybrid" | "dense_only" | "none"
    sparse_boost: float             = 0.3


# ─── Regex: identifier regulasi ─────────────────────────────────
_REGULATION_RE = re.compile(
    r'(?:PBI|POJK|SEBI|SEOJK)\s*(?:No\.?\s*)?'
    r'(\d+[/\.]\d+(?:[/\. ]\w+)?(?:[/\.]\d{4})?)',
    re.IGNORECASE
)
_PERATURAN_RE = re.compile(
    r'(?:Peraturan\s+)?(?:Bank\s*Indonesia|OJK|Otoritas\s+Jasa\s+Keuangan)\s+'
    r'(?:Nomor\s+)?(\d+(?:[/\.]\d+)*)\s*(?:Tahun\s+(\d{4}))?',
    re.IGNORECASE
)
_PASAL_RE = re.compile(r'\bPasal\s+(\d+)\b', re.IGNORECASE)
_AYAT_RE  = re.compile(r'\b[Aa]yat\s+\(?\s*(\d+|[a-z])\s*\)?')
_YEAR_RE  = re.compile(r'\b(20\d{2})\b')

# ─── Kata-kata yang bukan topik semantik (question/filler words) ─
_FILLER_WORDS = {
    "apa", "apakah", "bagaimana", "berapa", "bisakah", "bolehkah",
    "adalah", "isi", "dari", "tentang", "mengenai", "terkait",
    "nomor", "no", "tahun", "peraturan", "pasal", "ayat", "huruf",
    "yang", "di", "ke", "pada", "untuk", "dengan", "dan", "atau",
    "ini", "itu", "ada", "tidak", "pbi", "pojk", "sebi", "bi", "ojk",
    "bank", "indonesia", "otoritas", "jasa", "keuangan",
}

# ─── Kata kunci domain compliance ───────────────────────────────
_COMPLIANCE_KEYWORDS = {
    # Produk keuangan
    "e-wallet", "ewallet", "dompet", "digital", "fintech", "uang", "elektronik",
    "kartu", "kredit", "debit", "rekening", "tabungan", "pinjaman", "pinjol",
    "paylater", "transfer", "pembayaran", "payment",
    # Compliance & regulasi
    "kepatuhan", "regulasi", "peraturan", "compliance", "audit", "sop",
    "prosedur", "standar", "kewajiban", "larangan", "sanksi", "denda",
    # Topik spesifik BI/OJK
    "saldo", "transaksi", "kyc", "aml", "cdd", "limit", "batas",
    "verifikasi", "identitas", "pengaduan", "keluhan", "complaint", "sla",
    "perlindungan", "konsumen", "pengguna", "nasabah",
    "settlement", "kliring", "escrow", "dormant",
    "data", "pribadi", "privasi", "keamanan",
    # Lembaga
    "fintech", "penyelenggara", "operator", "merchant", "acquiring",
}

# ─── Pola sapaan (greeting) ──────────────────────────────────────
_GREETING_RE = re.compile(
    r'^\s*(?:'
    r'halo|hai|hi|hello|hey|'
    r'selamat\s+(?:pagi|siang|sore|malam)|'
    r'good\s+(?:morning|afternoon|evening|night)|'
    r'permisi|'
    r'(?:terima\s+kasih|makasih|thanks?)\b.*'
    r')\s*[!.,?]*\s*$',
    re.IGNORECASE
)

# ─── Query pertanyaan teknis tentang sistem ──────────────────────
_META_SYSTEM_RE = re.compile(
    r'(?:apa|bagaimana)\s+(?:cara|fungsi|fitur|kemampuan|bisa)\s+'
    r'(?:sistem|aplikasi|kamu|anda|ini)',
    re.IGNORECASE
)


class QueryAnalyzer:
    """
    Menganalisis query dan mengklasifikasikan ke dalam 5 QueryType.

    Contoh:
        qa = QueryAnalyzer()

        # Type 1: exact_regulation
        intent = qa.analyze("Apa isi dari Peraturan OJK no. 22 tahun 2023?")
        # intent.query_type  -> QueryType.EXACT_REGULATION
        # intent.retrieval_mode -> "exact"
        # intent.sparse_boost   -> 1.0

        # Type 2: hybrid_regulation
        intent = qa.analyze("Apakah pinjol diatur di Peraturan OJK no. 22 tahun 2023?")
        # intent.query_type  -> QueryType.HYBRID_REGULATION
        # intent.retrieval_mode -> "hybrid"
        # intent.sparse_boost   -> 0.7

        # Type 3: semantic_compliance
        intent = qa.analyze("Apa batas saldo e-wallet yang diperbolehkan?")
        # intent.query_type  -> QueryType.SEMANTIC_COMPLIANCE
        # intent.retrieval_mode -> "dense_only"

        # Type 4: greeting
        intent = qa.analyze("Halo!")
        # intent.query_type  -> QueryType.GREETING

        # Type 5: out_of_scope
        intent = qa.analyze("Cuaca hari ini gimana ya?")
        # intent.query_type  -> QueryType.OUT_OF_SCOPE
    """

    def analyze(self, query: str) -> QueryIntent:
        intent = QueryIntent(original_query=query)
        q = query.strip()

        # ── 1. Deteksi greeting ──────────────────────────────────
        if self._is_greeting(q):
            intent.query_type     = QueryType.GREETING
            intent.retrieval_mode = "none"
            intent.sparse_boost   = 0.0
            return intent

        # ── 2. Ekstrak identifier ────────────────────────────────
        self._extract_identifiers(q, intent)
        has_identifier = bool(
            intent.regulation_codes or intent.pasal_numbers or intent.ayat_numbers
        )
        intent.is_specific = has_identifier

        # ── 3. Ekstrak topik semantik (diluar identifier) ────────
        intent.semantic_terms = self._extract_semantic_terms(q)
        has_semantic = len(intent.semantic_terms) > 0

        # ── 4. Cek domain compliance ─────────────────────────────
        in_domain = self._is_compliance_domain(q)

        # ── 5. Klasifikasi QueryType ─────────────────────────────
        if has_identifier and not has_semantic:
            # "Apa isi PBI 23/6/2021?" → exact lookup
            intent.query_type     = QueryType.EXACT_REGULATION
            intent.retrieval_mode = "exact"
            intent.sparse_boost   = 1.0

        elif has_identifier and has_semantic:
            # "Apakah pinjol diatur di POJK no. 22 tahun 2023?" → hybrid
            intent.query_type     = QueryType.HYBRID_REGULATION
            intent.retrieval_mode = "hybrid"
            intent.sparse_boost   = 0.7

        elif in_domain:
            # "Apa batas saldo e-wallet?" → semantic compliance
            intent.query_type     = QueryType.SEMANTIC_COMPLIANCE
            intent.retrieval_mode = "dense_only"
            intent.sparse_boost   = 0.3

        else:
            # "Cuaca hari ini gimana?" → out of scope
            intent.query_type     = QueryType.OUT_OF_SCOPE
            intent.retrieval_mode = "none"
            intent.sparse_boost   = 0.0

        return intent

    # ── Private helpers ─────────────────────────────────────────

    def _is_greeting(self, query: str) -> bool:
        """True jika query adalah sapaan murni (pendek, pola sapaan)."""
        if len(query.split()) > 8:
            return False
        return bool(_GREETING_RE.match(query))

    def _extract_identifiers(self, query: str, intent: QueryIntent) -> None:
        """Isi intent.regulation_codes, pasal_numbers, ayat_numbers, years."""
        for m in _REGULATION_RE.finditer(query):
            intent.regulation_codes.append(m.group(0).strip())
        for m in _PERATURAN_RE.finditer(query):
            text = m.group(0).strip()
            if text not in intent.regulation_codes:
                intent.regulation_codes.append(text)
        for m in _PASAL_RE.finditer(query):
            intent.pasal_numbers.append(m.group(1))
        for m in _AYAT_RE.finditer(query):
            intent.ayat_numbers.append(m.group(1))
        for m in _YEAR_RE.finditer(query):
            intent.years.append(m.group(1))

        intent.regulation_codes = list(dict.fromkeys(intent.regulation_codes))
        intent.pasal_numbers    = list(dict.fromkeys(intent.pasal_numbers))
        intent.ayat_numbers     = list(dict.fromkeys(intent.ayat_numbers))
        intent.years            = list(dict.fromkeys(intent.years))

    def _extract_semantic_terms(self, query: str) -> List[str]:
        """
        Ambil kata-kata bermakna di luar identifier dan filler words.
        Digunakan untuk membedakan Type 1 vs Type 2.
        """
        # Hapus identifier dari query agar tidak terhitung sebagai semantic
        cleaned = _REGULATION_RE.sub("", query)
        cleaned = _PERATURAN_RE.sub("", cleaned)
        cleaned = _PASAL_RE.sub("", cleaned)
        cleaned = _AYAT_RE.sub("", cleaned)
        cleaned = _YEAR_RE.sub("", cleaned)

        words = re.findall(r'\b[a-zA-Z][a-zA-Z\-]{2,}\b', cleaned.lower())
        semantic = [w for w in words if w not in _FILLER_WORDS]
        return list(dict.fromkeys(semantic))

    def _is_compliance_domain(self, query: str) -> bool:
        """
        True jika query mengandung setidaknya satu keyword domain compliance,
        atau mengandung kata kunci peraturan/regulasi tanpa nomor spesifik.
        """
        q_lower = query.lower()

        # Cek keyword domain langsung
        if any(kw in q_lower for kw in _COMPLIANCE_KEYWORDS):
            return True

        # Cek pola "peraturan / regulasi / aturan / ketentuan" tanpa nomor
        if re.search(r'\b(?:peraturan|regulasi|aturan|ketentuan|kewajiban|larangan)\b',
                     q_lower):
            return True

        # Cek pertanyaan tentang sistem itu sendiri (meta)
        if _META_SYSTEM_RE.search(query):
            return True

        return False
