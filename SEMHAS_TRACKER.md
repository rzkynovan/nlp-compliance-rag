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

## 1. Ringkasan cepat

| Kategori | Jumlah | Status |
|---|---|---|
| Gap diperbaiki di kode (Phase 16) | 19 | ✅ / 🟡 (perlu run ulang) |
| Pekerjaan [DATA] di server | 10 langkah (R1–R8, R6b, R6c) | ⏳ lihat [§5 Runbook](#5-runbook--urutan-menjalankan-ulang-di-server) |
| Revisi teks untuk laporan Semhas | 27 | 📝 lihat [§3](#3-daftar-revisi-untuk-laporan-semhas-semhas) |
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
| **B3** | Prompt fallback LLM-only menyebut regulasi yang salah ("POJK 22/POJK.05/2023 … Jasa Keuangan Digital") dan tidak menyebut PBI 22/23/2020. | Batasan Masalah no. 2 | Diganti tiga regulasi korpus dengan judul resmi. | `rag_service.py` | — | ✅ |

**Test:** `python -m pytest src/tests -q` → **77 lulus**. `cd backend && OPENAI_API_KEY=sk-test python -m pytest tests -q` → 163 lulus. 3 gagal + 15 error **sudah ada sebelum Phase 16** (lihat §6, D1).

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
| S-08 | Tabel 3.2, Subbab 3.4.3 | Estimasi ±962 / ±628 / ±1.031 chunk (N ≈ 2.621) | Chunker hierarkis menghasilkan ±205 / ±358 / ±292 chunk (≈ 855, termasuk Penjelasan). Angka final dari log ingest. | Ganti dengan jumlah aktual setelah re-ingest. | 📝 (setelah R3) |
| S-09 (M4) | Tabel 3.3, Subbab 3.1.2 | Positif gate mencakup GoPay T&C & klausul Dummy | Klausul yang **dievaluasi** (12 golden + GoPay) ikut dilatih di gate → gate "sudah melihat" data uji RAG. n uji gate hanya 16. | Nyatakan di Keterbatasan; laporkan **Wilson CI 95%** (1,000 pada n = 16 → batas bawah ≈ 0,81). Opsional: stratified 5-fold CV. | 📝 |
| S-10 | Tabel 3.4 | BAB III 4 NC (pengaduan), BAB IV 2 NC (saldo & transaksi) | Golden aktual: 3 NC pengaduan/klausula (BAB3-01..03) + 3 NC saldo/transaksi (BAB4-01..03). | Perbaiki tabel komposisi: 2 NA + 4 PC + 3 NC + 3 NC = 12. | 📝 |
| S-11 | Tabel 3.4 | Label "Netral" | Dipakai sebagai `NOT_ADDRESSED` | Ganti "Netral" → Not Addressed. | 📝 |

### 3.2 Teknologi (Tabel 3.11, Gambar 3.4–3.5, Subbab 3.5.4)

| ID | Tertulis di proposal | Realita / keputusan | Alasan dipertahankan | Status |
|---|---|---|---|---|
| S-12 | Ekstraksi PDF dengan **PyMuPDF** (Fase 1, Step 3) | **LlamaParse** (markdown, cache SHA-256) + fallback pypdf | Struktur heading/tabel lebih baik untuk chunking; cache menghindari biaya ulang. | 📝 |
| S-13 | **Elasticsearch** BM25 (Fase 3, Step 9) | `rank_bm25` BM25Okapi in-memory (pickle), k1 = 1,5, b = 0,75 | Korpus ±855 chunk; ES menambah service JVM tanpa manfaat. Tabel 3.11 proposal sendiri menyebut BM25Okapi. | 📝 |
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
| S-27 | Catatan dokumen internal (`AGENTS.md`, `PROGRESS.md`, draf skripsi) | "Hit Rate@5 = 0 karena limitasi metodologi string matching" | Penyebabnya **bug K1**. Hapus klaim ini dan ganti dengan hasil run ulang. | 📝 |

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

## 5. Runbook — urutan menjalankan ulang di server

> Jalankan dari host server (repo di `~/nlp-compliance-rag`). Perkiraan biaya embedding re-ingest
> ±855 chunk × ±300 token ≈ 0,26 jt token × $0,13/1 jt ≈ **< $0,05**. LlamaParse memakai cache (gratis).

| # | Langkah | Perintah | Status |
|---|---|---|---|
| R1 | Tarik branch, lalu perbarui `docker/.env` server | `SOP_GATE_MODEL=indobert`, `SOP_GATE_THRESHOLD=0.5`, `RETRIEVAL_STRATEGY=query_aware`. ⚠️ `.env` server kemungkinan masih `rule_based` / `0.8` dan **mengalahkan default kode**. | ⏳ |
| R2 | Build ulang backend | `cd docker && docker-compose build backend && docker-compose up -d backend` | ⏳ |
| R3 | **Re-ingest hierarkis + cosine** (backup dulu `data/processed/`) | `cp -r data/processed data/processed_backup_phase13` lalu `docker-compose exec -e LLAMA_CLOUD_API_KEY=$LLAMAPARSE_API_KEY backend python /app/src/ingest.py --force` (default `--chunker hierarchical`). Catat jumlah chunk per collection untuk S-08. | ⏳ |
| R4 | Latih ulang IndoBERT (split 80/10/10) | `docker-compose exec backend python /app/src/classifier/train_indobert.py` → `data/classifier/indobert_metrics.json` | ⏳ |
| R5 | (Opsional, berbiaya) GPT FT ulang + evaluasi 3 gate | `python /app/src/classifier/train_gpt_finetune.py` lalu `python /app/src/classifier/evaluate_gates.py --mlflow-uri http://mlflow:5000` | ⏳ |
| R6 | Evaluasi utama (ablation LLM) | `~/nlp-compliance-rag/scripts/run_ablation.sh` (GPT-5.4-mini vs Claude Haiku 4.5, `query_aware`). Output: `data/audit_results/eval_<provider>_<model>_query_aware_<ts>.json` + MLflow | ⏳ |
| R6b | Ablation retrieval (GPT-5.4-mini) | `docker-compose exec -e RETRIEVAL_STRATEGY=dense backend python /app/src/evaluation_runner.py` dan ulangi dengan `RETRIEVAL_STRATEGY=rrf_equal` | ⏳ |
| R6c | Ablation chunking (baseline Markdown) | `docker-compose exec -e CHROMADB_PERSIST_DIR=/app/data/processed_md/chroma_db -e LLAMA_CLOUD_API_KEY=$LLAMAPARSE_API_KEY backend python /app/src/ingest.py --force --chunker markdown`, lalu jalankan `evaluation_runner.py` dengan `CHROMADB_PERSIST_DIR` yang sama | ⏳ |
| R7 | Audit ulang GoPay T&C (121 klausul) | Upload via UI/`POST /audit/upload` lalu `/audit/batch`; catat `analysis_mode` untuk S-16 | ⏳ |
| R8 | Kalibrasi confidence (S-01) | Dari JSON R6: reliability diagram + ECE (confidence vs `correct_6`) | ⏳ |

Setelah R1–R8 selesai: perbarui §4, isi angka S-08, dan ganti tabel hasil di `AGENTS.md` / `PROGRESS.md`.

---

## 6. Utang teknis di luar cakupan gap

| ID | Temuan | Dampak | Status |
|---|---|---|---|
| D1 | `backend/tests/test_audit_api.py` memakai `audit_mod.audit_history` (sudah diganti PostgreSQL di Phase 10) → 15 error. `TestMapStatus::test_case_sensitive` bertentangan dengan normalisasi case di `_map_status`. `TestAnalyzeWithRag` (budget, cache) gagal karena input uji `"test clause"` sudah dihentikan gate/pre-check scope sebelum mencapai cache/budget. | 3 gagal + 15 error **sudah ada sebelum Phase 16**; klaim "165/165 test lulus" di dokumen tidak berlaku lagi | ⏳ |
| D2 | `ingest.py` mewajibkan `LLAMA_CLOUD_API_KEY` walau semua PDF sudah di-cache; compose hanya menyediakan `LLAMAPARSE_API_KEY` | Perlu `-e LLAMA_CLOUD_API_KEY=...` saat re-ingest (R3) | ⏳ |
| D3 | Paket `llama-parse` deprecated (peringatan saat import) | Migrasi ke SDK LlamaCloud baru suatu saat | ⏳ |
| D4 | `Field(..., env=...)` di `config.py` deprecated di Pydantic v2 | Hanya peringatan | ⏳ |

---

## 7. Peta file Phase 16

```
src/retrieval/hierarchical_chunker.py   BARU  — chunker Bab→Bagian→Paragraf→Pasal→Ayat→Huruf
src/classifier/data_split.py            BARU  — split 80/10/10 bersama
src/tests/                              BARU  — 77 unit test (chunker, resolver, retrieval, coordinator, evaluasi)
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
