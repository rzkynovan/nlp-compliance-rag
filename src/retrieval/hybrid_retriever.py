"""
hybrid_retriever.py — Orkestrasi dense + sparse retrieval via RRF Fusion.
Menggabungkan ChromaDB (dense) dan BM25 (sparse) menggunakan
Reciprocal Rank Fusion agar robust terhadap perbedaan skala score.
"""

from typing import Dict, List, Optional, TYPE_CHECKING

from .bm25_retriever import BM25Retriever, RetrievedNode
from .query_analyzer import QueryIntent

if TYPE_CHECKING:
    from llama_index.core import VectorStoreIndex


_RRF_K = 60  # konstanta RRF standar (Robertson et al.)


class HybridRetriever:
    """
    Hybrid retriever yang menggabungkan:
    - Dense retrieval  : ChromaDB cosine similarity (via LlamaIndex)
    - Sparse retrieval : BM25Okapi (rank-bm25)
    - Fusion           : Reciprocal Rank Fusion (RRF)

    alpha (sparse_boost) dikontrol oleh QueryIntent:
        0.3 → query semantik (dense dominan)
        0.7 → query dengan identifier spesifik (sparse dominan)

    Contoh:
        retriever = HybridRetriever(llama_index, bm25_retriever)
        results = retriever.retrieve("Pasal 160 batas saldo", intent, top_k=5)
    """

    def __init__(
        self,
        dense_index: "VectorStoreIndex",
        bm25: BM25Retriever,
    ):
        self.dense_index = dense_index
        self.bm25        = bm25

    # ------------------------------------------------------------------
    def retrieve(
        self,
        query: str,
        intent: QueryIntent,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Retrieve top-k hasil gabungan dense + sparse.

        Returns list[dict] dengan keys:
            content, metadata, score, rank, source ("dense"|"bm25"|"hybrid")
        """
        fetch_k = top_k * 3  # ambil lebih banyak sebelum fusion

        # Dense retrieval (ChromaDB)
        dense_results = self._dense_retrieve(query, fetch_k)

        # Sparse retrieval (BM25)
        sparse_results = self.bm25.retrieve(query, top_k=fetch_k)

        # RRF Fusion
        fused = self._rrf_fusion(
            dense_results,
            sparse_results,
            alpha=intent.sparse_boost,
        )

        return fused[:top_k]

    # ------------------------------------------------------------------
    def _dense_retrieve(self, query: str, top_k: int) -> List[Dict]:
        """Ambil hasil dari ChromaDB via LlamaIndex retriever."""
        try:
            retriever = self.dense_index.as_retriever(similarity_top_k=top_k)
            nodes     = retriever.retrieve(query)
            results   = []
            for rank, node in enumerate(nodes):
                results.append({
                    'content':  node.get_content(),
                    'metadata': node.metadata,
                    'score':    float(node.score) if node.score is not None else 1.0,
                    'rank':     rank + 1,
                    'source':   'dense',
                })
            return results
        except Exception as e:
            print(f"[HybridRetriever] Dense retrieval error: {e}")
            return []

    # ------------------------------------------------------------------
    def _rrf_fusion(
        self,
        dense: List[Dict],
        sparse: List[RetrievedNode],
        alpha: float = 0.5,
        k: int = _RRF_K,
    ) -> List[Dict]:
        """
        Reciprocal Rank Fusion.

        score(d) = alpha * 1/(k + rank_sparse(d))
                 + (1-alpha) * 1/(k + rank_dense(d))

        Dokumen yang tidak muncul di salah satu list mendapat rank = infinity
        sehingga kontribusinya mendekati 0.
        """
        # Bangun lookup berdasarkan content hash (64 char pertama sebagai key)
        def doc_key(content: str) -> str:
            return content[:80].strip()

        # Inisialisasi score accumulator
        scores: Dict[str, float] = {}
        docs:   Dict[str, Dict]  = {}

        # Kontribusi sparse (BM25)
        for node in sparse:
            key = doc_key(node.content)
            contrib = alpha * (1.0 / (k + node.rank))
            scores[key] = scores.get(key, 0.0) + contrib
            if key not in docs:
                docs[key] = {
                    'content':  node.content,
                    'metadata': node.metadata,
                    'source':   'bm25',
                }

        # Kontribusi dense (ChromaDB)
        for item in dense:
            key     = doc_key(item['content'])
            contrib = (1.0 - alpha) * (1.0 / (k + item['rank']))
            scores[key] = scores.get(key, 0.0) + contrib
            if key not in docs:
                docs[key] = {
                    'content':  item['content'],
                    'metadata': item['metadata'],
                    'source':   'dense',
                }
            else:
                docs[key]['source'] = 'hybrid'  # muncul di kedua retriever

        # Sort descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        result = []
        for rank, (key, score) in enumerate(ranked):
            entry = docs[key].copy()
            entry['score'] = score
            entry['rank']  = rank + 1
            result.append(entry)

        return result
