# LOCAL_TODO — Pekerjaan untuk Claude Code **lokal** (laptop mahasiswa)

> Dibuat 2026-09-27 oleh sesi Claude Code cloud. Dieksekusi oleh Claude Code yang berjalan
> di laptop, karena hanya di sana tersedia API key, index ChromaDB/BM25 pasca-B7, dan model IndoBERT.
> Sumber kebenaran status tetap [`SEMHAS_TRACKER.md`](./SEMHAS_TRACKER.md); file ini adalah
> daftar kerja operasionalnya. Centang `[x]` dan isi kolom **Hasil** setiap selesai satu tugas.

## 0. Aturan untuk agent

1. **Branch kode:** `claude/funny-lovelace-lfga0w` (repo ini). **Branch laporan:** `semhas` di repo
   `rzkynovan/template-proposal-ta-its`. Jangan push ke `main` di kedua repo.
2. **API key hanya dari environment** (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Jangan menulis key ke
   file yang di-commit dan jangan mencetaknya ke output. Jika key tidak ada di env → **berhenti dan
   tanya user**, jangan menjalankan evaluasi (itulah penyebab run Haiku 16:43 tidak valid).
3. **Jangan mengubah prompt agen, golden dataset, atau parameter retrieval** untuk "memperbaiki angka".
   Semua penyetelan pada golden set menambah beban keterbatasan S-28. Keputusan X2 = **C (biarkan)**
   kecuali user memutuskan lain.
4. Setiap hasil evaluasi **wajib divalidasi** dengan `python scripts/semhas_metrics.py <file...>`
   sebelum di-commit. Skrip keluar dengan error jika ada panggilan API yang gagal.
5. Proposal final (`main` repo proposal) **tidak boleh diubah**. Angka baru hanya masuk ke branch `semhas`.
6. Setelah tiap tugas: perbarui `SEMHAS_TRACKER.md` (§3.4 tabel hasil, §5 status runbook, §9 log),
   commit dengan pesan jelas, lalu `git push -u origin claude/funny-lovelace-lfga0w`.
7. Tugas yang butuh aksi manusia (unduh PDF GoPay, login UI) → minta user melakukannya, jangan menebak.

## 1. Persiapan (sekali per sesi)

```bash
cd <root repo nlp-compliance-rag>
git fetch origin && git checkout claude/funny-lovelace-lfga0w && git pull
source venv/bin/activate          # atau env yang dipakai sebelumnya (lihat D5 bila pyarrow error)
export USE_TF=0
test -n "$OPENAI_API_KEY"    && echo "OPENAI ok"    || echo "OPENAI_API_KEY KOSONG"
test -n "$ANTHROPIC_API_KEY" && echo "ANTHROPIC ok" || echo "ANTHROPIC_API_KEY KOSONG"
python -m pytest src/tests -q     # harus lulus semua (85)
```

Pastikan index pasca-B7 ada: `data/processed/chroma_db` dan `data/processed/bm25_index` (BI 556 / OJK 292 chunk).
Jika tidak ada → jalankan R3: `python src/ingest.py --force`.

## 2. Daftar tugas (urut prioritas)

| # | ID | Tugas | Wajib? | Status |
|---|---|---|---|---|
| T1 | D6 | `evaluation_runner.py` gagal cepat saat error API | Wajib, **kerjakan pertama** | [ ] |
| T2 | R6 | Claude Haiku 4.5 ×3 | Wajib | [ ] |
| T3 | R6b | Ablation retrieval `dense` ×3 dan `rrf_equal` ×3 | Wajib | [ ] |
| T4 | R8 | Reliability diagram + ECE (GPT & Haiku) | Wajib | [ ] |
| T5 | R7 | Audit ulang T&C GoPay (121 klausul) | Wajib, butuh user | [ ] |
| T6 | R5 | GPT fine-tuned gate: latih ulang + evaluasi 3 gate | Opsional (berbiaya) | [ ] |
| T7 | D1 | Perbaiki test backend lama (3 gagal + 15 error) | Opsional | [ ] |
| T8 | — | Isi semua `\menunggu{...}` di Bab 4/5 (branch `semhas`) | Wajib, setelah T2–T5 | [ ] |
| T9 | — | Kompilasi PDF laporan | Wajib, terakhir | [ ] |

---

### T1 — D6: evaluation_runner gagal cepat saat error API

**Masalah:** jika semua panggilan LLM gagal (mis. key kosong), `src/evaluation_runner.py` tetap menulis
JSON dengan prediksi `UNCLEAR` dan metrik 0, sehingga terlihat seperti hasil model.

**Langkah:**
1. Di awal run: jika `LLM_PROVIDER=anthropic` dan `ANTHROPIC_API_KEY` kosong, atau `OPENAI_API_KEY`
   kosong (embedding selalu OpenAI) → `sys.exit` dengan pesan jelas sebelum memanggil API apa pun.
2. Setelah run: jika ada hasil dengan field `error`, tandai output `"invalid": true` + `"n_errors"`,
   jangan log ke MLflow, dan keluar dengan kode ≠ 0. `summarize_repeats` harus menolak run invalid.
3. Tambah test di `src/tests/test_evaluation_runner.py` (kasus key kosong dan kasus hasil ber-`error`).

**Selesai bila:** `python -m pytest src/tests -q` lulus, dan
`ANTHROPIC_API_KEY= LLM_PROVIDER=anthropic python src/evaluation_runner.py --no-mlflow` langsung berhenti
dengan pesan error tanpa menulis file hasil.

---

### T2 — R6: Claude Haiku 4.5 ×3

```bash
LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 RETRIEVAL_STRATEGY=query_aware \
  python src/evaluation_runner.py --repeat 3 --no-mlflow
python scripts/semhas_metrics.py data/audit_results/eval_anthropic_claude-haiku-4-5-20251001_query_aware_<ts_baru>*.json
```

**Selesai bila:** skrip metrik tidak menolak run, latensi rata-rata wajar (puluhan detik, bukan <1 dtk),
dan ada file `repeat_anthropic_..._x3.json`.
**Catat di tracker §3.4:** accuracy/macro-F1/recall NC ketat & longgar (mean ± SD), F1 NC/PC/NA,
MRR/Hit@K (harus sama dengan GPT, karena retrieval identik), grounding, citation accuracy, ECE,
latensi, klausul tidak stabil.
**Hapus file run Haiku lama yang tidak valid** (`*_20260927_164357/164403/164410.json` dan
`repeat_*_164357_x3.json`) dengan `git rm`, dan sebutkan di pesan commit.

---

### T3 — R6b: Ablation retrieval

```bash
RETRIEVAL_STRATEGY=dense     python src/evaluation_runner.py --repeat 3 --no-mlflow
RETRIEVAL_STRATEGY=rrf_equal python src/evaluation_runner.py --repeat 3 --no-mlflow
python scripts/semhas_metrics.py data/audit_results/eval_openai_gpt-5.4-mini_dense_<ts>*.json
python scripts/semhas_metrics.py data/audit_results/eval_openai_gpt-5.4-mini_rrf_equal_<ts>*.json
```

**Selesai bila:** keduanya valid. Catat MRR, Hit@3, Hit@5, dan rank per klausul
(`retrieval.per_clause`) untuk dibandingkan dengan `query_aware` (MRR 0,583; Hit@3 0,60; Hit@5 0,80).
Catat juga metrik klasifikasi, karena perubahan konteks dapat mengubah verdik.

---

### T4 — R8: Reliability diagram + ECE

1. Buat `scripts/reliability_diagram.py`: input file hasil (beberapa run), output PNG diagram reliabilitas
   (10 bin; sumbu x confidence, y akurasi; garis diagonal; histogram jumlah per bin) untuk tiap model.
2. Simpan ke `data/audit_results/figures/reliability_<model>.png`, lalu salin ke repo proposal
   `gambar/` pada branch `semhas`.
3. ECE diambil dari `scripts/semhas_metrics.py` supaya konsisten.
   Nilai GPT pasca-B7 saat ini: ECE 0,0575; semua 36 prediksi di bin 0,9–1,0;
   conf benar 0,975 vs salah 0,970.

---

### T5 — R7: Audit ulang T&C GoPay *(butuh user)*

1. **Minta user** mengunduh PDF T&C GoPay terbaru ke `data/raw/gopay/` dan menyebutkan tanggal akses.
   Jangan commit PDF jika lisensinya tidak jelas; cukup catat URL + tanggal.
2. Jalankan tanpa UI (lebih reprodusibel) bila memungkinkan:
   ekstrak dengan `src/pdf_extractor.py` (PyMuPDF), pecah klausul dengan fungsi `_split_into_clauses`
   di `backend/app/api/v1/audit.py`, lalu audit tiap klausul lewat `RAGAuditService.analyze_with_rag`
   (agar gate IndoBERT + pre-filter ikut aktif). Simpan ke
   `data/audit_results/gopay_<yyyymmdd>.json` berisi per klausul: teks, `final_status`,
   `analysis_mode`, `gate_decision`, violations, latency.
   Alternatif: UI (`docker-compose up -d --build`, tab Upload Dokumen, cache dimatikan).
3. Ringkas: jumlah klausul hasil segmentasi, jumlah ditolak gate/pre-filter (`analysis_mode`),
   distribusi 6 kelas, latensi rata-rata, 3–5 contoh temuan NC dengan pasalnya.

**Catatan:** hasil lama (4 C / 8 PC / 10 NC / 99 NA) tidak valid dan tidak boleh dipakai.

---

### T6 — R5: GPT fine-tuned gate *(opsional, berbiaya; tanya user dulu)*

```bash
python src/classifier/train_gpt_finetune.py          # split 80/10/10 yang sama, seed 42
# tunggu job selesai, ambil model id dari output / dashboard OpenAI
export GPT_FINETUNED_MODEL_ID=ft:gpt-4.1-mini-2025-04-14:...
python src/classifier/evaluate_gates.py              # bandingkan rule-based, IndoBERT, GPT FT pada 16 data uji
```

Catat accuracy, F1-w, precision bukan-klausul, recall klausul, dan latensi inferensi ketiga gate.
Model FT lama (`...:DaNe3Ai9`) dilatih dengan split lama; jangan dilaporkan pada split baru.

---

### T7 — D1: Test backend lama *(opsional)*

Detail di tracker §6 D1. Ringkasnya:
- `backend/tests/test_audit_api.py` masih memakai `audit_mod.audit_history` (sudah diganti PostgreSQL)
  → ganti dengan mock sesi DB / fixture SQLite.
- `TestMapStatus::test_case_sensitive` bertentangan dengan normalisasi case di `_map_status` → sesuaikan
  test dengan perilaku yang benar (normalisasi memang disengaja).
- `TestAnalyzeWithRag` (budget, cache): input `"test clause"` dihentikan gate/pre-check sebelum
  mencapai cache/budget → pakai klausul SOP yang valid atau mock gate.

**Selesai bila:** `cd backend && python -m pytest tests -q` lulus semua. Perbarui jumlah test di
`AGENTS.md` dan tracker.

---

### T8 — Isi `\menunggu` di laporan (repo proposal, branch `semhas`)

```bash
cd <root repo template-proposal-ta-its> && git checkout semhas && git pull
grep -n 'menunggu' konten/*.tex
```

Lokasi saat ini: Tabel 4.2 (GPT FT), paragraf gate (R5), Tabel 4.3 (dense, rrf_equal), subbab 4.4.2
(Haiku), subbab 4.5 (R8), subbab 4.6 (GoPay), dan Bab 5 butir 1 dan 3.

Aturan penulisan:
- Angka **hanya** dari output `scripts/semhas_metrics.py` / JSON; format desimal Indonesia (`0,917`).
- Untuk Haiku: tambahkan kolom/tabel pembanding di samping Tabel 4.5 (mean ± SD), bahas trade-off
  recall vs latensi (manfaat penelitian butir 3).
- Untuk ablation: bahas apakah `query_aware` lebih baik dari `rrf_equal`. Ingat semua klausul golden
  mendapat α = 0,3, sehingga perbedaan dengan `rrf_equal` murni efek bobot 0,3 vs 0,5.
- Jika hasil bertentangan dengan narasi yang ada (mis. Haiku lebih baik), **ubah narasinya**, jangan angkanya.
- Hapus setiap `\menunggu{...}` yang sudah terisi; biarkan yang memang tidak dikerjakan (mis. T6)
  lalu ubah menjadi kalimat keterbatasan.
- Commit ke `semhas`, push `git push origin semhas`.

---

### T9 — Kompilasi PDF

```bash
cd <root repo template-proposal-ta-its>
latexmk -xelatex -interaction=nonstopmode main.tex
grep -nE 'undefined|^!' main.log      # harus kosong
latexmk -c
```

Periksa manual: tidak ada teks merah `[MENUNGGU: ...]` kecuali yang disengaja, dan semua tabel/gambar Bab 4 bernomor.

## 3. Di luar cakupan agent (dikerjakan user)

- Regenerasi gambar `gambar/arsitektur-multi-agent-rag.png` di repo proposal (hapus Elasticsearch
  dan W&B; BM25 = `rank_bm25`). Prompt sumber: `arsitektur-prompt.txt`.
- Keputusan X2 (A/B/C) bila ingin mengubah dari default C.

## 4. Hasil

| # | Tanggal | Ringkasan hasil | File / commit |
|---|---|---|---|
| T1 | | | |
| T2 | | | |
| T3 | | | |
| T4 | | | |
| T5 | | | |
| T6 | | | |
| T7 | | | |
| T8 | | | |
| T9 | | | |
