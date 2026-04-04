# Experiment Plan - Compliance Audit RAG

## Status Implementasi MLflow

| Komponen | Status | Lokasi |
|----------|--------|--------|
| ExperimentTracker | ✅ Implemented | `backend/app/ml/tracking.py` |
| API Endpoints | ✅ Implemented | `backend/app/api/v1/experiments.py` |
| MLflow Server | ✅ Running | `http://localhost:5001` |
| Artifact Logging | ✅ Implemented | JSON results |
| Run Comparison | ✅ Implemented | Compare multiple runs |

---

## Daftar Experiment untuk Thesis

### Kategori 1: Hyperparameter Tuning

#### Experiment 1.1: Effect of Top-K Retrieval

**Tujuan:** Menemukan jumlah artikel optimal yang di-retrieve untuk hasil terbaik.

```python
# Konfigurasi
params = {
    "experiment_name": "top_k_tuning",
    "params": [
        {"top_k": 3},
        {"top_k": 5},
        {"top_k": 10},
        {"top_k": 20},
    ]
}

# Metrics yang diukur
metrics = [
    "recall_at_k",      # Recall@K
    "precision_at_k",   # Precision@K
    "latency_ms",       # Processing time
    "total_cost_usd",   # Biaya API
    "confidence_score"  # Model confidence
]
```

**Hypothesis:** Top-K yang lebih besar meningkatkan recall tapi menambah latency dan cost.

**Sample Size:** 50 klausa SOP per konfigurasi

---

#### Experiment 1.2: Temperature Effect on Verdicts

**Tujuan:** Menganalisis pengaruh temperature terhadap konsistensi verdict.

```python
# Konfigurasi
params = {
    "experiment_name": "temperature_analysis",
    "params": [
        {"temperature": 0.0},
        {"temperature": 0.1},  # Baseline
        {"temperature": 0.3},
        {"temperature": 0.5},
        {"temperature": 0.7},
    ]
}

# Metrics
metrics = [
    "verdict_consistency",   # Variance dalam verdict
    "reasoning_diversity",    # Keanekaragaman reasoning
    "confidence_variance",    # Variance confidence score
    "hallucination_rate"      # Rate of incorrect claims
]
```

**Hypothesis:** Temperature rendah (0.0-0.1) menghasilkan verdict lebih konsisten.

---

### Kategori 2: Model Comparison

#### Experiment 2.1: LLM Model Comparison

**Tujuan:** Membandingkan performa berbagai model LLM.

```python
# Konfigurasi
models = [
    "gpt-4o",
    "gpt-4o-mini",      # Baseline
    "gpt-4-turbo",
    "gpt-3.5-turbo",
    "claude-3-sonnet",   # Jika ada akses
]

params = {
    "experiment_name": "model_comparison",
    "variables": "model",
    "fixed_params": {
        "top_k": 5,
        "temperature": 0.1,
        "embedding_model": "text-embedding-3-small"
    }
}

# Metrics
metrics = [
    "accuracy",             # Akurasi vs ground truth
    "reasoning_quality",     # Kualitas reasoning (human eval)
    "latency_ms",           # Processing time
    "cost_per_query_usd",   # Biaya per query
    "f1_score"              # F1 Score
]
```

**Expected Results:**
| Model | Accuracy | Cost/Query | Latency | F1 Score |
|-------|----------|-------------|---------|----------|
| gpt-4o | ~95% | $0.15 | ~25s | ~0.93 |
| gpt-4o-mini | ~92% | $0.02 | ~16s | ~0.89 |
| gpt-3.5-turbo | ~85% | $0.01 | ~12s | ~0.80 |

---

#### Experiment 2.2: Embedding Model Comparison

**Tujuan:** Mengevaluasi dampak model embedding pada retrieval quality.

```python
# Konfigurasi
embedding_models = [
    "text-embedding-3-small",  # Baseline
    "text-embedding-3-large",
    "text-embedding-ada-002",
]

params = {
    "experiment_name": "embedding_comparison",
    "fixed_params": {
        "model": "gpt-4o-mini",
        "top_k": 5,
        "temperature": 0.1
    }
}

# Metrics
metrics = [
    "retrieval_recall@k",    # Retrieval recall
    "retrieval_precision@k", # Retrieval precision
    "retrieval_mrr",         # Mean Reciprocal Rank
    "embedding_cost_usd"     # Embedding cost
]
```

---

### Kategori 3: Retrieval Strategy

