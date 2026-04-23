"""
query_analyzer.py — Deteksi intent query untuk menentukan strategi retrieval.
Query dengan identifier spesifik (nomor pasal, kode regulasi) mendapat
sparse_boost lebih tinggi agar BM25 lebih dominan dalam fusion.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class QueryIntent:
    original_query: str
    is_specific: bool           # True jika ada identifier spesifik
    regulation_codes: List[str] = field(default_factory=list)  # ["PBI 23/6/2021"]
    pasal_numbers: List[str]   = field(default_factory=list)   # ["160"]
    ayat_numbers: List[str]    = field(default_factory=list)   # ["2"]
    years: List[str]           = field(default_factory=list)   # ["2021"]
    retrieval_mode: str        = "dense_only"   # "hybrid" | "dense_only"
    sparse_boost: float        = 0.3            # bobot sparse dalam RRF


# Regex patterns
_REGULATION_RE = re.compile(
    r'(?:PBI|POJK|SEBI|SEOJK)\s*(?:No\.?\s*)?'
    r'(\d+[/\.]\d+(?:[/\. ]\w+)?(?:[/\.]\d{4})?)',
    re.IGNORECASE
)
_PERATURAN_RE = re.compile(
    r'(?:Peraturan\s+)?(?:Bank Indonesia|OJK|Otoritas Jasa Keuangan)\s+'
    r'(?:Nomor\s+)?(\d+(?:[/\.]\d+)*)\s*(?:Tahun\s+(\d{4}))?',
    re.IGNORECASE
)
_PASAL_RE = re.compile(r'\bPasal\s+(\d+)\b', re.IGNORECASE)
_AYAT_RE  = re.compile(r'\b[Aa]yat\s+\(?\s*(\d+|[a-z])\s*\)?')
_YEAR_RE  = re.compile(r'\b(20\d{2})\b')


class QueryAnalyzer:
    """
    Menganalisis query dan mengklasifikasikan strategi retrieval.

    Contoh:
        qa = QueryAnalyzer()
        intent = qa.analyze("Peraturan BI nomor 23/6/2021 tentang apa?")
        # intent.is_specific  -> True
        # intent.sparse_boost -> 0.7
        # intent.retrieval_mode -> "hybrid"
    """

    def analyze(self, query: str) -> QueryIntent:
        intent = QueryIntent(original_query=query)

        # Cari kode regulasi
        for m in _REGULATION_RE.finditer(query):
            intent.regulation_codes.append(m.group(0).strip())
        for m in _PERATURAN_RE.finditer(query):
            intent.regulation_codes.append(m.group(0).strip())

        # Cari nomor pasal
        for m in _PASAL_RE.finditer(query):
            intent.pasal_numbers.append(m.group(1))

        # Cari nomor ayat
        for m in _AYAT_RE.finditer(query):
            intent.ayat_numbers.append(m.group(1))

        # Cari tahun
        for m in _YEAR_RE.finditer(query):
            intent.years.append(m.group(1))

        # Deduplicate
        intent.regulation_codes = list(dict.fromkeys(intent.regulation_codes))
        intent.pasal_numbers    = list(dict.fromkeys(intent.pasal_numbers))
        intent.ayat_numbers     = list(dict.fromkeys(intent.ayat_numbers))
        intent.years            = list(dict.fromkeys(intent.years))

        # Tentukan strategi
        has_identifier = bool(
            intent.regulation_codes or intent.pasal_numbers or intent.ayat_numbers
        )
        intent.is_specific    = has_identifier
        intent.retrieval_mode = "hybrid" if has_identifier else "dense_only"
        intent.sparse_boost   = 0.7 if has_identifier else 0.3

        return intent
