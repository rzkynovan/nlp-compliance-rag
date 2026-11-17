"""Metrik Prometheus untuk endpoint /metrics (dibaca dashboard Grafana compliance-audit)."""
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

AUDIT_REQUESTS = Counter("audit_requests", "Jumlah audit klausul yang selesai")
AUDIT_LATENCY = Histogram(
    "audit_latency_seconds",
    "Latensi audit end-to-end per klausul",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 20, 30, 60, 120),
)
AUDIT_STATUS = Counter("audit_compliance_status", "Verdik akhir audit", ["status"])
AUDIT_GATE = Counter("audit_gate_decision", "Keputusan gate classifier", ["model", "decision"])
LLM_TOKENS = Counter("llm_tokens_used", "Token LLM yang tercatat di cost tracker", ["model", "kind"])


def record_audit(final_status: str, latency_ms: float, gate_model: str, gate_decision: str) -> None:
    AUDIT_REQUESTS.inc()
    AUDIT_LATENCY.observe(latency_ms / 1000)
    AUDIT_STATUS.labels(status=final_status).inc()
    AUDIT_GATE.labels(model=gate_model, decision=gate_decision).inc()


def record_tokens(model: str, input_tokens: int, output_tokens: int) -> None:
    LLM_TOKENS.labels(model=model, kind="input").inc(input_tokens)
    LLM_TOKENS.labels(model=model, kind="output").inc(output_tokens)


def render() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
