# Draft Implementasi: Hybrid Retrieval (Dense + BM25)

**Tanggal:** 2026-04-24  
**Konteks:** Feedback dosen — perlu hard match untuk query identifier spesifik  
**Contoh query:** "Peraturan BI nomor 23/6/2021 berbicara tentang apa?"

---

## Latar Belakang

Sistem RAG saat ini hanya menggunakan **dense retrieval** (ChromaDB cosine similarity).
Kelemahan: gagal pada query yang mengandung identifier spesifik seperti nomor peraturan,
nomor pasal, atau tahun karena vektor semantik tidak bisa "menghitung" nomor.

Solusi: tambahkan **BM25 sparse retrieval** secara paralel, gabungkan dengan
**Reciprocal Rank Fusion (RRF)**.

---

## Arsitektur Baru

```
Query Masuk
    │
    ▼
[Query Analyzer] ──── deteksi "PBI 23/6/2021", "Pasal 160", "tahun 2021"
    │
    ├── identifier terdeteksi → sparse_boost = 0.7
    └── query semantik biasa  → sparse_boost = 0.3
    │
    ├──────────────────────────────────┐
    ▼                                  ▼
[Dense: ChromaDB]           [Sparse: BM25 per-collection]
cosine similarity           keyword + nomor pasal/PBI/POJK
    │                                  │
    └──────────┬───────────────────────┘
               ▼
    [RRF Fusion: score = Σ 1/(k + rank_i), k=60]
               │
               ▼
    [Agen BI / Agen OJK → Conflict Resolver]
```

---

## Urutan Implementasi (12 Step)

| Step | File | Aksi | Catatan |
|---|---|---|---|
| 1 | `src/retrieval/metadata_extractor.py` | **Buat baru** | Ekstrak `regulation_code`, `pasal_number`, `ayat_number` dari teks chunk |
| 2 | `src/retrieval/query_analyzer.py` | **Buat baru** | Regex detector → output `QueryIntent` dataclass |
| 3 | `src/retrieval/bm25_retriever.py` | **Buat baru** | BM25Okapi, persist ke disk, per-collection |
| 4 | `src/retrieval/hybrid_retriever.py` | **Buat baru** | Gabungkan dense + sparse via RRF |
| 5 | `src/retrieval/__init__.py` | **Buat baru** | Export semua modul retrieval |
| 6 | `requirements.txt` | **Modifikasi** | Tambah `rank-bm25>=0.2.2` |
| 7 | `src/ingest.py` | **Modifikasi** | Perkaya metadata chunk + build BM25 index |
| 8 | `src/agents/base_agent.py` | **Modifikasi** | Terima `HybridRetriever` sebagai opsional |
| 9 | `src/agents/bi_specialist.py` | **Modifikasi** | Init hybrid retriever + query analyzer |
| 10 | `src/agents/ojk_specialist.py` | **Modifikasi** | Sama seperti step 9 |
| 11 | `backend/app/services/rag_service.py` | **Modifikasi** | Expose `retrieval_mode` di response |
| 12 | Re-ingest + Evaluasi | **Jalankan ulang** | Metadata lama ChromaDB tidak ada field baru |

---

## Detail per File

### File Baru 1: `src/retrieval/metadata_extractor.py`

Ekstrak metadata terstruktur dari teks chunk saat proses ingest.

```python
def extract_regulation_metadata(text: str, filename: str) -> dict:
    # Return:
    # {
    #   "regulation_code": "PBI 23/6/2021",
    #   "regulation_number": "23/6/2021",
    #   "regulation_year": "2021",
    #   "pasal_number": "160",
    #   "ayat_number": "2",
    #   "section_heading": "Pasal 160",
    # }
```

Metadata ini disimpan bersama setiap chunk di ChromaDB dan BM25 index.

---

### File Baru 2: `src/retrieval/query_analyzer.py`

Mendeteksi apakah query mengandung identifier spesifik via regex.

**Regex patterns:**
- Nomor regulasi: `r'(?:PBI|POJK|SEBI)\s*(?:No\.?\s*)?(\d+[/\.]\d+(?:[/\.]\d+)?)'`
- Nomor pasal: `r'[Pp]asal\s+(\d+)'`
- Nomor ayat: `r'[Aa]yat\s+(\d+|\([a-z]\))'`
- Tahun: `r'\b(20\d{2})\b'`

**Output `QueryIntent` dataclass:**
```python
@dataclass
class QueryIntent:
    original_query: str
    is_specific: bool        # True jika ada identifier
    regulation_codes: list   # ["PBI 23/6/2021"]
    pasal_numbers: list      # ["160"]
    ayat_numbers: list       # ["2"]
    years: list              # ["2021"]
    retrieval_mode: str      # "hybrid" | "dense_only"
    sparse_boost: float      # 0.7 jika specific, 0.3 jika tidak
```

---

### File Baru 3: `src/retrieval/bm25_retriever.py`

BM25 berbasis `rank-bm25`, disimpan per-collection (BI dan OJK terpisah).

**Index path:** `data/processed/bm25_index/{collection_name}/`

