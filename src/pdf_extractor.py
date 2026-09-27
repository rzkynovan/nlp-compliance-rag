"""
pdf_extractor.py — Ekstraksi teks PDF regulasi menggunakan PyMuPDF.

Sesuai proposal (Gambar 3.4 Fase 1 dan Subbab 3.5.4 Step 3): ekstraksi teks
dilakukan dengan PyMuPDF — lokal, deterministik, dan tanpa biaya API.
LlamaParse tetap tersedia di ingest.py lewat `--extractor llamaparse`.

Header/footer halaman (mis. "- 5 -") dibiarkan di teks; HierarchicalChunker
yang membuangnya saat parsing struktur.
"""

from pathlib import Path
from typing import List

try:
    import pymupdf
except ImportError:  # PyMuPDF < 1.24 hanya menyediakan nama modul "fitz"
    import fitz as pymupdf


def extract_pdf_pages(path) -> List[str]:
    """Kembalikan teks per halaman (indeks 0 = halaman 1)."""
    with pymupdf.open(str(Path(path))) as doc:
        return [page.get_text() for page in doc]


def extract_pdf_bytes(content: bytes) -> List[str]:
    """Sama seperti extract_pdf_pages, tetapi dari isi file di memori (upload)."""
    with pymupdf.open(stream=content, filetype="pdf") as doc:
        return [page.get_text() for page in doc]
