"""
bm25_retriever.py — Sparse retriever berbasis BM25Okapi (rank-bm25).
Disimpan per-collection (BI dan OJK terpisah) agar konsisten dengan
arsitektur ChromaDB yang sudah ada.
"""

import re
import pickle
from pathlib import Path
from typing import Dict, List, Optional

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    raise ImportError(
        "rank-bm25 belum terinstal. Jalankan: pip install rank-bm25"
    )


# Stopword bahasa Indonesia — hapus kata generik, PERTAHANKAN kata regulasi
_STOPWORDS = {
    'dan', 'yang', 'dari', 'dalam', 'pada', 'untuk', 'dengan', 'ini',
    'tersebut', 'adalah', 'atau', 'ke', 'di', 'oleh', 'sebagai', 'juga',
    'tidak', 'akan', 'dapat', 'telah', 'sedang', 'harus', 'wajib', 'serta',
    'bahwa', 'maka', 'atas', 'bagi', 'hal', 'paling', 'setiap', 'antara',
    'the', 'of', 'and', 'in', 'to', 'a', 'is', 'that', 'for', 'with',
}


def _tokenize(text: str) -> List[str]:
    """
    Tokenizer sederhana dengan awareness kata regulasi Indonesia.
    Pertahankan nomor dan kode regulasi agar BM25 bisa hard-match.
    """
    # Lowercase kecuali singkatan regulasi
    text_lower = text.lower()
    # Pisahkan token: alfanumerik + slash (untuk nomor PBI/POJK)
    tokens = re.findall(r'[a-z0-9]+(?:/[a-z0-9]+)*', text_lower)
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


class RetrievedNode:
    """Hasil retrieval dari BM25."""
    def __init__(self, content: str, metadata: Dict, score: float, rank: int):
        self.content  = content
        self.metadata = metadata
        self.score    = score
        self.rank     = rank

    def to_dict(self) -> Dict:
        return {
            'content':  self.content,
            'metadata': self.metadata,
            'score':    self.score,
            'rank':     self.rank,
            'source':   'bm25',
        }


class BM25Retriever:
    """
    BM25 sparse retriever yang persist ke disk via pickle.
    Gunakan satu instance per collection (bi_regulations / ojk_regulations).

    Contoh:
        bm25 = BM25Retriever("/path/to/bm25_index/bi_regulations")
        bm25.build_index(chunks)   # chunks: list[{"text": ..., "metadata": ...}]
        results = bm25.retrieve("Pasal 160 ayat 2 batas saldo")
    """

    INDEX_FILE   = "bm25_index.pkl"
    CORPUS_FILE  = "corpus.pkl"

    def __init__(self, index_path: str):
        self.index_dir   = Path(index_path)
        self.bm25: Optional[BM25Okapi] = None
        self.corpus: List[Dict] = []  # {"text": ..., "metadata": ...}

    # ------------------------------------------------------------------
    def build_index(self, chunks: List[Dict]) -> None:
        """
        Bangun BM25 index dari list chunk.
        chunks: [{"text": str, "metadata": dict}, ...]
        """
        if not chunks:
            print("[BM25] Tidak ada chunk untuk di-index.")
            return

        self.corpus = chunks
        tokenized  = [_tokenize(c["text"]) for c in chunks]
        self.bm25  = BM25Okapi(tokenized)

        self.index_dir.mkdir(parents=True, exist_ok=True)
        with open(self.index_dir / self.INDEX_FILE, 'wb') as f:
            pickle.dump(self.bm25, f)
        with open(self.index_dir / self.CORPUS_FILE, 'wb') as f:
            pickle.dump(self.corpus, f)

        print(f"[BM25] Index dibangun: {len(chunks)} chunks → {self.index_dir}")

    # ------------------------------------------------------------------
    def load_index(self) -> bool:
        """Load index dari disk. Return True jika berhasil."""
        idx_file    = self.index_dir / self.INDEX_FILE
        corpus_file = self.index_dir / self.CORPUS_FILE

        if not idx_file.exists() or not corpus_file.exists():
            return False

        try:
            with open(idx_file, 'rb') as f:
                self.bm25 = pickle.load(f)
            with open(corpus_file, 'rb') as f:
                self.corpus = pickle.load(f)
            print(f"[BM25] Index dimuat: {len(self.corpus)} chunks dari {self.index_dir}")
            return True
        except Exception as e:
            print(f"[BM25] Gagal memuat index: {e}")
            return False

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        filter_regulation: Optional[str] = None,
    ) -> List[RetrievedNode]:
        """
        Retrieve top-k chunk paling relevan berdasarkan BM25 score.

        Args:
            query              : Query string
            top_k              : Jumlah hasil yang dikembalikan
            filter_regulation  : Jika diisi, filter chunk yang metadata
                                 regulation_code-nya mengandung string ini.
        """
        if self.bm25 is None or not self.corpus:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        # Pasangkan score dengan chunk
        scored = [
            (score, i, chunk)
            for i, (score, chunk) in enumerate(zip(scores, self.corpus))
            if score > 0
        ]

        # Optional: filter berdasarkan kode regulasi di metadata
        if filter_regulation:
            fl = filter_regulation.lower()
            scored = [
                (s, i, c) for s, i, c in scored
                if fl in c.get('metadata', {}).get('regulation_code', '').lower()
            ]

        # Sort descending by score, ambil top_k
        scored.sort(key=lambda x: x[0], reverse=True)
        scored = scored[:top_k]

        return [
            RetrievedNode(
                content  = c["text"],
                metadata = c.get("metadata", {}),
                score    = float(s),
                rank     = rank + 1,
            )
            for rank, (s, _, c) in enumerate(scored)
        ]
