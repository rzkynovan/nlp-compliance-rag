---
description: Kerjakan tugas berikutnya dari LOCAL_TODO.md (evaluasi Semhas di laptop)
argument-hint: "[ID tugas opsional, mis. T2]"
---

Baca `LOCAL_TODO.md` dan `SEMHAS_TRACKER.md`, lalu kerjakan tugas **$ARGUMENTS**. Jika argumen kosong,
kerjakan tugas pertama yang statusnya masih `[ ]` di tabel §2, sesuai urutan prioritas.

Langkah:
1. Jalankan pemeriksaan persiapan §1 (branch, env, API key, test `src/tests`). Jika API key yang
   dibutuhkan kosong atau test gagal, berhenti dan laporkan ke user.
2. Kerjakan tugas persis sesuai langkah dan kriteria "Selesai bila" di LOCAL_TODO.md, dengan patuh pada
   aturan §0. Untuk tugas yang butuh aksi manusia atau berbiaya (T5, T6), tanya user dulu.
3. Validasi hasil evaluasi dengan `scripts/semhas_metrics.py`.
4. Perbarui LOCAL_TODO.md (centang + tabel §4 Hasil) dan SEMHAS_TRACKER.md (§3.4, §5, §9), commit,
   lalu push ke `claude/funny-lovelace-lfga0w`.
5. Laporkan ke user: apa yang dijalankan, angka utama, file/commit, dan tugas berikutnya.
