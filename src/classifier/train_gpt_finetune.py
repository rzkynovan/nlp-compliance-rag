"""
train_gpt_finetune.py — Fine-tune GPT-5.4-mini untuk SOP Gate Classifier.

Upload training data ke OpenAI Fine-tuning API, poll status, dan simpan
model ID ke data/classifier/gpt_finetuned_model_id.txt.

Format training: JSONL dengan chat format (system + user + assistant).
Label: "SOP" atau "BUKAN_SOP"

Usage:
    python src/classifier/train_gpt_finetune.py [--model gpt-5.4-mini-2026-03-17]

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
from sklearn.model_selection import train_test_split

DATA_PATH    = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "dataset.csv"
JSONL_TRAIN  = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_train.jsonl"
JSONL_VAL    = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_val.jsonl"
MODEL_ID_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_finetuned_model_id.txt"
METRICS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gpt_finetune_metrics.json"

SYSTEM_PROMPT = (
    "Kamu adalah classifier yang menentukan apakah sebuah teks adalah klausa SOP "
    "(Standar Operasional Prosedur) atau dokumen T&C (Terms & Conditions) layanan keuangan "
    "digital yang valid, atau bukan.\n\n"
    "Jawab hanya dengan satu kata: 'SOP' jika teks adalah klausa SOP/T&C yang valid, "
    "atau 'BUKAN_SOP' jika teks bukan klausa SOP (misalnya: sapaan, pertanyaan umum, "
    "lirik lagu, kalimat acak, atau teks tidak bermakna)."
)


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


def train(model: str = "gpt-5.4-mini-2026-03-17", seed: int = 42):
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
    X_train, X_val, y_train, y_val = train_test_split(
        texts, labels, test_size=0.15, stratify=labels, random_state=seed
    )
    print(f"Training: {len(X_train)}, Validation: {len(X_val)}")

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

    # Poll status
    print("\nPolling job status (ctrl+C untuk berhenti, job tetap berjalan di OpenAI)...")
    while True:
        job = client.fine_tuning.jobs.retrieve(job.id)
        print(f"  Status: {job.status} | {time.strftime('%H:%M:%S')}")

        if job.status in ("succeeded", "failed", "cancelled"):
            break
        time.sleep(30)

    if job.status != "succeeded":
        print(f"Fine-tuning GAGAL: {job.status}")
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
        "base_model": model,
        "fine_tuned_model": fine_tuned_model,
        "status": job.status,
        "train_file_id": train_file.id,
        "val_file_id": val_file.id,
        "train_size": len(X_train),
        "val_size": len(X_val),
        "result_files": [f.id for f in (job.result_files or [])],
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
    args = parser.parse_args()

    train(model=args.model, seed=args.seed)
