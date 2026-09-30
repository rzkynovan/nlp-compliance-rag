"""
train_gpt_finetune.py — Fine-tune GPT-4.1-mini untuk SOP Gate Classifier (Tabel 3.10 proposal).

Upload training data ke OpenAI Fine-tuning API, poll status, dan simpan
model ID ke data/classifier/gpt_finetuned_model_id.txt.

Format training: JSONL dengan chat format (system + user + assistant).
Label: "SOP" atau "BUKAN_SOP"

Usage:
    python src/classifier/train_gpt_finetune.py [--model gpt-4.1-mini-2025-04-14]

Requirements:
    pip install openai pandas scikit-learn
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from classifier.data_split import split_80_10_10  # noqa: E402
from classifier.sop_gate import GPT_GATE_SYSTEM_PROMPT  # noqa: E402

DATA_PATH    = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "dataset.csv"
JSONL_TRAIN  = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_train.jsonl"
JSONL_VAL    = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_val.jsonl"
MODEL_ID_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_finetuned_model_id.txt"
METRICS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_finetune_metrics.json"

# Sumber tunggal prompt: dipakai juga saat inferensi di GPTFineTunedGate
SYSTEM_PROMPT = GPT_GATE_SYSTEM_PROMPT


def build_jsonl(texts, labels, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for text, label in zip(texts, labels):
            answer = "SOP" if label == 1 else "BUKAN_SOP"
            record = {
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Klasifikasikan teks berikut:\n\n{text}"},
                    {"role": "assistant", "content": answer},
                ]
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"JSONL tersimpan: {path} ({sum(1 for _ in open(path))} records)")


def train(model: str = "gpt-4.1-mini-2025-04-14", seed: int = 42):
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai belum terinstall. Jalankan: pip install openai")
        sys.exit(1)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY tidak ditemukan di environment.")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Load & split dataset
    df = pd.read_csv(DATA_PATH)
    texts, labels = df["text"].tolist(), df["label"].tolist()
    # Split 80/10/10 (Subbab 3.1.2) — partisi uji TIDAK dikirim ke OpenAI;
    # validation file hanya berisi partisi validasi.
    X_train, X_val, _X_test, y_train, y_val, _y_test = split_80_10_10(texts, labels, seed=seed)
    print(f"Training: {len(X_train)}, Validation: {len(X_val)} (test {len(_X_test)} disimpan untuk evaluate_gates.py)")

    # Build JSONL
    build_jsonl(X_train, y_train, JSONL_TRAIN)
    build_jsonl(X_val, y_val, JSONL_VAL)

    # Upload files
    print("Uploading training file ke OpenAI...")
    with open(JSONL_TRAIN, "rb") as f:
        train_file = client.files.create(file=f, purpose="fine-tune")
    print(f"Training file ID: {train_file.id}")

    print("Uploading validation file ke OpenAI...")
    with open(JSONL_VAL, "rb") as f:
        val_file = client.files.create(file=f, purpose="fine-tune")
    print(f"Validation file ID: {val_file.id}")

    # Create fine-tuning job
    print(f"Membuat fine-tuning job dengan model: {model}...")
    job = client.fine_tuning.jobs.create(
        training_file=train_file.id,
        validation_file=val_file.id,
        model=model,
        hyperparameters={"n_epochs": 3},
        suffix="sop-gate",
    )
    print(f"Job ID: {job.id} | Status: {job.status}")

    return wait_and_save(client, job.id, model, train_file.id, val_file.id, len(X_train), len(X_val))


def wait_and_save(client, job_id: str, model: str, train_file_id: str = None, val_file_id: str = None,
                  train_size: int = None, val_size: int = None, poll_seconds: int = 30):
    """Poll job sampai selesai. Koneksi putus (mis. laptop sleep) tidak menghentikan polling."""
    from openai import APIConnectionError, APITimeoutError

    print("\nPolling job status (ctrl+C untuk berhenti, job tetap berjalan di OpenAI;"
          f" lanjutkan dengan --resume-job {job_id})...")
    last_status = None
    while True:
        try:
            job = client.fine_tuning.jobs.retrieve(job_id)
        except (APIConnectionError, APITimeoutError) as e:
            print(f"  Koneksi gagal ({type(e).__name__}) — coba lagi | {time.strftime('%H:%M:%S')}")
            time.sleep(poll_seconds)
            continue
        if job.status != last_status:
            print(f"  Status: {job.status} | {time.strftime('%H:%M:%S')}")
            last_status = job.status
        if job.status in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(poll_seconds)

    if job.status != "succeeded":
        print(f"Fine-tuning GAGAL: {job.status} {job.error}")
        sys.exit(1)

    fine_tuned_model = job.fine_tuned_model
    print(f"\nFine-tuning selesai! Model ID: {fine_tuned_model}")

    # Simpan model ID
    MODEL_ID_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_ID_PATH, "w") as f:
        f.write(fine_tuned_model)

    # Simpan metrics dari OpenAI
    metrics = {
        "job_id": job.id,
        "base_model": job.model or model,
        "fine_tuned_model": fine_tuned_model,
        "status": job.status,
        "train_file_id": train_file_id or job.training_file,
        "val_file_id": val_file_id or job.validation_file,
        "train_size": train_size,
        "val_size": val_size,
        "trained_tokens": job.trained_tokens,
        "n_epochs": getattr(job.hyperparameters, "n_epochs", None),
        "seed": job.seed,
        "result_files": list(job.result_files or []),
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"Model ID tersimpan: {MODEL_ID_PATH}")
    print(f"Set env var: GPT_FINETUNED_MODEL_ID={fine_tuned_model}")
    return fine_tuned_model


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune GPT untuk SOP Gate Classifier")
    parser.add_argument("--model", default="gpt-4.1-mini-2025-04-14")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resume-job", default=None,
                        help="Lanjutkan polling job yang sudah dibuat (ftjob-...), tanpa upload/job baru")
    args = parser.parse_args()

    if args.resume_job:
        from openai import OpenAI
        df = pd.read_csv(DATA_PATH)
        split = split_80_10_10(df["text"].tolist(), df["label"].tolist(), seed=args.seed)
        wait_and_save(OpenAI(), args.resume_job, args.model,
                      train_size=len(split[0]), val_size=len(split[1]))
    else:
        train(model=args.model, seed=args.seed)
