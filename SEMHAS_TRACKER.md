# SEMHAS TRACKER — Gap Proposal TA ↔ Implementasi

> **Untuk agent/AI yang melanjutkan pekerjaan:** baca file ini **sebelum** mengubah kode atau
> dokumen TA. File ini adalah sumber kebenaran untuk status setiap gap antara proposal final
> dan implementasi. Setiap kali menyelesaikan item, **perbarui kolom Status dan Log Sesi** di bawah.

| | |
|---|---|
| **Proyek** | Implementasi RAG untuk Otomatisasi Audit Kepatuhan Regulasi Ganda (BI dan OJK) pada Layanan Dompet Digital |
| **Mahasiswa** | Rizky Novan Aditiya — NRP 5052231035 (Sains Data, FSAD ITS) |
| **Pembimbing** | Tintrim Dwi Ary Widhianingsih, S.Si., M.Stat., Ph.D. |
| **Proposal** | **FINAL, sudah dikumpulkan** (Sempro Agustus 2026). Teks proposal **tidak diubah lagi**. |
| **Target berikutnya** | Seminar Hasil (Semhas) & Ujian TA — minggu ke-4 Desember 2026 |
| **Dibuat** | 2026-09-25 (Phase 16) |
| **Branch kerja** | `claude/funny-lovelace-lfga0w` |
| **Versi halaman (artifact)** | https://claude.ai/artifact/Egridfhr6WkQx4XqiDsy3h — salinan baca-saja; **file ini tetap sumber kebenaran**. Jika tracker diubah, publish ulang artifact tersebut. |

## 0. Aturan main

1. **Proposal final = kontrak.** Semua gap diselesaikan dengan salah satu cara:
   - **[KODE]**: kode diubah agar sesuai proposal. Boleh dikerjakan kapan saja.
   - **[SEMHAS]**: kode dipertahankan (lebih tepat atau lebih realistis), lalu **laporan
     Semhas/skripsi** menjelaskan perubahan dari proposal beserta alasannya (Bab III revisi dan Bab IV).
   - **[DATA]**: butuh menjalankan ulang pipeline (API key, server, biaya). Tidak bisa diselesaikan di sandbox.