#### Experiment 3.1: Retrieval Method Comparison

**Tujuan:** Membandingkan metode retrieval yang berbeda.

```python
# Konfigurasi
retrieval_methods = [
    {"method": "semantic", "rerank": False},
    {"method": "semantic", "rerank": True},
    {"method": "hybrid", "rerank": False},    # Semantic + Keyword
    {"method": "hybrid", "rerank": True},
    {"method": "bm25", "rerank": False},      # Pure keyword
]

params = {
    "experiment_name": "retrieval_methods",
    "fixed_params": {
        "model": "gpt-4o-mini",
        "top_k": 5
    }
}

# Metrics
metrics = [
    "retrieval_recall",
    "retrieval_precision",
    "final_accuracy",
    "latency_ms"
]
```

**Hypothesis:** Hybrid retrieval dengan reranking memberikan hasil terbaik.

---

#### Experiment 3.2: Reranking Strategy

**Tujuan:** Evaluasi efek reranking pada retrieval quality.

```python
# Konfigurasi
reranking_strategies = [
    {"rerank": False},
    {"rerank": True, "reranker": "cross-encoder"},
    {"rerank": True, "reranker": "bge-reranker"},
    {"rerank": True, "reranker": "cohere-rerank"},
]

params = {
    "experiment_name": "reranking_comparison"
}
```

---

### Kategori 4: Agent Architecture

#### Experiment 4.1: Single-Agent vs Multi-Agent

**Tujuan:** Membuktikan bahwa multi-agent lebih baik dari single-agent.

```python
# Konfigurasi
architectures = [
    {"architecture": "single_agent", "agent": "general"},
    {"architecture": "single_agent", "agent": "bi_only"},
    {"architecture": "single_agent", "agent": "ojk_only"},
    {"architecture": "multi_agent", "regulators": ["BI", "OJK"]},
]

params = {
    "experiment_name": "architecture_comparison",
    "fixed_params": {
        "model": "gpt-4o-mini",
        "top_k": 5
    }
}

# Metrics
metrics = [
    "regulation_coverage",     # Seberapa lengkap regulasi dicover
    "conflict_detection_rate", # Rate of detecting conflicts
    "verdict_accuracy",        # Accuracy vs ground truth
    "false_positive_rate",     # False alarms
    "false_negative_rate"      # Missed violations
]
```

**Critical Experiment untuk Thesis:**
- Ini membuktikan bahwa arsitektur multi-agent superior untuk compliance audit

---

#### Experiment 4.2: Conflict Resolution Strategy

**Tujuan:** Menguji strategi penyelesaian konflik antar regulator.

```python
# Konfigurasi
resolution_strategies = [
    {"strategy": "strict"},           # Apply both regulations
    {"strategy": "hierarchy"},        # BI priority over OJK
    {"strategy": "consumer_first"},   # Consumer protection priority
    {"strategy": "lenient"},          # Most lenient interpretation
]

params = {
    "experiment_name": "conflict_resolution"
}

# Ground truth cases dengan konflik
test_cases = [
    {
        "clause": "...",
        "bi_verdict": "COMPLIANT",
        "ojk_verdict": "NON_COMPLIANT",
        "expected_resolution": "..."
    }
]
```

---

### Kategori 5: Cost Optimization

#### Experiment 5.1: Cost vs Accuracy Trade-off

**Tujuan:** Menemukan konfigurasi optimal dengan biaya minimal.

```python
# Konfigurasi
configs = [
    {"model": "gpt-4o", "top_k": 10, "embedding": "large"},    # Expensive
    {"model": "gpt-4o", "top_k": 5, "embedding": "small"},     # Medium
    {"model": "gpt-4o-mini", "top_k": 5, "embedding": "small"}, # Cheap (baseline)
    {"model": "gpt-4o-mini", "top_k": 3, "embedding": "small"}, # Cheapest
]

params = {
    "experiment_name": "cost_accuracy_tradeoff"
}

# Metrics
metrics = [
    "accuracy",
    "total_cost_usd",
    "accuracy_per_dollar"  # Efficiency metric
]
```

---

#### Experiment 5.2: Caching Effectiveness

**Tujuan:** Mengukur penghematan dari caching mechanism.

```python
# Konfigurasi
cache_configs = [
    {"cache_enabled": False},
    {"cache_enabled": True, "ttl_hours": 1},
    {"cache_enabled": True, "ttl_hours": 24},    # Baseline
    {"cache_enabled": True, "ttl_hours": 72},
]

# Test dengan klausa berulang
test_scenarios = {
    "unique_queries": 100,
    "repeat_rate": [0.0, 0.2, 0.4, 0.6, 0.8]
}
```

