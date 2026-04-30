"""
train_indobert.py — Fine-tune IndoBERT untuk SOP Gate Classifier.

Model: indobenchmark/indobert-base-p1
Task : Binary sequence classification (SOP=1, bukan SOP=0)
Input: data/classifier/dataset.csv
Output: data/classifier/indobert_gate/ (model + tokenizer)

Usage:
    python src/classifier/train_indobert.py [--epochs 3] [--batch 16]

Requirements:
    pip install transformers torch scikit-learn pandas
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, f1_score

DATA_PATH  = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "dataset.csv"
MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "indobert_gate"
METRICS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "indobert_metrics.json"

BASE_MODEL = "indobenchmark/indobert-base-p1"


def load_data():
    df = pd.read_csv(DATA_PATH)
    assert "text" in df.columns and "label" in df.columns, "Dataset harus punya kolom 'text' dan 'label'"
    return df["text"].tolist(), df["label"].tolist()


def train(epochs: int = 3, batch_size: int = 16, lr: float = 2e-5, seed: int = 42):
    try:
        from transformers import (
            AutoTokenizer,
            AutoModelForSequenceClassification,
            TrainingArguments,
            Trainer,
        )
        import torch
        from torch.utils.data import Dataset as TorchDataset
    except ImportError:
        print("ERROR: transformers dan torch belum terinstall.")
        print("Jalankan: pip install transformers torch")
        sys.exit(1)

    print(f"Loading dataset dari {DATA_PATH}...")
    texts, labels = load_data()
    print(f"Total: {len(texts)} contoh | Positif: {sum(labels)} | Negatif: {len(labels)-sum(labels)}")

    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.15, stratify=labels, random_state=seed
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.12, stratify=y_train, random_state=seed
    )
    print(f"Split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}")

    print(f"Loading tokenizer: {BASE_MODEL}...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)

    class SOPDataset(TorchDataset):
        def __init__(self, texts, labels, tokenizer, max_len=128):
            self.texts = texts
            self.labels = labels
            self.tokenizer = tokenizer
            self.max_len = max_len

        def __len__(self):
            return len(self.labels)

        def __getitem__(self, idx):
            enc = self.tokenizer(
                str(self.texts[idx]),
                truncation=True,
                padding="max_length",
                max_length=self.max_len,
                return_tensors="pt",
            )
            item = {k: v.squeeze(0) for k, v in enc.items()}
            item["labels"] = torch.tensor(self.labels[idx], dtype=torch.long)
            return item

    train_dataset = SOPDataset(X_train, y_train, tokenizer)
    val_dataset   = SOPDataset(X_val,   y_val,   tokenizer)
    test_dataset  = SOPDataset(X_test,  y_test,  tokenizer)

    print(f"Loading model: {BASE_MODEL}...")
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE_MODEL,
        num_labels=2,
        id2label={0: "BUKAN_SOP", 1: "SOP"},
        label2id={"BUKAN_SOP": 0, "SOP": 1},
    )

    MODEL_PATH.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(MODEL_PATH),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=lr,
        weight_decay=0.01,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        seed=seed,
        logging_steps=10,
        report_to="none",
    )

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = logits.argmax(axis=-1)
        return {
            "accuracy": accuracy_score(labels, preds),
            "f1": f1_score(labels, preds, average="weighted"),
        }

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        compute_metrics=compute_metrics,
    )

    print(f"\nTraining IndoBERT ({epochs} epochs, batch={batch_size}, lr={lr})...")
    trainer.train()

    # Evaluate on test set
    print("\nEvaluating on test set...")
    predictions = trainer.predict(test_dataset)
    preds = predictions.predictions.argmax(axis=-1)
    report = classification_report(y_test, preds, target_names=["BUKAN_SOP", "SOP"], output_dict=True)

    print("\n" + classification_report(y_test, preds, target_names=["BUKAN_SOP", "SOP"]))
    print(f"Accuracy: {accuracy_score(y_test, preds):.4f}")

    # Save model + tokenizer
    trainer.save_model(str(MODEL_PATH))
    tokenizer.save_pretrained(str(MODEL_PATH))

    # Save metrics
    metrics = {
        "model": BASE_MODEL,
        "epochs": epochs,
        "batch_size": batch_size,
        "learning_rate": lr,
        "train_size": len(X_train),
        "val_size": len(X_val),
        "test_size": len(X_test),
        "accuracy": accuracy_score(y_test, preds),
        "f1_weighted": f1_score(y_test, preds, average="weighted"),
        "f1_sop": report["SOP"]["f1-score"],
        "precision_bukan_sop": report["BUKAN_SOP"]["precision"],
        "recall_bukan_sop": report["BUKAN_SOP"]["recall"],
        "classification_report": report,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\nModel tersimpan: {MODEL_PATH}")
    print(f"Metrics tersimpan: {METRICS_PATH}")
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fine-tune IndoBERT untuk SOP Gate Classifier")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    train(epochs=args.epochs, batch_size=args.batch, lr=args.lr, seed=args.seed)