```python
class BM25Retriever:
    def build_index(self, chunks: List[Dict]) -> None: ...
    def load_index(self) -> bool: ...
    def retrieve(self, query: str, top_k: int = 10,
                 filter_regulation: str = None) -> List[RetrievedNode]: ...
    def _tokenize(self, text: str) -> List[str]: ...
```

**Stopword:** Hapus kata generik (`dan`, `yang`, `dari`, `dalam`, `pada`, `untuk`,
`dengan`, `ini`, `tersebut`, `adalah`). **Pertahankan** kata penting regulasi
(`pasal`, `ayat`, `peraturan`, `nomor`) karena informatif untuk matching.

---

### File Baru 4: `src/retrieval/hybrid_retriever.py`

Orkestrasi RRF Fusion antara dense dan sparse.

```python
class HybridRetriever:
    def retrieve(self, query: str, intent: QueryIntent,
                 top_k: int = 5) -> List[Dict]:
        dense_results  = self._dense_retrieve(query, top_k * 2)
        sparse_results = self.bm25.retrieve(query, top_k * 2)
        fused = self._rrf_fusion(dense_results, sparse_results,
                                  alpha=intent.sparse_boost)
        return fused[:top_k]

    def _rrf_fusion(self, dense, sparse, alpha=0.5, k=60) -> List[Dict]:
        # score(d) = alpha * (1/(k + rank_sparse)) + (1-alpha) * (1/(k + rank_dense))
        ...
```

---

### Modifikasi `src/ingest.py`

Dua perubahan:

1. **Perkaya metadata** — setelah node parser, panggil `metadata_extractor` untuk setiap node
2. **Build BM25 index** — setelah ChromaDB selesai, kumpulkan semua nodes dan bangun BM25

```python
# Setelah build ChromaDB:
bm25 = BM25Retriever(index_path=str(BM25_INDEX_DIR / collection_name))
all_chunks = [{"text": n.get_content(), "metadata": n.metadata} for n in nodes]
bm25.build_index(all_chunks)
```

> ⚠️ **Wajib re-ingest** setelah perubahan ini karena metadata lama tidak punya field baru.

---

### Modifikasi `src/agents/bi_specialist.py` & `ojk_specialist.py`

Di `initialize()`, tambahkan:

```python
bm25 = BM25Retriever(index_path=str(BM25_INDEX_DIR / self.collection_name))
if bm25.load_index():
    self.hybrid_retriever = HybridRetriever(self.index, bm25)
    self.query_analyzer   = QueryAnalyzer()
else:
    self.hybrid_retriever = None  # fallback ke dense-only
```

Di `retrieve_relevant_articles()`:

```python
def retrieve_relevant_articles(self, query: str, top_k: int = 5) -> List[Dict]:
    intent = self.query_analyzer.analyze(query)
    if self.hybrid_retriever and intent.is_specific:
        return self.hybrid_retriever.retrieve(query, intent, top_k)
    # fallback: existing dense-only path
    ...
```

---

## Design Decisions

| Keputusan | Alasan |
|---|---|
| BM25, bukan ChromaDB `where` filter | Filter hanya menyaring, tidak ranking. BM25 memberi relevance score ke seluruh corpus |
| `rank-bm25` library | Pure Python, zero external service, cocok dengan arsitektur ChromaDB local |
| Alpha dinamis (0.3 / 0.7) | Query audit SOP = semantik (dense dominan). Query identifier = sparse dominan |
| BM25 per-collection | Konsisten dengan isolasi BI/OJK di ChromaDB |
| RRF bukan weighted sum | Tidak sensitif terhadap perbedaan skala skor (cosine 0–1 vs BM25 0–20+) |

---

## Evaluasi Tambahan (setelah implementasi)

Tambahkan ke `src/evaluation.py`:

- **Retrieval Precision@K** untuk query specific vs. generic (dipisah)
- **Rank quality**: apakah chunk dengan pasal yang tepat muncul di rank 1–3?
- Bandingkan hasil dense-only vs. hybrid pada query identifier ("PBI 23/6/2021 tentang apa?")

---

## Status

- [x] Step 1: `metadata_extractor.py` — selesai 2026-04-24
- [x] Step 2: `query_analyzer.py` — selesai 2026-04-24
- [x] Step 3: `bm25_retriever.py` — selesai 2026-04-24
- [x] Step 4: `hybrid_retriever.py` — selesai 2026-04-24
- [x] Step 5: `__init__.py` — selesai 2026-04-24
- [x] Step 6: `requirements.txt` — selesai 2026-04-24
- [x] Step 7: `ingest.py` — selesai 2026-04-24
- [x] Step 8: `base_agent.py` — selesai 2026-04-24
- [x] Step 9: `bi_specialist.py` — selesai 2026-04-24
- [x] Step 10: `ojk_specialist.py` — selesai 2026-04-24
- [x] Step 11: `rag_service.py` — selesai 2026-04-24
- [ ] Step 12: Re-ingest + evaluasi — **PERLU DIJALANKAN MANUAL**
  ```bash
  python src/ingest.py --force
  ```