---

### Kategori 6: Prompt Engineering

#### Experiment 6.1: Prompt Template Comparison

**Tujuan:** Menguji efektifitas berbagai prompt template.

```python
# Konfigurasi
prompt_versions = [
    {"prompt": "v1_basic", "description": "Simple prompt"},
    {"prompt": "v2_detailed", "description": "Detailed instructions"},
    {"prompt": "v3_cot", "description": "Chain of Thought"},
    {"prompt": "v4_few_shot", "description": "Few-shot examples"},
    {"prompt": "v5_self_consistency", "description": "Self-consistency with voting"},
]

params = {
    "experiment_name": "prompt_engineering",
    "fixed_params": {
        "model": "gpt-4o-mini",
        "top_k": 5,
        "temperature": 0.1
    }
}

# Metrics
metrics = [
    "reasoning_quality",    # Human evaluation
    "verdict_accuracy",
    "hallucination_rate",
    "prompt_tokens",
    "output_tokens"
]
```

---

### Kategori 7: Robustness Testing

#### Experiment 7.1: Adversarial Input Testing

**Tujuan:** Menguji robustness sistem terhadap input yang sulit.

```python
# Test cases
adversarial_cases = [
    {"type": "ambiguity", "clause": "..."},      # Ambiguous clauses
    {"type": "edge_case", "clause": "..."},       # Edge cases
    {"type": "multi_regulation", "clause": "..."}, # Multiple regulations
    {"type": "contradictory", "clause": "..."},   # Contradictory statements
    {"type": "incomplete", "clause": "..."},      # Incomplete information
]

params = {
    "experiment_name": "robustness_testing"
}

# Metrics
metrics = [
    "error_rate",
    "graceful_degradation",  # Can system handle errors?
    "confidence_on_edge_cases"
]
```

---

#### Experiment 7.2: Regulation Coverage Testing

**Tujuan:** Menguji coverage sistem terhadap berbagai regulasi.

```python
# Test per regulation
regulations = [
    {"regulation": "PBI_222320", "topics": [...]},
    {"regulation": "PBI_230621", "topics": [...]},
    {"regulation": "POJK_22_2023", "topics": [...]},
]

# Metrics per regulation
metrics = [
    "coverage_score",       # How many topics covered
    "retrieval_accuracy",   # Correct article retrieved
    "verdict_accuracy"       # Correct verdict
]
```

---

### Kategori 8: Ablation Study

#### Experiment 8.1: Component Ablation

**Tujuan:** Mengukur kontribusi setiap komponen.

```python
# Konfigurasi
ablations = [
    {"full_system": True},                          # Complete system
    {"without_rag": True},                          # Without retrieval
    {"without_conflict_resolver": True},           # Direct verdict
    {"single_agent": True},                         # Single agent only
    {"without_evidence": True},                     # No evidence trail
]

params = {
    "experiment_name": "component_ablation"
}

# Metrics
metrics = [
    "accuracy",
    "recall",
    "precision",
    "f1_score",
    "latency_ms"
]
```

---

## Cara Menjalankan Experiment

### Via Python Script

```python
# backend/scripts/run_experiment.py

from app.ml.tracking import ExperimentTracker
from app.services.rag_service import get_rag_service
import asyncio

async def run_top_k_experiment():
    tracker = ExperimentTracker()
    service = get_rag_service()
    
    test_cases = load_test_cases("data/test_cases.json")
    
    for top_k in [3, 5, 10, 20]:
        run_id = tracker.start_run(
            experiment_name="top_k_tuning",
            params={"top_k": top_k}
        )
        
        results = []
        for case in test_cases:
            result = await service.analyze_with_rag(
                clause=case["clause"],
                regulator="all",
                top_k=top_k
            )
            results.append(result)
        
        metrics = calculate_metrics(results, test_cases)
        tracker.log_metrics(run_id, metrics)
        tracker.end_run(run_id)

if __name__ == "__main__":
    asyncio.run(run_top_k_experiment())
```

### Via API

