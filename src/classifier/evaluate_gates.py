"""
evaluate_gates.py — Evaluasi 3 gate pada test set yang sama + log ke MLflow.

Membandingkan:
  A: RuleBasedGate   (baseline)
  B: IndoBERTGate    (fine-tuned, jika model tersedia)
  C: GPTFineTunedGate (fine-tuned, jika model ID tersedia)

Usage:
    python src/classifier/evaluate_gates.py [--mlflow-uri http://mlflow:5000]
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, classification_report,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from classifier.sop_gate import RuleBasedGate, IndoBERTGate, GPTFineTunedGate

DATA_PATH    = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "dataset.csv"
RESULTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "classifier" / "gate_evaluation_results.json"


def evaluate_gate(gate, X_test, y_test, gate_name: str) -> dict:
    print(f"\n[{gate_name}] Evaluating {len(X_test)} samples...")
    preds, confidences = [], []

    for text in X_test:
        result = gate.predict(text)
        preds.append(1 if result.is_sop else 0)
        confidences.append(result.confidence)

    report = classification_report(y_test, preds, target_names=["BUKAN_SOP", "SOP"], output_dict=True)
    print(classification_report(y_test, preds, target_names=["BUKAN_SOP", "SOP"]))

    return {
        "gate": gate_name,
        "model": gate.model_name,
        "accuracy":            round(accuracy_score(y_test, preds), 4),
        "f1_weighted":         round(f1_score(y_test, preds, average="weighted"), 4),
        "f1_sop":              round(report["SOP"]["f1-score"], 4),
        "precision_sop":       round(report["SOP"]["precision"], 4),
        "recall_sop":          round(report["SOP"]["recall"], 4),
        "precision_bukan_sop": round(report["BUKAN_SOP"]["precision"], 4),
        "recall_bukan_sop":    round(report["BUKAN_SOP"]["recall"], 4),
        "f1_bukan_sop":        round(report["BUKAN_SOP"]["f1-score"], 4),
        "avg_confidence":      round(sum(confidences) / len(confidences), 4),
        "n_test":              len(X_test),
        "classification_report": report,
    }


def run_evaluation(mlflow_uri: str = None):
    df = pd.read_csv(DATA_PATH)
    texts, labels = df["text"].tolist(), df["label"].tolist()

    # Use same seed as training scripts for consistent test set
    _, X_test, _, y_test = train_test_split(
        texts, labels, test_size=0.15, stratify=labels, random_state=42
    )

    print(f"Test set: {len(X_test)} samples | Positif: {sum(y_test)} | Negatif: {len(y_test)-sum(y_test)}")

    gates = [
        ("A_RuleBased",    RuleBasedGate()),
        ("B_IndoBERT",     IndoBERTGate()),
        ("C_GPTFineTuned", GPTFineTunedGate()),
    ]

    results = []
    for gate_name, gate in gates:
        if not gate.is_available():
            print(f"\n[{gate_name}] Tidak tersedia (model belum ditraining) — skip.")
            results.append({"gate": gate_name, "model": gate.model_name, "status": "not_available"})
            continue
        metrics = evaluate_gate(gate, X_test, y_test, gate_name)
        results.append(metrics)

    # Print comparison table
    print("\n" + "=" * 70)
    print("  PERBANDINGAN GATE CLASSIFIER")
    print("=" * 70)
    print(f"{'Gate':<20} {'Acc':>6} {'F1-W':>6} {'F1-SOP':>7} {'P-BUKAN':>8} {'R-BUKAN':>8}")
    print("-" * 70)
    for r in results:
        if r.get("status") == "not_available":
            print(f"{r['gate']:<20} {'N/A':>6} {'N/A':>6} {'N/A':>7} {'N/A':>8} {'N/A':>8}")
        else:
            print(
                f"{r['gate']:<20} "
                f"{r['accuracy']:>6.4f} "
                f"{r['f1_weighted']:>6.4f} "
                f"{r['f1_sop']:>7.4f} "
                f"{r['precision_bukan_sop']:>8.4f} "
                f"{r['recall_bukan_sop']:>8.4f}"
            )
    print("=" * 70)
    print("Target: precision_bukan_sop >= 0.95 (hindari false reject klausa SOP)")

    # Save results
    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nHasil disimpan: {RESULTS_PATH}")

    # Log to MLflow if URI provided
    if mlflow_uri:
        try:
            import mlflow
            mlflow.set_tracking_uri(mlflow_uri)
            mlflow.set_experiment("sop_gate_evaluation")
            for r in results:
                if r.get("status") == "not_available":
                    continue
                with mlflow.start_run(run_name=r["gate"]):
                    mlflow.log_param("gate_model", r["model"])
                    mlflow.log_param("n_test", r["n_test"])
                    mlflow.log_metric("accuracy", r["accuracy"])
                    mlflow.log_metric("f1_weighted", r["f1_weighted"])
                    mlflow.log_metric("f1_sop", r["f1_sop"])
                    mlflow.log_metric("precision_bukan_sop", r["precision_bukan_sop"])
                    mlflow.log_metric("recall_bukan_sop", r["recall_bukan_sop"])
                    mlflow.log_metric("avg_confidence", r["avg_confidence"])
                    mlflow.log_artifact(str(RESULTS_PATH))
            print("MLflow runs logged.")
        except Exception as e:
            print(f"MLflow logging gagal: {e}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mlflow-uri", default=None)
    args = parser.parse_args()
    run_evaluation(mlflow_uri=args.mlflow_uri)
