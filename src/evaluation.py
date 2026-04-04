"""
evaluation.py — Evaluation Metrics untuk Multi-Agent Compliance Auditor
=========================================================================
Modul untuk menghitung Confusion Matrix, Precision, Recall, F1-Score,
dan metrik lainnya untuk evaluasi sistem.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ComplianceEvaluator:
    """
    Evaluator untuk sistem compliance audit.
    Menghitung metrik berbasis Confusion Matrix.
    """
    
    # Label mapping
    LABELS = ["COMPLIANT", "NON_COMPLIANT", "NOT_ADDRESSED", "NEEDS_REVIEW"]
    
    def __init__(self):
        self.predictions: List[Dict] = []
        self.ground_truth: List[Dict] = []
        self.results: List[Dict] = []
    
    def add_result(
        self,
        clause_id: str,
        predicted: str,
        expected: str,
        bi_verdict: str = None,
        ojk_verdict: str = None,
        confidence: float = None
    ):
        """
        Add a single audit result for evaluation.
        """
        self.results.append({
            "clause_id": clause_id,
            "predicted": predicted,
            "expected": expected,
            "bi_verdict": bi_verdict,
            "ojk_verdict": ojk_verdict,
            "confidence": confidence
        })
    
    def load_results_from_file(self, filepath: str):
        """
        Load results from JSON file.
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for result in data.get("results", []):
            self.results.append({
                "clause_id": result.get("clause_id"),
                "predicted": result.get("final_status") or result.get("predicted"),
                "expected": result.get("expected") or result.get("status"),
                "bi_verdict": result.get("bi_verdict", {}).get("verdict"),
                "ojk_verdict": result.get("ojk_verdict", {}).get("verdict"),
                "confidence": result.get("overall_confidence")
            })
    
    def calculate_confusion_matrix(self) -> Dict:
        """
        Calculate confusion matrix for multi-class classification.
        """
        # Initialize matrix
        matrix = {pred: {exp: 0 for exp in self.LABELS} for pred in self.LABELS}
        
        for result in self.results:
            pred = result["predicted"]
            exp = result["expected"]
            
            if pred not in self.LABELS:
                continue
            if exp not in self.LABELS:
                # Map common variations
                exp_mapping = {
                    "NON_COMPLIANT": "NON_COMPLIANT",
                    "COMPLIANT": "COMPLIANT",
                    "NOT_ADDRESSED": "NOT_ADDRESSED",
                    "NEEDS_REVIEW": "NEEDS_REVIEW"
                }
                exp = exp_mapping.get(exp, "NOT_ADDRESSED")
            
            matrix[pred][exp] += 1
        
        return matrix
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate Precision, Recall, F1-Score for each class.
        """
        cm = self.calculate_confusion_matrix()
        
        metrics = {}
        
        for label in self.LABELS:
            # True Positives: pred=label, expected=label
            tp = cm[label][label]
            
            # False Positives: pred=label, expected!=label
            fp = sum(cm[label][other] for other in self.LABELS if other != label)
            
            # False Negatives: pred!=label, expected=label
            fn = sum(cm[other][label] for other in self.LABELS if other != label)
            
            # True Negatives: pred!=label, expected!=label
            tn = sum(
                cm[other][exp]
                for other in self.LABELS if other != label
                for exp in self.LABELS if exp != label
            )
            
            # Precision
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            
            # Recall
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            
            # F1-Score
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            
            # Accuracy per class
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0
            
            metrics[label] = {
                "TP": tp,
                "FP": fp,
                "FN": fn,
                "TN": tn,
                "Precision": round(precision, 4),
                "Recall": round(recall, 4),
                "F1-Score": round(f1, 4),
                "Accuracy": round(accuracy, 4)
            }
        
        # Macro averages
        macro_precision = sum(m["Precision"] for m in metrics.values()) / len(self.LABELS)
        macro_recall = sum(m["Recall"] for m in metrics.values()) / len(self.LABELS)
        macro_f1 = sum(m["F1-Score"] for m in metrics.values()) / len(self.LABELS)
        
        # Overall accuracy
        total_correct = sum(cm[label][label] for label in self.LABELS)
        total_samples = len(self.results)
        overall_accuracy = total_correct / total_samples if total_samples > 0 else 0
        
        metrics["MACRO_AVG"] = {
            "Precision": round(macro_precision, 4),
            "Recall": round(macro_recall, 4),
            "F1-Score": round(macro_f1, 4)
        }
        
        metrics["OVERALL"] = {
            "Accuracy": round(overall_accuracy, 4),
            "Total_Samples": total_samples,
            "Correct_Predictions": total_correct
        }
        
        return metrics
    
    def calculate_agent_metrics(self) -> Dict:
        """
        Calculate metrics for each agent (BI and OJK).
        """
        bi_results = {"compliant": 0, "non_compliant": 0, "not_addressed": 0, "needs_review": 0}
        ojk_results = {"compliant": 0, "non_compliant": 0, "not_addressed": 0, "needs_review": 0}
        
        bi_violations = 0
        ojk_violations = 0
        
        for result in self.results:
            bi_v = result.get("bi_verdict", "")
            ojk_v = result.get("ojk_verdict", "")
            
            if bi_v in bi_results:
                bi_results[bi_v.lower()] = bi_results.get(bi_v.lower(), 0) + 1
            if ojk_v in ojk_results:
                ojk_results[ojk_v.lower()] = ojk_results.get(ojk_v.lower(), 0) + 1
        
        return {
            "BI_Agent": {
                "verdict_distribution": bi_results,
                "total_violations_found": bi_violations
            },
            "OJK_Agent": {
                "verdict_distribution": ojk_results,
                "total_violations_found": ojk_violations
            }
        }
    
    def generate_report(self, output_path: str = None) -> str:
        """
        Generate evaluation report in Markdown format.
        """
        metrics = self.calculate_metrics()
        cm = self.calculate_confusion_matrix()
        agent_metrics = self.calculate_agent_metrics()
        
        report_lines = [
            "# LAPORAN EVALUASI MULTI-AGENT COMPLIANCE AUDITOR",
            "",
            f"**Tanggal:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 1. RINGKASAN EKSEKUTIF",
            "",
            f"- **Total Klausa Diaudit:** {metrics['OVERALL']['Total_Samples']}",
            f"- **Prediksi Benar:** {metrics['OVERALL']['Correct_Predictions']}",
            f"- **Akurasi Keseluruhan:** {metrics['OVERALL']['Accuracy']*100:.2f}%",
            f"- **Macro F1-Score:** {metrics['MACRO_AVG']['F1-Score']:.4f}",
            "",
            "---",
            "",
            "## 2. CONFUSION MATRIX",
            "",
            "| Prediksi \\ Aktual | " + " | ".join(self.LABELS) + " |",
            "|" + "|".join(["---"] * (len(self.LABELS) + 1)) + "|"
        ]
        
        for pred in self.LABELS:
            row = f"| **{pred}** |"
            for exp in self.LABELS:
                row += f" {cm[pred][exp]} |"
            report_lines.append(row)
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 3. METRIK PER KELAS",
            "",
            "| Kelas | Precision | Recall | F1-Score | Support |",
            "|-------|-----------|--------|----------|---------|"
        ])
        
        for label in self.LABELS:
            p = metrics[label]["Precision"]
            r = metrics[label]["Recall"]
            f1 = metrics[label]["F1-Score"]
            support = sum(cm[label].values())
            report_lines.append(f"| {label} | {p:.4f} | {r:.4f} | {f1:.4f} | {support} |")
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 4. ANALISIS PER AGENT",
            "",
            "### 4.1 BI Specialist Agent",
            "",
            f"- **Distribusi Verdict:** {agent_metrics['BI_Agent']['verdict_distribution']}",
            "",
            "### 4.2 OJK Specialist Agent",
            "",
            f"- **Distribusi Verdict:** {agent_metrics['OJK_Agent']['verdict_distribution']}",
            "",
            "---",
            "",
            "## 5. DETAIL HASIL AUDIT",
            "",
            "| No | ID Klausa | Prediksi | Expected | Status |",
            "|----|-----------|----------|----------|--------|"
        ])
        
        for i, result in enumerate(self.results, 1):
            status = "✓" if result["predicted"] == result["expected"] else "✗"
            report_lines.append(
                f"| {i} | {result['clause_id']} | {result['predicted']} | {result['expected']} | {status} |"
            )
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 6. KESIMPULAN",
            "",
            f"Sistem Multi-Agent Compliance Auditor berhasil mengaudit **{metrics['OVERALL']['Total_Samples']}** klausa ",
            f"dengan akurasi **{metrics['OVERALL']['Accuracy']*100:.2f}%**.",
            "",
            f"- **Macro Precision:** {metrics['MACRO_AVG']['Precision']:.4f}",
            f"- **Macro Recall:** {metrics['MACRO_AVG']['Recall']:.4f}",
            f"- **Macro F1-Score:** {metrics['MACRO_AVG']['F1-Score']:.4f}",
            "",
            "---",
            "",
            "*Laporan dibuat secara otomatis oleh sistem evaluasi.*"
        ])
        
        report = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Laporan disimpan di: {output_path}")
        
        return report
    
    def save_metrics_json(self, output_path: str):
        """
        Save metrics to JSON file for further analysis.
        """
        output = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.calculate_metrics(),
            "confusion_matrix": self.calculate_confusion_matrix(),
            "agent_metrics": self.calculate_agent_metrics(),
            "results": self.results
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        print(f"Metrics disimpan di: {output_path}")


def compare_with_expected(results_file: str, expected_labels: Dict[str, str]) -> 'ComplianceEvaluator':
    """
    Compare audit results with expected labels.
    
    Args:
        results_file: Path to audit results JSON
        expected_labels: Dict mapping clause_id to expected status
    
    Returns:
        ComplianceEvaluator with results loaded
    """
    evaluator = ComplianceEvaluator()
    evaluator.load_results_from_file(results_file)
    
    # Add expected labels
    for result in evaluator.results:
        clause_id = result.get("clause_id")
        if clause_id in expected_labels:
            result["expected"] = expected_labels[clause_id]
    
    return evaluator


# Expected labels for SOP Dummy
SOP_DUMMY_EXPECTED = {
    "KLAUSA-01": "COMPLIANT",
    "KLAUSA-02": "NON_COMPLIANT",
    "KLAUSA-03": "NON_COMPLIANT",
    "KLAUSA-04": "NON_COMPLIANT",
    "BAB II - Data Pribadi": "COMPLIANT",
    "BAB III - Keluhan": "NON_COMPLIANT",
    "BAB IV - Batas Saldo": "NON_COMPLIANT",
}


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python evaluation.py <results.json>")
        print("       python evaluation.py <results.json> --expected")
        sys.exit(1)
    
    results_path = sys.argv[1]
    use_expected = "--expected" in sys.argv
    
    evaluator = ComplianceEvaluator()
    
    if use_expected:
        evaluator.load_results_from_file(results_path)
        # Apply expected labels
        for result in evaluator.results:
            clause_id = result.get("clause_id", "")
            result["expected"] = SOP_DUMMY_EXPECTED.get(clause_id, "NOT_ADDRESSED")
    else:
        evaluator.load_results_from_file(results_path)
    
    # Generate reports
    base_path = Path(results_path).stem
    output_dir = Path(results_path).parent
    
    evaluator.generate_report(output_dir / f"{base_path}_evaluation_report.md")
    evaluator.save_metrics_json(output_dir / f"{base_path}_metrics.json")