```bash
# Create experiment
curl -X POST http://localhost:8000/api/v1/experiments/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "top_k_tuning",
    "description": "Effect of Top-K on retrieval quality",
    "params": {"top_k": 5}
  }'

# Run audit with tracking
curl -X POST http://localhost:8000/api/v1/audit/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "clause": "Saldo maksimal untuk akun unverified adalah Rp 10.000.000",
    "regulator": "all",
    "top_k": 5,
    "track_experiment": true
  }'

# Get results
curl http://localhost:8000/api/v1/experiments/list

# Compare runs
curl -X POST http://localhost:8000/api/v1/experiments/compare \
  -H "Content-Type: application/json" \
  -d '["run_id_1", "run_id_2", "run_id_3"]'
```

### Via MLflow UI

```
1. Buka http://localhost:5001
2. Buat experiment baru
3. Jalankan audit dengan parameter berbeda
4. Compare runs di dashboard
5. Download artifacts untuk analisis
```

---

## Metrics Definitions

| Metric | Formula | Description |
|--------|---------|-------------|
| `accuracy` | (TP + TN) / (TP + TN + FP + FN) | Overall accuracy |
| `precision@k` | TP@k / (TP@k + FP@k) | Precision at K |
| `recall@k` | TP@k / (TP@k + FN@k) | Recall at K |
| `f1_score` | 2 * (P * R) / (P + R) | Harmonic mean |
| `latency_ms` | End - Start | Processing time |
| `cost_usd` | input_tokens * 0.15/1M + output_tokens * 0.60/1M | API cost |
| `confidence_score` | Model confidence | 0.0 - 1.0 |
| `verdict_consistency` | 1 - variance | Consistency across runs |

---

## Ground Truth Dataset

Untuk evaluasi, diperlukan dataset dengan label yang sudah ditandai:

```json
// data/test_cases.json
{
  "test_cases": [
    {
      "id": "TC001",
      "clause": "Saldo maksimal untuk akun unverified adalah Rp 10.000.000",
      "regulator": "BI",
      "ground_truth": {
        "verdict": "NON_COMPLIANT",
        "violations": ["PBI No. 23/6/2021 Pasal 160"],
        "confidence": 0.95
      }
    },
    {
      "id": "TC002",
      "clause": "Customer data disimpan selama 5 tahun",
      "regulator": "OJK",
      "ground_truth": {
        "verdict": "PARTIALLY_COMPLIANT",
        "violations": ["POJK 22/2023 Pasal 8"],
        "confidence": 0.8
      }
    }
  ]
}
```

---

## Experiment Schedule untuk Thesis

### Bab IV - Hasil dan Evaluasi

| Week | Experiment | Output |
|------|------------|--------|
| 1 | Top-K Tuning | Optimal top_k value |
| 2 | Model Comparison | Best model selection |
| 3 | Retrieval Strategy | Best retrieval method |
| 4 | Multi-Agent vs Single-Agent | Architecture justification |
| 5 | Prompt Engineering | Optimal prompt |
| 6 | Ablation Study | Component contribution |
| 7 | Cost Analysis | Cost-effectiveness curve |
| 8 | Robustness Testing | System reliability |

---

## MLflow Dashboard Preview

```
http://localhost:5001

┌─────────────────────────────────────────────────────────────┐
│ Experiments                                                  │
├─────────────────────────────────────────────────────────────┤
│ experiment_id: 1                                             │
│ experiment_name: compliance_audit_v1                          │
│                                                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Run ID      │ top_k │ accuracy │ recall │ latency_ms   │ │
│ ├─────────────────────────────────────────────────────────┤ │
│ │ abc123      │ 3     │ 0.85     │ 0.78   │ 12500        │ │
│ │ def456      │ 5     │ 0.92     │ 0.89   │ 15953        │ │
│ │ ghi789      │ 10    │ 0.93     │ 0.92   │ 22000        │ │
│ │ jkl012      │ 20    │ 0.94     │ 0.95   │ 35000        │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                              │
│ Best Run: ghi789 (top_k=10, accuracy=0.93)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Recommended Experiments untuk Thesis Start

### Priority 1 (Wajib)
1. **Top-K Tuning** - Menentukan parameter optimal
2. **Model Comparison** - Justifikasi pemilihan model
3. **Multi-Agent vs Single-Agent** - Proof of concept

### Priority 2 (Penting)
4. **Retrieval Strategy** - Optimasi retrieval
5. **Cost vs Accuracy Trade-off** - Analisis biaya

### Priority 3 (Opsional)
6. **Prompt Engineering** - Optimasi prompt
7. **Robustness Testing** - Validasi sistem
8. **Ablation Study** - Deep dive analysis

---

*Last updated: 2025-04-05*