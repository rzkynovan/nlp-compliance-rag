# CLAUDE.md

Instruksi proyek untuk Claude Code. Baca berurutan:

1. @AGENTS.md: arsitektur, struktur folder, cara menjalankan sistem.
2. @SEMHAS_TRACKER.md: **sumber kebenaran** status gap proposal ↔ kode, hasil evaluasi valid/tidak valid, runbook.
3. @LOCAL_TODO.md: **daftar kerja aktif** untuk Claude Code yang berjalan di laptop (API key + index lokal).

Aturan singkat:
- Proposal TA sudah final. Jangan ubah perilaku kode menjauh dari proposal tanpa mencatatnya di tracker.
- Jangan menyetel prompt, golden dataset, atau parameter retrieval demi angka evaluasi (S-28).
- Validasi setiap hasil evaluasi dengan `python scripts/semhas_metrics.py <file...>` sebelum commit.
- API key hanya dari environment; jangan pernah di-commit atau dicetak.
- Branch kerja: `claude/funny-lovelace-lfga0w` (kode) dan `semhas` di repo `template-proposal-ta-its` (laporan).