2. Semua angka hasil lama (Phase 9–13 di `AGENTS.md`/`PROGRESS.md`) **tidak valid lagi** setelah
   Phase 16. Lihat [§4](#4-hasil-lama-yang-tidak-valid--wajib-dijalankan-ulang). Jangan kutip angka lama di laporan Semhas.
3. Rujukan "Pers. x.y", "Subbab x.y", dan "Tabel x.y" mengacu ke **PDF proposal final**.

**Legenda status:** ✅ selesai · 🟡 selesai di kode, menunggu run [DATA] · ⏳ belum dikerjakan · 📝 perlu ditulis di laporan Semhas

---

## 0.1 Status infrastruktur (per 2026-09-27)

⚠️ **Server cloud lama (`144.126.136.57`) sudah mati** karena tidak diperpanjang. Semua yang hanya ada di server dianggap **hilang**:

| Aset | Status | Dampak / pengganti |
|---|---|---|
| ChromaDB + BM25 index (`data/processed/chroma_db`, `bm25_index`) | ❌ hilang | Dibangun ulang lewat R3 (memang wajib karena chunking berubah) |
| Cache LlamaParse (`data/llama_cache`) | ❌ hilang | **Tidak dibutuhkan lagi**: re-ingest memakai PyMuPDF (keputusan X1). Hanya dibutuhkan untuk ablation chunking Markdown (R6c, opsional) |
| Model IndoBERT gate (`data/classifier/indobert_gate/`) | ❌ hilang | Dilatih ulang lewat R4 (memang wajib karena split berubah) |
| File hasil evaluasi `data/audit_results/eval_*.json` Phase 11–13 | ❌ hilang | Sudah tidak valid (§4); diganti hasil R6 |
| MLflow runs, riwayat audit PostgreSQL, dashboard Grafana | ❌ hilang | Tidak dibutuhkan untuk Semhas; MLflow opsional (`--no-mlflow`) |
| Dokumen **T&C GoPay** (sumber 121 klausul) | ❌ tidak ada di repo | Unduh ulang dari situs GoPay untuk R7. **Catat tanggal akses dan versinya**, karena bisa berbeda dari versi April 2026 |
| Model GPT fine-tuned `ft:gpt-4.1-mini-2025-04-14:novan:sop-gate:DaNe3Ai9` | ✅ masih di akun OpenAI | Bisa dipakai lewat `GPT_FINETUNED_MODEL_ID`; tapi dilatih dengan split lama (bocor ke test set baru), jadi R5 tetap disarankan |
| PDF regulasi (`data/raw/`), dataset gate, golden dataset, seluruh kode | ✅ ada di repo | — |

**Runbook §5 sekarang dijalankan di laptop** (atau server baru), bukan di server lama.

**Keputusan X1 (2026-09-27): ekstraktor PDF = PyMuPDF** ✅ diputuskan mahasiswa dan diimplementasikan (item E1 di §2).
- `ingest.py` memakai PyMuPDF secara default (`--extractor pymupdf`); LlamaParse tetap tersedia lewat `--extractor llamaparse`.
- Upload dokumen (`POST /audit/upload`) juga memakai PyMuPDF secara default (`PDF_EXTRACTOR=pymupdf`).
- Sesuai proposal (Fase 1 dan Step 3), sehingga S-12 pindah dari [SEMHAS] ke [KODE]. `LLAMA_CLOUD_API_KEY` tidak lagi wajib (D2 selesai).

---

## 1. Ringkasan cepat

| Kategori | Jumlah | Status |
|---|---|---|
| Gap diperbaiki di kode (Phase 16) | 26 | ✅ / 🟡 (perlu run ulang) |
| Pekerjaan [DATA] di server | 10 langkah (R1–R8, R6b, R6c) | ⏳ lihat [§5 Runbook](#5-runbook--urutan-menjalankan-ulang-di-server) |
| Item revisi untuk laporan Semhas | 27 (25 perlu ditulis; S-12 sudah diselesaikan di kode, S-26 sudah sesuai) | 📝 lihat [§3](#3-daftar-revisi-untuk-laporan-semhas-semhas) |
| Utang teknis yang ditemukan | 4 | ⏳ lihat [§6](#6-utang-teknis-di-luar-cakupan-gap) |

---

## 2. Gap yang sudah diperbaiki di kode [KODE]

Semua item di tabel ini **menyelaraskan kode dengan proposal final tanpa mengubah teks proposal**.

| ID | Gap (sebelum) | Rujukan proposal | Perubahan | File utama | Verifikasi | Status |
|---|---|---|---|---|---|---|
| **K1** | MRR dan Hit Rate@K **selalu 0** karena bug: `evaluation_runner` membaca verdict `dict` memakai `getattr`/`hasattr`, sehingga `retrieved_articles` kosong. Status BI/OJK per klausul juga selalu `UNCLEAR`. | Subbab 3.5.6, Pers. 2.32–2.33 | `build_result()` membaca dict dengan benar. MRR/Hit@K dihitung dari **metadata chunk** (`pasal_number` + kode regulasi) pada Top-K agen regulator yang sesuai, memakai `violated_articles` golden sebagai **qrels tingkat pasal** (anotasi manual chunk-ke-query). | `src/evaluation_runner.py` | `src/tests/test_evaluation_runner.py` | 🟡 |
| **K2** | BI dan OJK **tidak paralel**: `async def` berisi panggilan LLM sinkron, sehingga `asyncio.gather` berjalan berurutan. | Abstrak, RM2, Tujuan 2, Step 9–11 | `asyncio.to_thread(agent.analyze, ...)` | `src/agents/coordinator.py` | Test: 2 agen × 0,4 dtk selesai < 0,7 dtk | 🟡 (ukur ulang latensi) |
| **K3** | Belum ada hierarchical chunking. Yang ada `MarkdownNodeParser` (heading LlamaParse), tanpa metadata bab/bagian/huruf. | Subbab 3.3.1, 3.4.3; BAB 1 (novelty) | Modul baru `HierarchicalChunker`: unit chunk = Pasal; pecah per kelompok Ayat jika > 1.800 karakter; breadcrumb hierarki di awal teks chunk; metadata `regulator, document, bab, bagian, paragraf, pasal, ayat, huruf, section`; bagian PENJELASAN ditandai `section=penjelasan` dan entri "Cukup jelas." dibuang. Jadi default `ingest.py`; `--chunker markdown` untuk baseline ablation. | `src/retrieval/hierarchical_chunker.py`, `src/ingest.py` | 7 unit test; diuji pada ketiga PDF asli: nomor Pasal berurutan tanpa celah (PBI 22/23: 122, PBI 23/6: 276, POJK 22: 125) | 🟡 (re-ingest) |
| **K4** | Hybrid hanya jalan jika klausul memuat nomor pasal/kode regulasi, sehingga hampir semua klausul SOP **dense-only**. Mode α = 1,0 (BM25 saja) tidak ada di proposal. | Pers. 3.1–3.2, Subbab 3.4.7, Step 8–10 | Audit klausul **selalu** memakai weighted RRF (Pers. 3.2) dengan α = 0,7 (ada identifikasi regulasi) atau 0,3 (konseptual). `relevance_score` dinormalisasi: RRF·(κ+1) ∈ (0,1]. Switch ablation `RETRIEVAL_STRATEGY=query_aware\|rrf_equal\|dense` (default `query_aware` = proposal). | `src/retrieval/hybrid_retriever.py`, `src/agents/base_agent.py` | `test_retrieval_and_agents.py` | 🟡 |
| **K6a** | Prompt agen hanya mengizinkan 4 status; NEEDS_REVIEW hanya muncul sebagai fallback parse; UNCLEAR tidak pernah jadi status final. | Tabel 3.6 (6 kelas) | Prompt BI/OJK memuat definisi operasional NEEDS_REVIEW dan UNCLEAR dari Tabel 3.6. Teks rusak/garbled → `UNCLEAR` (sebelumnya `NOT_ADDRESSED`). Status tidak dikenal → `NEEDS_REVIEW`. | `bi_specialist.py`, `ojk_specialist.py`, `base_agent.py`, `rag_service.py`, `query_analyzer.py` | unit test | 🟡 |
| **K6b** | Evaluasi hanya 4 kelas (NEEDS_REVIEW→NON_COMPLIANT, UNCLEAR→NOT_ADDRESSED). | Tabel 2.4–2.5, Subbab 2.11 | Runner melaporkan **dua skema**: `metrics_6class` (6 kelas proposal, tanpa peleburan) dan `metrics` (4 kelas lama, untuk pembanding). | `src/evaluation_runner.py` | unit test | 🟡 |
| **M1** | Conflict Resolver: `HIERARCHY`, `RESOLUTION_PRINCIPLES`, `clause_category` tidak pernah dipakai. PARTIALLY+PARTIALLY bisa berubah menjadi COMPLIANT (melanggar Φ). | Pers. 2.26, Subbab 3.5.5 | Φ diimplementasikan persis: vBI = vOJK → vBI; berbeda → argmax π. π = urutan keparahan `NON_COMPLIANT > PARTIALLY > NEEDS_REVIEW > COMPLIANT > NOT_ADDRESSED > UNCLEAR` (prinsip 4, "standar ketat"). Prinsip 2–3 (OJK konsumen / BI transaksi) menentukan `primary_regulator` untuk urutan rekomendasi. Validasi pra-Φ: PARTIALLY tanpa pelanggaran **dan** tanpa `missing_elements` → COMPLIANT. Kode mati dihapus. | `src/agents/conflict_resolver.py` | 45 kasus test (semua pasangan status) | 🟡 |
| **M2** | Pilihan regulator (BI Only / OJK Only) diabaikan: kedua agen selalu jalan dan status final dari keduanya. `top_k` request tidak diteruskan. | Step 2 & 10, Subbab 3.5.4 | Hanya agen terpilih yang dijalankan (`resolve_single`, Φ trivial). `top_k` diteruskan ke retrieval. | `coordinator.py`, `conflict_resolver.py`, agen | unit test | ✅ |
| **M3a** | Default gate `rule_based`, threshold 0,8 dengan logika `is_sop or conf < 0.8` (hanya menolak jika yakin ≥ 0,8 bukan SOP). | Tabel 3.11, Pers. 2.17, Step 5–6 | Default `SOP_GATE_MODEL=indobert` (fallback otomatis ke rule-based jika model belum dilatih); δ(q) = 1[P(klausul \| q) ≥ 0,5]. | `backend/app/config.py`, `rag_service.py`, `sop_gate.py`, `docker/.env.example` | `backend/tests/test_gate_and_output.py` | 🟡 (ubah `.env` server) |
| **M3c** | Status penolakan gate bernama `NOT_SOP_CLAUSE`. | Tabel 3.8, Step 5 | Menjadi `NOT_REGULATION_CLAUSE` (+ `gate_decision`); alias lama tetap dipetakan. | `rag_service.py`, `audit.py` | test | ✅ |
| **M4a** | Split gate 118/17/24 (≈74/11/15), bukan 80/10/10. Validation file GPT FT = test set `evaluate_gates`. | Subbab 3.1.2, 3.4.4 | Fungsi bersama `split_80_10_10` (stratified, seed 42) → 127/16/16. GPT FT hanya mengunggah partisi train + val; test tidak pernah dikirim ke OpenAI. | `src/classifier/data_split.py`, `train_indobert.py`, `train_gpt_finetune.py`, `evaluate_gates.py` | verifikasi ukuran split | 🟡 (latih ulang) |
| **M4b** | Default model GPT fine-tune di fungsi `train()` = `gpt-5.4-mini`, padahal yang dilaporkan `gpt-4.1-mini`. | Tabel 3.10 | Default `gpt-4.1-mini-2025-04-14`. | `train_gpt_finetune.py` | — | ✅ |
| **M5** | Evidence trail berisi ringkasan agen, bukan pasal Top-K dengan skor. Sitasi LLM tidak diverifikasi. | Subbab 3.3.3, Tabel 3.7 (Evidence Trail ⊆ Top-K) | Verdict agen memuat `evidence` (rank, regulator, dokumen, bab, bagian, pasal/ayat, `relevance_score`, cuplikan). Setiap `violated_article` diberi `grounded` (True jika pasal yang dikutip ada di Top-K). Runner melaporkan **citation grounding rate**. Response API menambah `evidence_trail`, `gate_decision`, `analysis_mode`, `retrieval_mode` (opsional, kompatibel dengan frontend). | `base_agent.py`, agen, `rag_service.py`, `models/audit.py`, `audit.py`, `evaluation_runner.py` | unit test | 🟡 |
| **M6** | Risk score dihitung di dua tempat dengan rumus berbeda; `CRITICAL` dipetakan ke 0,5. | Tabel 3.7 (heuristik) | Satu sumber: `ConflictResolverAgent._calculate_risk`. Peta API: LOW 0,25 / MEDIUM 0,5 / HIGH 0,75 / CRITICAL 1,0. | `rag_service.py`, `audit.py`, `backend/tests/test_rag_service.py` | test | ✅ |
| **T1** | ChromaDB default L2. | Subbab 3.3.2 (cosine) | Collection dibuat dengan `hnsw:space=cosine`. | `src/ingest.py` | — | 🟡 (re-ingest) |
| **G1** | Tiga versi golden dataset saling bertentangan (YAML 9 sampel basi; runner vs API beda teks BAB2-01). | Subbab 3.1.4, Tabel 3.4 | `data/golden_dataset.yaml` = **sumber tunggal** (12 klausul; teks versi runner yang dipakai evaluasi). Dibaca oleh runner dan `GET /evaluation/golden-dataset`. | `data/golden_dataset.yaml`, `evaluation_runner.py`, `api/v1/evaluation.py` | test | ✅ |
| **B1** | Ingest: dokumen dari cache LlamaParse kehilangan `source_file`/`regulator` karena cache disimpan sebelum metadata diisi. Chunk dari cache jadi tanpa kode regulasi. | Subbab 3.4.3 | Metadata diisi ulang saat cache hit. | `src/ingest.py` | uji ingest end-to-end (mock embedding) | 🟡 (re-ingest) |
| **B2** | `PBI_230621.pdf` tidak dikenali mapping nama file, sehingga `regulation_code` kosong. | Tabel 3.1 | Mapping ditambahkan. | `src/retrieval/metadata_extractor.py` | verifikasi 3 file | 🟡 (re-ingest) |
| **E1** | Ekstraksi PDF memakai LlamaParse (berbayar, butuh API key), bukan PyMuPDF. Cache LlamaParse ikut hilang bersama server. | Gambar 3.4 Fase 1, Subbab 3.5.4 Step 3 | Modul `src/pdf_extractor.py` (PyMuPDF). `ingest.py --extractor pymupdf` jadi default; `--extractor llamaparse` opsional (key hanya diperiksa di mode ini). Upload dokumen: PyMuPDF default (`PDF_EXTRACTOR`), LlamaParse bila `PDF_EXTRACTOR=llamaparse`, pypdf hanya cadangan bila PyMuPDF tidak terpasang. `pymupdf>=1.24.0` ditambahkan ke kedua requirements. | `src/pdf_extractor.py`, `src/ingest.py`, `backend/app/api/v1/audit.py`, `backend/app/config.py`, `requirements.txt`, `backend/requirements.txt`, `docker/.env.example` | **Ingest end-to-end sungguhan** di sandbox (PyMuPDF → chunker → ChromaDB cosine → BM25; embedding mock): BI 556 chunk, OJK 292 chunk, tanpa `LLAMA_CLOUD_API_KEY`. Test upload pada PDF asli. | 🟡 (R3 dengan embedding asli) |
| **B4** | RRF menggabungkan skor chunk **berbeda** karena kunci dokumen = 80 karakter pertama; breadcrumb hierarki membuat prefiks sama antar-pasal. Ditemukan saat uji ingest end-to-end (3 chunk berbeda sama-sama `relevance_score` 1,0). | Pers. 3.2 | Kunci dokumen = SHA-1 seluruh isi chunk. | `src/retrieval/hybrid_retriever.py` | Test regresi (gagal di kode lama, lulus di kode baru) | ✅ |
| **B5** | Regresi dari Phase 16: `ingest.py` membaca `CHROMADB_PERSIST_DIR` dari `.env` lokal yang berisi path container `/app/...` → di macOS gagal `Read-only file system (os error 30)` (run lokal 2026-09-27). | — | `src/storage_paths.py::resolve_chroma_dir`: env dipakai hanya bila direktorinya bisa dibuat/ditulis; jika tidak, kembali ke `data/processed/chroma_db` dengan peringatan. Dipakai `ingest.py` dan `evaluation_runner.py`. | `src/storage_paths.py`, `src/ingest.py`, `src/evaluation_runner.py` | `src/tests/test_storage_paths.py` | ✅ |
| **B6** | `train_indobert.py` gagal di env conda yang memasang TensorFlow + Keras 3 (`transformers` ikut memuat TF). | — | `USE_TF=0` / `TRANSFORMERS_NO_TF=1` di-set sebelum import `transformers` (training & inferensi gate). | `train_indobert.py`, `sop_gate.py` | uji import | ✅ |
| **P1** | Prompt BI/OJK tidak punya aturan prioritas antara "pelanggaran aktif → NON_COMPLIANT" dan "cakupan tidak lengkap → PARTIALLY". Checklist `BALANCE_LIMIT` bahkan memuat keduanya, sehingga klausul satu-tier bernilai melanggar (BAB4-01/02) berganti label antar-run. | Tabel 3.6 (Partially = mematuhi *sebagian*) | Aturan PRIORITAS di kedua prompt: jika semua ketentuan yang dinyatakan klausul bertentangan (tidak ada bagian yang sesuai) → NON_COMPLIANT; sub-elemen yang tidak disebut bukan "bagian yang sesuai". Aturan `BALANCE_LIMIT` / `TRANSACTION_LIMIT` diberi syarat "hanya bila nilainya sesuai". Tidak ada contoh baru yang meniru klausul uji. | `bi_specialist.py`, `ojk_specialist.py` | perlu R6 ulang (`--repeat 3`) | 🟡 |
| **V1** | Satu run evaluasi pada n = 12 sangat sensitif terhadap variasi LLM (satu klausul berubah = ±0,167 recall NC). | Subbab 3.5.6 | `evaluation_runner.py --repeat N` → rata-rata ± SD metrik utama + daftar klausul yang tidak stabil (`repeat_*.json`). Hasil per klausul kini menyertakan diagnostik agen (status, reasoning, pelanggaran + grounded, missing_elements, resolusi Φ). | `src/evaluation_runner.py` | 2 unit test | ✅ |
| **B7** | Chunker: baris rujukan yang terpotong ("…dimaksud pada ayat⏎(1) dan/atau ayat (3) dikenai…") terbaca sebagai ayat baru → label ayat salah (mis. POJK Pasal 69 "Ayat 1-1") dan batas pemecahan chunk bergeser. 105 dari 1.046 pasal terdampak. Ditemukan saat analisis run 16:22. | Subbab 3.3.1 | Penanda `(n)` polos hanya diterima bila melanjutkan urutan (n = sebelumnya + 1); `Ayat (n)` eksplisit (Penjelasan) cukup lebih besar; huruf diterima bila `a` atau huruf berikutnya. Jumlah chunk tetap 848 (198/358/292); POJK Pasal 69 kini "Ayat 1-7". | `src/retrieval/hierarchical_chunker.py` | 2 test regresi | 🟡 (re-ingest) |
| **B3** | Prompt fallback LLM-only menyebut regulasi yang salah ("POJK 22/POJK.05/2023 … Jasa Keuangan Digital") dan tidak menyebut PBI 22/23/2020. | Batasan Masalah no. 2 | Diganti tiga regulasi korpus dengan judul resmi. | `rag_service.py` | — | ✅ |

**Test:** `python -m pytest src/tests -q` → **85 lulus**. `cd backend && OPENAI_API_KEY=sk-test python -m pytest tests -q` → 164 lulus. 3 gagal + 15 error **sudah ada sebelum Phase 16** (lihat §6, D1).

---

## 3. Daftar revisi untuk laporan Semhas [SEMHAS]

Kode **dipertahankan** untuk item-item berikut. Laporan Semhas (Bab III revisi / Bab IV / Keterbatasan)
wajib menjelaskan perbedaan dari proposal beserta alasannya. Kolom "Tulis di Semhas" berisi draf poin.

### 3.1 Metodologi & formalisasi

| ID | Lokasi di proposal | Tertulis di proposal | Realita / keputusan | Tulis di Semhas | Status |
|---|---|---|---|---|---|
| S-01 (K5) | Pers. 2.23–2.24, Subbab 2.9, Tabel 3.7 | Confidence = softmax posterior P(ĉ \| q, r) dari logit | Confidence adalah **verbalized confidence**: angka yang diisi LLM di JSON. `overall_confidence` = rata-rata BI dan OJK. | Revisi: confidence sebagai skor kepercayaan verbal. Alasan: API Claude tidak menyediakan logprobs, sehingga Pers. 2.24 tidak bisa diterapkan adil ke kedua model ablation. **Tambahkan analisis kalibrasi** (reliability diagram + ECE) di Bab IV. | 📝 |
| S-02 (M3b) | Pers. 2.16–2.18 | IndoBERT: sigmoid + binary cross-entropy | HuggingFace `AutoModelForSequenceClassification` 2 label: softmax + cross-entropy | Ubah notasi ke softmax 2 kelas, atau beri catatan ekuivalensi matematis sigmoid ↔ softmax 2 kelas. | 📝 |
| S-03 (M6) | Subbab 3.3.3 (contoh JSON `risk_score: 0.87`) | Risk numerik | Kategorikal LOW/MEDIUM/HIGH/CRITICAL (API memetakan ke 0,25–1,0) | Contoh JSON pakai kategori. Proposal sendiri menyebut risk "heuristik, tidak diformalkan". | 📝 |
| S-04 (K6) | Tabel 3.6, Subbab 3.2.3 | 6 kelas diprediksi LLM (argmax) | LLM memprediksi 6 kelas; teks rusak dideteksi aturan → UNCLEAR. Golden dataset **tidak memiliki** label NEEDS_REVIEW/UNCLEAR, jadi metrik per kelas untuk keduanya tidak terdefinisi (support = 0). | Laporkan macro-F1 atas kelas yang punya support; laporkan juga **deferral rate** (proporsi NEEDS_REVIEW/UNCLEAR) terpisah; jelaskan kaitannya dengan DSS (Batasan 6). | 📝 |
| S-05 (M1) | Pers. 2.26, Subbab 3.5.5 | π berdasar 4 prinsip | π = urutan keparahan (prinsip 4). Prinsip 1 tidak membedakan PBI dan POJK (setara). Prinsip 2–3 menentukan regulator utama untuk urutan rekomendasi. Ada **validasi pra-Φ** (PARTIALLY tanpa bukti → COMPLIANT). | Tuliskan π eksplisit sebagai tabel ordinal + aturan validasi pra-Φ. | 📝 |
| S-06 (K4) | Subbab 3.4.7 | α ∈ {0,3; 0,7} ditetapkan | Sesuai proposal, tapi nilai α **tidak dituning**. | Tambahkan hasil ablation `query_aware` vs `rrf_equal` (α = 0,5) vs `dense` sebagai justifikasi empiris. | 📝 |
| S-07 (K3) | Subbab 3.3.1 | Chunk per Huruf (5 tingkat) | Unit chunk = Pasal; dipecah per kelompok Ayat bila > 1.800 karakter; Huruf disimpan di metadata (`huruf`), bukan chunk terpisah. Bagian Penjelasan ikut di-index (`section=penjelasan`). Tingkat **Paragraf** (ada di PBI/POJK) ikut dicatat. | Jelaskan parameter `max_chars=1800`, alasan tidak memecah per Huruf (huruf kehilangan konteks kalimat induk), perlakuan Penjelasan, dan tingkat Paragraf. | 📝 |
| S-08 | Tabel 3.2, Subbab 3.4.3 | Estimasi ±962 / ±628 / ±1.031 chunk (N ≈ 2.621) | Ingest PyMuPDF + chunker hierarkis (uji sandbox 2026-09-27): **BI 556 chunk (PBI 22/23: 198, PBI 23/6: 358), OJK 292 chunk, total 848** (termasuk Penjelasan). Jumlah chunk tidak bergantung pada embedding, jadi angka ini seharusnya sama saat R3. | Ganti Tabel 3.2 dengan 198 / 358 / 292 (N = 848); konfirmasi dari log R3. | 📝 |
| S-09 (M4) | Tabel 3.3, Subbab 3.1.2 | Positif gate mencakup GoPay T&C & klausul Dummy | Klausul yang **dievaluasi** (12 golden + GoPay) ikut dilatih di gate → gate "sudah melihat" data uji RAG. n uji gate hanya 16. | Nyatakan di Keterbatasan; laporkan **Wilson CI 95%** (1,000 pada n = 16 → batas bawah ≈ 0,81). Opsional: stratified 5-fold CV. | 📝 |
| S-10 | Tabel 3.4 | BAB III 4 NC (pengaduan), BAB IV 2 NC (saldo & transaksi) | Golden aktual: 3 NC pengaduan/klausula (BAB3-01..03) + 3 NC saldo/transaksi (BAB4-01..03). | Perbaiki tabel komposisi: 2 NA + 4 PC + 3 NC + 3 NC = 12. | 📝 |
| S-11 | Tabel 3.4 | Label "Netral" | Dipakai sebagai `NOT_ADDRESSED` | Ganti "Netral" → Not Addressed. | 📝 |

### 3.2 Teknologi (Tabel 3.11, Gambar 3.4–3.5, Subbab 3.5.4)

| ID | Tertulis di proposal | Realita / keputusan | Alasan dipertahankan | Status |
|---|---|---|---|---|
| S-12 | Ekstraksi PDF dengan **PyMuPDF** (Fase 1, Step 3) | ~~LlamaParse~~ → **sudah PyMuPDF** sejak 2026-09-27 (E1). Tidak perlu revisi; cukup sebut LlamaParse sebagai opsi pembanding di ablation chunking (R6c). | — | ✅ |
| S-13 | **Elasticsearch** BM25 (Fase 3, Step 9) | `rank_bm25` BM25Okapi in-memory (pickle), k1 = 1,5, b = 0,75 | Korpus 848 chunk; ES menambah service JVM tanpa manfaat. Tabel 3.11 proposal sendiri menyebut BM25Okapi. | 📝 |
| S-14 | **Weights & Biases** di panel monitoring | Tidak dipakai; MLflow + Prometheus + Grafana | IndoBERT hanya 1 epoch; MLflow cukup untuk eksperimen. | 📝 |
| S-15 | **LlamaIndex** sebagai orkestrator pipeline multi-agent | LlamaIndex untuk index/retriever/embedding; orkestrasi memakai asyncio (`CoordinatorAgent`) | Lebih transparan dan langsung memetakan Pers. 2.25–2.26. | 📝 |
| S-16 | — (tidak disebut) | Pre-filter deterministik tahap 2: `is_noise_clause` (header, disclaimer, boilerplate HKI/pilihan hukum/severability) → `NOT_ADDRESSED` tanpa LLM; greeting/out-of-scope → tanpa LLM | Menghemat biaya. **Wajib diungkap:** laporkan berapa klausul GoPay yang dilabeli aturan vs LLM (memengaruhi 99 NOT_ADDRESSED). | 📝 |
| S-17 | — | **Checklist prompting** (sub-elemen per topik: DATA_PRIVACY, COMPLAINT_SLA, PROHIBITED_CLAUSE, BALANCE_LIMIT, …) | Faktor utama deteksi PARTIALLY_COMPLIANT. Masukkan sebagai teknik prompting di Bab III. | 📝 |
| S-18 | — | `COMPLIANCE_RULES` hardcode (batas saldo 2 jt / 10 jt, transaksi 20 jt) disisipkan ke prompt BI | Nyatakan sebagai *domain knowledge injection* + keterbatasan (angka sama dengan skenario golden, bisa membuat kelas LIMITS terlihat lebih baik dari aslinya). | 📝 |
| S-19 | — | Mode fallback **LLM-only** jika ChromaDB kosong/gagal (`analysis_mode=llm_only`) | Evaluation runner sekarang **berhenti** jika vector store tidak termuat (`check_retrieval_ready`). Sebut di arsitektur. | 📝 |
| S-20 | — | Fitur produksi: RBAC JWT (basic/advanced), cache 24 jam, cost tracker, rate limiter, Celery + Redis, nginx | Cukup satu baris di Tabel 3.11. | 📝 |
| S-21 | Struktur output Subbab 3.3.3 | Response memakai `final_status`, `overall_confidence`, `evidence_trail[{agent, regulator, document, bab, pasal, relevance_score, rank}]`, `gate_decision` | Nama field sedikit berbeda dari `verdict`/`confidence`; struktur semantik sama. | 📝 |
| S-22 | Step 9: K = 5 | K = 5 **per regulator** (Top-K(R_BI, q) dan Top-K(R_OJK, q)); fetch awal 3·K per daftar sebelum fusi | Perjelas. | 📝 |

### 3.3 Kesalahan faktual di proposal (ditemukan dari PDF regulasi resmi)

| ID | Lokasi | Tertulis | Fakta (PDF resmi di `data/raw/`) | Status |
|---|---|---|---|---|
| S-23 | Batasan Masalah no. 2, Subbab 3.1.1, Daftar Pustaka | PBI 23/6/PBI/2021 tentang "Penyelenggaraan Pemrosesan Transaksi Pembayaran" | Judul resmi: **"Penyedia Jasa Pembayaran"** | 📝 |
| S-24 | Subbab 3.3.1 | PBI 23/6/PBI/2021 memiliki **18 bab** | **11 BAB** (PBI 22/23/2020: 12 BAB; POJK 22/2023: 13 BAB) | 📝 |
| S-25 | Subbab 3.1.1 | "batas nominal **transaksi** unverified Rp2 jt dan verified Rp10 jt … batas transaksi bulanan Rp20 jt untuk akun **verified**" | Pasal 160 ayat (1): batas **nilai uang elektronik yang disimpan (saldo)**, unregistered Rp2 jt / registered Rp10 jt. Ayat (2): batas **nilai transaksi** Rp20 jt/bulan untuk **semua** uang elektronik. | 📝 |
| S-26 | Tabel 3.2 | PBI 23/6 = 215 halaman, POJK = 131 halaman, PBI 22/23 = 96 halaman | Cocok dengan PDF (96 / 215 / 131). ✅ tidak perlu diubah. | ✅ |
| S-28 | (metodologi evaluasi) | — | Prompt disetel berulang kali dengan melihat hasil pada golden 12 klausul yang sama (Phase 11–16). Contoh di prompt OJK ("SLA 60 hari … maksimal 20 hari kerja") mirip klausul uji BAB3-02. | **Wajib diungkap** di Keterbatasan: golden dataset berfungsi sebagai set pengembangan, bukan hold-out murni. Mitigasi: laporkan hasil `--repeat`, dan idealnya evaluasi pada set hold-out baru (TODO-B1, T&C e-wallet lain) yang tidak pernah dipakai menyetel prompt. | 📝 |
| S-27 | Catatan dokumen internal (`AGENTS.md`, `PROGRESS.md`, draf skripsi) | "Hit Rate@5 = 0 karena limitasi metodologi string matching" | Penyebabnya **bug K1**. Hapus klaim ini dan ganti dengan hasil run ulang. | 📝 |

---

## 3.4 Hasil awal dari sandbox (belum hasil final)

Dijalankan 2026-09-27 tanpa API key, pada index hasil ingest PyMuPDF + chunker hierarkis. **Belum boleh dilaporkan sebagai hasil sistem**: dense retrieval memakai embedding mock, jadi hanya komponen sparse yang bermakna.

| Pengujian | Hasil | Catatan |
|---|---|---|
| Gate rule-based, split 80/10/10 (n uji 16) | Accuracy 0,875; F1-w 0,875; precision "bukan klausul" 0,889; recall "klausul" 0,857 | Final untuk varian rule-based (tidak butuh API) |
| **Run lokal pertama** (laptop, 2026-09-27, GPT-5.4-mini, `query_aware`) — ⚠️ **memakai index LAMA** (1.590 / 1.031 vektor, chunking Markdown) karena re-ingest gagal (B5) | Accuracy 0,833 (CI95 0,552–0,953); Macro-F1 6 kelas 0,867; Recall NC 0,667 (broad 1,000); F1 NC 0,800; F1 PC 0,800; NA 1,000; latensi rata-rata **3,5 dtk** (dulu 9,6 dtk → efek K2 paralel); MRR/Hit@K 0 dan 0 sitasi diperiksa | Salah: BAB3-02 (SLA 60 hari) dan BAB4-02 → PARTIALLY, seharusnya NON_COMPLIANT. MRR 0 dan grounding kosong diduga karena index lama tidak memiliki metadata `pasal_number` yang dipakai qrels; **ulang setelah re-ingest**. File: `data/audit_results/eval_openai_gpt-5.4-mini_query_aware_20260927_161143.json` (di laptop). |
| **R6 GPT-5.4-mini ×3 (`--repeat 3`)** — laptop 2026-09-27 16:22–16:24, index baru, **setelah P1**, sebelum B7. **Hasil valid pertama sesuai konfigurasi proposal** | Accuracy 6 kelas **0,917 ± 0,083** (1,000 / 0,833 / 0,917); Macro-F1 6 kelas **0,933 ± 0,067**; **Recall NC 0,833 ± 0,167** (1,000 / 0,667 / 0,833); F1 NC 0,903 ± 0,100; F1 PC 0,896 ± 0,100; **MRR 0,575; Hit@3 0,50; Hit@5 0,80** (deterministik, SD 0); citation grounding 1,0 (7–10 sitasi/run); latensi **4,4 ± 0,1 dtk** | Lihat analisis kesalahan §3.5. File: `data/audit_results/eval_openai_gpt-5.4-mini_query_aware_20260927_162210.json`, `…_162301`, `…_162355`, `repeat_…_162210_x3.json` (di repo). Target Recall NC ≥ 0,90 tercapai di 1 dari 3 run. Hit@5 0,80 < target 0,85. |
| **Run lokal kedua — index BARU** (laptop, 2026-09-27 16:15, GPT-5.4-mini, `query_aware`, PyMuPDF + hierarkis, 556/292 chunk) — hasil pertama dengan konfigurasi retrieval sesuai proposal; **sebelum** perbaikan P1 | Accuracy 0,667 (CI95 0,391–0,862); Macro-F1 6 kelas 0,676; **Recall NC 0,333** (broad 0,833); F1 NC 0,500; F1 PC 0,727; F1 NA 0,800; **MRR 0,575; Hit@3 0,50; Hit@5 0,80**; citation grounding 1,0 (3 sitasi); latensi 3,9 dtk | Salah: BAB3-01 (jam pengaduan) → PC; BAB3-03 (pembekuan akun) → NA; BAB4-01, BAB4-02 (batas saldo) → PC. Retrieval kini valid (bug K1 terkonfirmasi selesai). Penurunan recall NC → konflik aturan prompt, diperbaiki P1. File: `eval_openai_gpt-5.4-mini_query_aware_20260927_161541.json` (laptop). |
| **R6 GPT-5.4-mini ×3 — pasca-B7 (FINAL untuk Bab 4)** — laptop 2026-09-27 16:42–16:44 | Accuracy 6 kelas **0,917 ± 0,083** (0,833 / 1,000 / 0,917); Macro-F1 0,933 ± 0,067; Recall NC ketat 0,833 ± 0,167 (broad 1,000); **MRR 0,583; Hit@3 0,60; Hit@5 0,80** (BAB3-01 naik rank 4→3); grounding 26/26; **citation accuracy 15/18 = 0,833** (hanya BAB3-03 salah: Pasal 36/55 bukan 46); ECE 0,058; conf benar 0,975 vs salah 0,970; latensi **3,2 ± 0,3 dtk** | Tidak stabil: BAB3-02 (PC/NC/NC — PC sambil mengutip Pasal 75, alasan sub-elemen lain tidak disebut) dan BAB4-02 (PC/NC/PC). File `…_164235/164312/164347.json`, `repeat_…_164235_x3.json`. |
| **R6b Ablation `dense` ×3** (GPT-5.4-mini, tanpa BM25) — laptop 2026-09-27 17:40–17:42 | Accuracy 6 kelas **0,972 ± 0,048** (CI95 gabungan 0,858–0,995); Macro-F1 0,978 ± 0,039; Recall NC ketat 0,944 (broad 1,000); **MRR 0,590; Hit@3 0,60; Hit@5 0,80**; grounding 25/25; citation accuracy **12/18 = 0,667**; ECE 0,004; latensi 4,5 ± 0,2 dtk | Rank per klausul: BAB2-01 1 · BAB2-02 5 · **BAB2-03 2** · BAB2-04 5 · **BAB3-01 –** · BAB3-02 1 · BAB3-03 – · BAB4-01..03 1. Tidak stabil: BAB3-01 (NC/PC/NC). File `eval_openai_gpt-5.4-mini_dense_20260927_174015/174108/174205.json`, `repeat_…_174015_x3.json`. |
| **R6b Ablation `rrf_equal` ×3** (α = 0,5) — laptop 2026-09-27 17:43–17:45 | Accuracy 6 kelas **0,972 ± 0,048**; Macro-F1 0,968 ± 0,056; Recall NC ketat 0,944 (broad 0,944); **MRR 0,525; Hit@3 0,60; Hit@5 0,70**; grounding 24/24; citation accuracy 14/18 = 0,778; ECE 0,002; latensi 4,6 ± 0,3 dtk | Rank: BAB2-01 1 · **BAB2-02 –** · BAB2-03 – · BAB2-04 4 · BAB3-01 2 · BAB3-02 1 · BAB3-03 – · BAB4-01 1 · BAB4-02 2 · BAB4-03 1. Tidak stabil: BAB3-01 (NC/NC/**NA**). File `eval_openai_gpt-5.4-mini_rrf_equal_20260927_174307/174401/174453.json`, `repeat_…_174307_x3.json`. |
| **Interpretasi R6b (untuk Bab 4)** | Retrieval: `query_aware` (α = 0,3 untuk semua klausul golden) ≈ `dense` (MRR 0,583 vs 0,590, Hit@5 sama 0,80) > `rrf_equal` (0,525; 0,70). Menaikkan bobot BM25 ke 0,5 **menurunkan** peringkat. Dense & hybrid saling melengkapi: dense menemukan BAB2-03 (privasi singkat) yang gagal di hybrid; hybrid menemukan BAB3-01 yang gagal di dense. | Klasifikasi: ketiga strategi berbeda ≤ 2 dari 36 prediksi dan CI95 akurasi tumpang-tindih (query_aware 0,782–0,971 vs 0,858–0,995) → **tidak ada bukti strategi retrieval mengubah verdik** pada 12 klausul; variasi didominasi ketidakstabilan LLM di klausul batas (BAB3-01/02, BAB4-02). Citation accuracy tertinggi di `query_aware` (0,833 vs 0,667 dense). **Narasi Bab 4 harus mengikuti ini** — jangan klaim hybrid unggul dalam akurasi. Catatan: label `retrieval_setup` run `dense` tertulis "hybrid" (bug label, per-hasil `retrieval_mode = dense` benar); diperbaiki untuk run berikutnya. |
| **R6 Claude Haiku 4.5 ×3** — 2026-09-27 16:43 | ❌ **TIDAK VALID** — semua 36 panggilan gagal: `Could not resolve authentication method` (ANTHROPIC_API_KEY tidak terbaca). Akurasi 0 dan latensi 0,55 dtk adalah artefak error. | Ulangi dengan `ANTHROPIC_API_KEY` ter-export. Sejak D6 selesai, run seperti ini langsung berhenti dengan exit 1. |
| **IndoBERT (R4)** — split 80/10/10, 1 epoch, batch 8, lr 2e-5 | Accuracy **0,938**; F1-w 0,938; precision bukan-klausul 1,000; recall bukan-klausul 0,889; recall klausul 1,000 | 1 bukan-klausul diloloskan. `data/classifier/indobert_metrics.json`. |
| **BM25 saja** pada 10 klausul golden yang punya qrels (Top-10 per regulator) | **MRR@10 = 0,520; Hit@3 = 0,60; Hit@5 = 0,70; Hit@10 = 0,70** | Rank pasal relevan: BAB2-01 → 1, BAB2-02 → –, BAB2-03 → –, BAB2-04 → 5, BAB3-01 → 1, BAB3-02 → 2, BAB3-03 → –, BAB4-01 → 1, BAB4-02 → 2, BAB4-03 → 1. Klausul privasi yang sangat singkat (AES-256, right to erasure) dan klausula pembekuan akun (Pasal 46) tidak ditemukan BM25; diharapkan tertolong oleh dense retrieval. Bisa dipakai sebagai baseline "sparse-only" di Bab IV setelah dikonfirmasi ulang di R6. |

## 3.5 Analisis kesalahan R6 (GPT-5.4-mini ×3)

**Klasifikasi.** 10 dari 12 klausul stabil dan benar di ketiga run. Dua klausul tidak stabil:

| Klausul | Label | Run 1 / 2 / 3 | Temuan dari diagnostik |
|---|---|---|---|
| BAB4-02 (saldo verified Rp500 jt) | NC | NC / **PC** / **PC** | Agen BI menandai PARTIALLY **sambil mencantumkan pelanggaran Pasal 160 ayat (1) (grounded)**, dan reasoning-nya mengakui nilainya melampaui batas. Keluaran agen tidak konsisten dengan aturannya sendiri (prioritas P1). |
| BAB3-02 (SLA 60 hari kerja) | NC | NC / **PC** / NC | Run 2: agen OJK menandai PARTIALLY dengan `violations = []`, padahal reasoning menyebut nilai waktunya tidak sesuai. Inkonsistensi yang sama. |

→ **Sumber kesalahan tersisa = inkonsistensi internal keluaran LLM** (status vs. pelanggaran yang ia tulis sendiri), bukan retrieval. Pasal yang benar (160, 75) ada di peringkat 1 pada ketiga run.

**Retrieval (per klausul, identik di ketiga run).** Rank pasal relevan: BAB2-01 → 1, BAB2-02 → 4, **BAB2-03 → tidak ada**, BAB2-04 → 4, BAB3-01 → 4, BAB3-02 → 1, **BAB3-03 → tidak ada**, BAB4-01/02/03 → 1. Kegagalan ada pada klausul privasi yang sangat singkat (BAB2-03 "right to erasure") dan BAB3-03 (pembekuan akun; qrel POJK Pasal 46 ayat 2 tentang klausul eksonerasi).

**Sitasi.** BAB3-03 dilabeli benar (NC) di ketiga run, tetapi pasal yang dikutip adalah **Pasal 36** (pemasaran) atau **Pasal 51** (masa jeda), bukan Pasal 46. Keduanya ada di Top-5 sehingga `grounded = True`. → **Citation grounding hanya mengukur "pasal ada di konteks", bukan "pasal tepat"**. Untuk Bab IV, tambahkan metrik *citation accuracy* terhadap qrels di samping grounding rate.

**Confidence (S-01).** Rata-rata confidence prediksi benar = 0,977, prediksi salah = 0,977 (3 kesalahan dari 36 prediksi). Verbalized confidence **tidak membedakan** prediksi benar dan salah. Temuan penting untuk analisis kalibrasi (R8).

**Opsi perbaikan inkonsistensi (keputusan terbuka X2, belum dikerjakan):**
- *X2-A — ekstraksi terstruktur + aturan deterministik:* LLM hanya mengeluarkan daftar ketentuan yang dinyatakan klausul beserta `sesuai/bertentangan`, dan status ditentukan aturan Tabel 3.6 di kode. Paling konsisten dan mudah dijelaskan, tetapi mengubah format keluaran agen, dan perlu disetel lagi pada golden set (menambah beban S-28).
- *X2-B — self-consistency (n = 3, voting mayoritas per agen):* biaya dan latensi LLM ×3; sekaligus memberi confidence berbasis proporsi suara (lebih bermakna untuk S-01).
- *X2-C — biarkan:* laporkan rata-rata ± SD dan klausul tidak stabil sebagai keterbatasan.

---

## 3.6 Status penerapan di laporan (repo `rzkynovan/template-proposal-ta-its`, branch `semhas`)

Revisi §3 sudah **ditulis ke LaTeX** di branch `semhas` (2026-09-27). Proposal final di `main` tidak diubah.
Hasil yang belum ada ditandai makro `\menunggu{...}` (merah) — **cari `\menunggu` sebelum Semhas** dan isi dari runbook §5.

| Item | Diterapkan di | Catatan |
|---|---|---|
| S-01 | Bab 2 (paragraf confidence, Pers. ECE `eq:ece`), Tabel 3.7 | Verbalized confidence p̃; ECE di Bab 4.5 |
| S-02 | Bab 2 setelah `eq:bce_loss`; Bab 3 subbab gate | Ekuivalensi softmax 2 logit ↔ BCE |
| S-03, S-21 | Bab 3 Struktur Output | JSON aktual (`final_status`, `overall_confidence`, `evidence_trail{agent,…,rank}`); risk ordinal → numerik |
| S-04 | Bab 3 setelah Tabel 3.6 | Definisi operasional NEEDS_REVIEW / UNCLEAR + kaidah prioritas NC vs PC |
| S-05 | Bab 3 Conflict Resolution | Tabel baru `tab:prioritas-pi`; validasi pra-Φ; prinsip domain = regulator utama |
| S-06 | Bab 3 Query Analyzer | α heuristik + rencana ablation `rrf_equal`/`dense` |
| S-07, S-24 | Bab 3 Struktur Hierarchical Chunking | Kaidah chunker (Pasal, >1.800 kar., breadcrumb, urutan ayat, Penjelasan); 11 BAB |
| S-08 | Tabel 3.2, Pipeline Preprocessing | 198/358/292 = 848 |
| S-09 | Bab 3 dataset gate; Bab 4 Keterbatasan | Split 127/16/16 + kebocoran |
| S-10, S-11 | Tabel 3.4 + narasi golden | 2 NA / 4 PC / 3+3 NC; qrels |
| S-12–S-15 | Tabel 3.11, narasi Gambar 3.4, Step 9, panel Monitoring | PyMuPDF, rank_bm25, tanpa Elasticsearch/W&B, LlamaIndex = index/retriever. **Gambar `arsitektur-multi-agent-rag.png` belum diregenerasi** (masih Elasticsearch/W&B; teks sudah menyebut perbedaannya) |
| S-16–S-19, P1 | Subbab baru `subsec:rancangan-prompt` | Checklist, nilai ambang, kaidah prioritas, pre-filter, NEEDS_REVIEW saat JSON rusak, LLM-only, regulator tunggal |
| S-22 | Step 9 | 3K kandidat → Top-5 per regulator |
| S-23, S-25 | Bab 1 batasan 2, Bab 2, Bab 3.1.1, pustaka.bib | Judul PBI; Pasal 160 (1) saldo vs (2) transaksi |
| S-27 | Bab 3 Evaluasi Kinerja | Catatan string matching diganti qrels, repeat 3, Wilson, citation grounding + accuracy, ECE, deferral rate |
| S-28 | Bab 4 Keterbatasan | Penyetelan prompt pada golden set |
| S-20 | — | Tidak ditulis (fitur produksi, bukan kontribusi penelitian) |
| S-26 | — | Tidak perlu revisi |

**Bab 4 (`konten/4-hasil-pembahasan.tex`)** memakai R6 ×3 GPT-5.4-mini (§3.4). Angka turunan yang dihitung dari JSON R6:
confusion matrix gabungan NC→NC 15, NC→PC 3, PC→PC 12, NA→NA 6; akurasi gabungan 33/36 (Wilson 0,78–0,97);
**citation accuracy 12/18 = 0,667** (Wilson 0,44–0,84); grounding 24/24; **ECE = 0,060** (10 bin, semua 36 prediksi di bin 0,9–1,0).
Bab 4/5 **sudah diperbarui ke hasil pasca-B7 + IndoBERT** (commit `a528392`): MRR 0,583, Hit@3 0,60, citation accuracy 0,833, ECE 0,058, latensi 3,2 dtk. Angka R6 pra-B7 di atas diganti.
`\menunggu` tersisa: GPT FT (R5), dense/rrf_equal (R6b), Claude Haiku ×3 (R6, run pertama gagal auth), GoPay (R7), reliability diagram (R8).
**Bab 5** menjawab RM1–RM3 + saran (X2-A/B, hold-out, anotasi pakar, reranker, dataset gate terpisah).

---

## 4. Hasil lama yang TIDAK VALID — wajib dijalankan ulang

Hasil berikut dihasilkan **sebelum** Phase 16 dan dipengaruhi K1, K2, K3, K4, K6, M1, M4:

| Hasil lama (sumber) | Kenapa tidak valid | Pengganti |
|---|---|---|
| Accuracy 0,750 / Macro-F1 0,774 / Recall NC 1,000 / F1 PC 0,400 (GPT-5.4-mini, Phase 13) | Resolver (M1), prompt 6 kelas (K6), retrieval (K3/K4) berubah | R6 |
| Accuracy 0,667 / Macro-F1 0,600 (Claude Haiku 4.5) | idem | R6 |
| MRR 0 / Hit Rate@3 0 / Hit Rate@5 0 | Bug K1 | R6 |
| Avg latency 9,573 s / 29,098 s | Agen sebelumnya berurutan (K2) | R6 |
| Gate: RuleBased 0,917; IndoBERT 1,000; GPT FT 1,000 (n uji 24) | Split berubah ke 80/10/10 (M4a) | R4, R5 |
| Distribusi GoPay 4 C / 8 PC / 10 NC / 99 NA | Semua komponen di atas berubah | R7 |
| 1.590 vektor BI / 1.031 vektor OJK | Chunking berubah (K3) | R3 |

---

## 5. Runbook — urutan menjalankan ulang (laptop / server baru)

> Server lama sudah mati (§0.1). Jalankan dari root repo di laptop atau server baru; perintah `docker-compose exec … backend` dapat diganti `python src/…` langsung di venv. Perkiraan biaya embedding re-ingest
> 848 chunk × ±300 token ≈ 0,25 jt token × $0,13/1 jt ≈ **< $0,05**. Ekstraksi PyMuPDF gratis dan tidak butuh `LLAMA_CLOUD_API_KEY`.

| # | Langkah | Perintah | Status |
|---|---|---|---|
| R1 | Tarik branch, lalu siapkan `docker/.env` baru dari `docker/.env.example` (default sudah `indobert` / `0.5` / `query_aware`) | `SOP_GATE_MODEL=indobert`, `SOP_GATE_THRESHOLD=0.5`, `RETRIEVAL_STRATEGY=query_aware`. Jika memakai `.env` lama, pastikan tidak lagi berisi `rule_based` / `0.8`, karena `.env` mengalahkan default kode. | ⏳ |
| R2 | Build ulang backend | `cd docker && docker-compose build backend && docker-compose up -d backend` | ⏳ |
| R3 | **Re-ingest PyMuPDF + hierarkis + cosine** | Lokal: `OPENAI_API_KEY=… python src/ingest.py --force` (default `--extractor pymupdf --chunker hierarchical`). Docker: `docker-compose exec backend python /app/src/ingest.py --force`. Pastikan log menunjukkan BI 556 / OJK 292 (S-08). | ⏳ |
| R4 | Latih ulang IndoBERT (split 80/10/10) — ✅ **selesai 2026-09-27** (acc 0,938, lihat §3.4) | `docker-compose exec backend python /app/src/classifier/train_indobert.py` → `data/classifier/indobert_metrics.json` | ⏳ |
| R5 | (Opsional, berbiaya) GPT FT ulang + evaluasi 3 gate. **Rule-based sudah dihitung ulang di sandbox (2026-09-25), split 80/10/10, n uji 16: accuracy 0,875; F1-w 0,875; precision "bukan klausul" 0,889; recall "klausul" 0,857.** Salah 2: 1 klausul GoPay ("GoPay berhak untuk mengubah, menangguhkan…") ditolak, 1 keluhan pengguna ("Saya mau komplain…") diloloskan. | `python /app/src/classifier/train_gpt_finetune.py` lalu `python /app/src/classifier/evaluate_gates.py --mlflow-uri http://mlflow:5000` | ⏳ |
| R6 | Evaluasi utama (ablation LLM) — **pakai `--repeat 3`** dan laporkan rata-rata ± SD | `~/nlp-compliance-rag/scripts/run_ablation.sh` (GPT-5.4-mini vs Claude Haiku 4.5, `query_aware`). Output: `data/audit_results/eval_<provider>_<model>_query_aware_<ts>.json` + MLflow | ⏳ |
| R6b | Ablation retrieval (GPT-5.4-mini) | `RETRIEVAL_STRATEGY=dense python src/evaluation_runner.py --repeat 3 --no-mlflow` dan ulangi dengan `RETRIEVAL_STRATEGY=rrf_equal` | ✅ 2026-09-27 (§3.4) |
| R6c | (Opsional, berbayar LlamaParse) Ablation chunking — baseline Markdown | `CHROMADB_PERSIST_DIR=data/processed_md/chroma_db LLAMA_CLOUD_API_KEY=… python src/ingest.py --force --extractor llamaparse --chunker markdown`, lalu `evaluation_runner.py` dengan `CHROMADB_PERSIST_DIR` yang sama. Baseline Markdown butuh heading dari LlamaParse; dengan PyMuPDF hasilnya praktis satu chunk per halaman. | ⏳ |
| R7 | Audit ulang GoPay T&C (121 klausul) | Unduh ulang PDF T&C GoPay (catat tanggal akses/versi), upload via UI/`POST /audit/upload` lalu `/audit/batch`; catat `analysis_mode` untuk S-16 | ⏳ |
| R8 | Kalibrasi confidence (S-01) | `python scripts/reliability_diagram.py --label <model> <file...>` → `data/audit_results/figures/reliability_<model>.png` | 🟡 GPT selesai (ECE 0,0575, 36/36 di bin 0,9–1,0); Haiku menunggu T2 |

Setelah R1–R8 selesai: perbarui §4, isi angka S-08, dan ganti tabel hasil di `AGENTS.md` / `PROGRESS.md`.

---

## 6. Utang teknis di luar cakupan gap

| ID | Temuan | Dampak | Status |
|---|---|---|---|
| D1 | `backend/tests/test_audit_api.py` memakai `audit_mod.audit_history` (sudah diganti PostgreSQL di Phase 10) → 15 error. `TestMapStatus::test_case_sensitive` bertentangan dengan normalisasi case di `_map_status`. `TestAnalyzeWithRag` (budget, cache) gagal karena input uji `"test clause"` sudah dihentikan gate/pre-check scope sebelum mencapai cache/budget. | 3 gagal + 15 error **sudah ada sebelum Phase 16**; klaim "165/165 test lulus" di dokumen tidak berlaku lagi | ⏳ |
| D2 | `ingest.py` mewajibkan `LLAMA_CLOUD_API_KEY` walau semua PDF sudah di-cache | Selesai lewat E1: key hanya diperiksa bila `--extractor llamaparse` | ✅ |
| D3 | Paket `llama-parse` deprecated (peringatan saat import) | Migrasi ke SDK LlamaCloud baru suatu saat | ⏳ |
| D5 | `train_indobert.py` di conda base gagal: `pyarrow` terlalu lama untuk `datasets` (`module 'pyarrow' has no attribute 'json_'`) — konflik paket env, bukan kode | `pip install -U "pyarrow>=15" datasets`, atau lebih bersih: venv terpisah (`python -m venv venv && pip install -r requirements.txt -r backend/requirements.txt`) | ⏳ |
| D6 | `evaluation_runner.py` tidak gagal cepat saat error API | Run Haiku 16:43 tercatat sebagai hasil (akurasi 0) | ✅ (lihat bawah) |
| D4 | `Field(..., env=...)` di `config.py` deprecated di Pydantic v2 | Hanya peringatan | ⏳ |

---

### D6 — evaluation_runner tidak gagal cepat saat error API ✅ (2026-09-27, T1)
Masalah: jika semua panggilan LLM error (mis. kunci API hilang), runner tetap menulis JSON dengan prediksi `UNCLEAR` dan metrik 0 — mudah terbaca sebagai hasil model.

Perbaikan di `src/evaluation_runner.py`:
- `check_api_keys()` dipanggil sebelum inisialisasi agen: `OPENAI_API_KEY` wajib (embedding), `ANTHROPIC_API_KEY` wajib bila `LLM_PROVIDER=anthropic` → `sys.exit` dengan pesan, tanpa memanggil API dan tanpa menulis file.
- `is_fatal_api_error()` (auth, saldo/kredit habis, `insufficient_quota`, billing) menghentikan loop pada klausul pertama yang gagal.
- Run dengan ≥ 1 error atau klausul tidak lengkap → `"invalid": true`, `"n_errors"`, disimpan sebagai `invalid_eval_*.json` (tidak cocok pola `eval_*`), tidak di-log ke MLflow, proses keluar kode 1 dan `--repeat` dihentikan.
- `summarize_repeats()` menolak run invalid / ber-`error` (`ValueError`).
- Test baru di `src/tests/test_evaluation_runner.py` (12 kasus) → `src/tests` 97 lulus.
- Verifikasi: `ANTHROPIC_API_KEY= LLM_PROVIDER=anthropic python src/evaluation_runner.py --no-mlflow` → exit 1, jumlah file `data/audit_results/` tidak berubah.

---

## 7. Peta file Phase 16

```
src/retrieval/hierarchical_chunker.py   BARU  — chunker Bab→Bagian→Paragraf→Pasal→Ayat→Huruf
src/classifier/data_split.py            BARU  — split 80/10/10 bersama
src/tests/                              BARU  — 78 unit test (chunker, resolver, retrieval, coordinator, evaluasi)
src/pdf_extractor.py                    BARU  — ekstraksi PDF PyMuPDF (default ingest)
backend/tests/test_gate_and_output.py   BARU  — gate δ(q), NOT_REGULATION_CLAUSE, evidence trail, risk
data/golden_dataset.yaml                GANTI — sumber tunggal 12 klausul golden
src/ingest.py                           chunker hierarkis default, cosine, fix metadata cache, CHROMADB_PERSIST_DIR
src/retrieval/hybrid_retriever.py       retrieve_weighted() — Pers. 3.2 + relevance_score
src/agents/base_agent.py                retrieval bersama, α (Pers. 3.1), RETRIEVAL_STRATEGY, evidence, verifikasi sitasi, 6 status
src/agents/{bi,ojk}_specialist.py       top_k dari context, evidence, prompt 6 kelas
src/agents/conflict_resolver.py         Φ & π formal (Pers. 2.26), resolve_single
src/agents/coordinator.py               asyncio.to_thread (paralel), pilihan regulator
src/evaluation_runner.py                fix K1, qrels MRR/Hit@K, 6 kelas, Wilson CI, grounding, strict retrieval check
backend/app/services/rag_service.py     gate δ(q), NOT_REGULATION_CLAUSE, UNCLEAR, evidence trail, risk satu sumber
backend/app/api/v1/{audit,evaluation}.py field output baru, golden dari YAML
backend/app/models/audit.py             evidence_trail, gate_decision, analysis_mode, retrieval_mode
backend/app/config.py, docker/.env.example  default gate indobert / 0.5, RETRIEVAL_STRATEGY
```

---

## 8. Keterkaitan dengan TODO Phase 15 di `PROGRESS.md`

| TODO Phase 15 | Status setelah Phase 16 |
|---|---|
| TODO-B2 Evaluasi retrieval valid (MRR/Hit@K) | Akar masalah ternyata **bug K1**, bukan string matching. Qrels tingkat pasal dari `violated_articles` golden sudah dipakai. Anotasi `chunk_id` terpisah tidak lagi diperlukan untuk golden 12 klausul; tetap diperlukan untuk dataset v2. |
| TODO-A2 Validasi eksternal / kalibrasi confidence | Kalibrasi → S-01 & R8. Anotasi pakar + Cohen's Kappa tetap ⏳. |
| TODO-B1 Perluasan dataset (≥ 100 klausul) | Tetap ⏳. Mengatasi juga S-09 (n kecil & kebocoran gate) bila T&C DANA/OVO/ShopeePay dipakai sebagai data **baru** yang tidak ikut melatih gate. |
| TODO-B3 Deteksi PARTIALLY_COMPLIANT | Terdampak M1 (validasi pra-Φ kini menghormati `missing_elements`) → ukur ulang di R6. |
| TODO-C2 Tambah unit test | +77 test `src/tests` + 7 test backend. Test lama yang rusak → D1. |
| TODO-C3 Retrain IndoBERT | Split kini 80/10/10 → R4. |

---

## 9. Log sesi

| Tanggal | Sesi / agent | Ringkasan |
|---|---|---|
| 2026-09-25 | Claude Code (Phase 16) | Analisis gap proposal final ↔ repo. Implementasi 19 perbaikan [KODE] (§2). Menyusun 27 revisi [SEMHAS] (§3) dan runbook [DATA] (§5). Menemukan kesalahan faktual proposal S-23..S-25 dan bug K1 penyebab Hit Rate = 0. |
| 2026-09-25 | Claude Code (Phase 16, lanjutan) | Sandbox cloud tidak punya API key dan memblokir api.openai.com, huggingface.co, api.cloud.llamaindex.ai; `data/processed/chroma_db` dan `data/llama_cache` tidak ada di repo. Hanya evaluasi gate rule-based yang bisa dijalankan (lihat R5). R3–R8 tetap harus di laptop/server. |
| 2026-09-27 | Claude Code | Server cloud lama mati. Aset yang hilang dicatat di §0.1; runbook §5 diarahkan ke laptop/server baru; keputusan X1 (LlamaParse vs PyMuPDF) dibuka. |
| 2026-09-27 | Claude Code | Keputusan X1 = PyMuPDF, diimplementasikan (E1) untuk ingest dan upload. Uji ingest end-to-end di sandbox (848 chunk). Menemukan dan memperbaiki bug B4 (tabrakan kunci RRF). Hasil awal BM25-only dicatat di §3.4. |
| 2026-09-27 | Claude Code | Run lokal pertama: ingest gagal (B5, path `/app` dari `.env`), train IndoBERT gagal (B6, Keras 3). Keduanya diperbaiki. Evaluasi GPT-5.4-mini berjalan pada index lama (hasil dicatat di §3.4 sebagai non-final). |
| 2026-09-27 | Claude Code | Run lokal kedua (index baru): retrieval valid (MRR 0,575, Hit@5 0,80) tapi Recall NC 0,333. Akar masalah: konflik aturan prompt → P1. Tambah `--repeat` + diagnostik (V1). Catat S-28 (tuning prompt pada golden set) dan D5 (pyarrow). |
| 2026-09-27 | Claude Code | Analisis R6 ×3 (§3.4–3.5): Acc 0,917 ± 0,083, Recall NC 0,833 ± 0,167, MRR 0,575, Hit@5 0,80. Kesalahan tersisa = inkonsistensi status LLM (X2 dibuka). Temuan: grounding ≠ sitasi tepat; confidence tidak informatif. Bug chunker B7 diperbaiki (perlu re-ingest). IndoBERT belum dilatih ulang. |
| 2026-09-27 | Claude Code | Branch `semhas` di repo proposal: revisi §3 diterapkan ke Bab 1–3, Bab 4 (hasil R6) dan Bab 5 disusun, jadwal & file basi dihapus, kompilasi XeLaTeX lokal OK (94 hlm, tanpa referensi tak terdefinisi). Detail §3.6. |
| 2026-09-27 | Claude Code | Merge hasil pasca-B7 + Haiku + IndoBERT dari laptop. Bab 4/5 di branch `semhas` diperbarui (MRR 0,583; cit. acc 0,833; IndoBERT 0,938). Run Haiku tidak valid (auth) → D6. |
| 2026-09-27 | Claude Code | Serah terima ke Claude Code lokal: `LOCAL_TODO.md` (T1–T9: D6, Haiku ×3, ablation retrieval, R8, GoPay, GPT FT, D1, isi `\menunggu`, kompilasi), `CLAUDE.md`, slash command `/semhas-todo`, dan `scripts/semhas_metrics.py` (metrik turunan Bab 4 + penolakan run ber-error). |
| 2026-09-27 | Claude Code (lokal) | T1/D6 selesai: `evaluation_runner` cek key di awal, berhenti pada error API fatal, tandai run `invalid` (`invalid_eval_*.json`, tanpa MLflow, exit 1); `summarize_repeats` menolak run invalid. `src/tests` 97 lulus. T2 (Haiku) ditunda: saldo Anthropic habis. |
| 2026-09-27 | Claude Code (lokal) | T3/R6b selesai (dense ×3, rrf_equal ×3; semua valid). Run pertama di venv gagal `Unknown model 'gpt-5.4-mini'` (llama-index-llms-openai 0.6.26) → ditangkap D6 sebagai run invalid; diulang dengan conda base (0.7.10, env yang sama dengan run GPT pasca-B7). 'unknown model' ditambahkan ke error fatal. Label `retrieval_setup` untuk strategi dense diperbaiki. T4 sebagian: `scripts/reliability_diagram.py` + diagram GPT. |
