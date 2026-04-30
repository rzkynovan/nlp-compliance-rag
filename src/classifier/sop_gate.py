"""
sop_gate.py — SOP Gate Classifier abstraction + 3 implementations.

Digunakan sebagai pre-filter sebelum RAG pipeline:
  - RuleBasedGate   : regex keyword matching (sudah ada via QueryAnalyzer)
  - IndoBERTGate    : fine-tuned indobenchmark/indobert-base-p1
  - GPTFineTunedGate: fine-tuned gpt-5.4-mini via OpenAI API

Interface:
    gate = load_gate(model_type="indobert", threshold=0.8)
    result = gate.predict("klausa SOP disini")
    # result.is_sop → bool
    # result.confidence → float
    # result.model → str
"""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "classifier"


@dataclass
class GateResult:
    is_sop: bool
    confidence: float
    model: str
    raw_label: str


class BaseSOPGate(ABC):
    model_name: str = "base"

    @abstractmethod
    def predict(self, text: str) -> GateResult:
        """Return GateResult for the given text."""
        pass

    def is_available(self) -> bool:
        return True


# ── Gate A: Rule-based ────────────────────────────────────────────────────────

_SOP_KEYWORDS = [
    # Regulatori
    r"\bsop\b", r"\bregulasi\b", r"\bpasal\b", r"\bayat\b",
    r"\bpbi\b", r"\bpojk\b", r"\bsebi\b",
    # Transaksi
    r"\btransaksi\b", r"\bsaldo\b", r"\blimit\b", r"\btransfer\b",
    r"\btop.?up\b", r"\bpenarikan\b", r"\bpembayaran\b",
    # Akun & identitas
    r"\bkyc\b", r"\bverifikasi\b", r"\bidentitas\b", r"\bakun\b",
    r"\bnasabah\b", r"\bpengguna\b", r"\bpemegang\b",
    # Layanan
    r"\bpengaduan\b", r"\bkeluhan\b", r"\bsla\b", r"\blayanan\b",
    r"\bkomplain\b", r"\bpenyelesaian\b",
    # Data & privasi
    r"\bdata.pribadi\b", r"\bprivasi\b", r"\bpersetujuan\b", r"\bconsent\b",
    r"\benkripsi\b", r"\baes.256\b",
    # Hukum & kewajiban
    r"\bwajib\b", r"\bdilarang\b", r"\bketentuan\b", r"\bsyarat\b",
    r"\bkewajiban\b", r"\bhak\b", r"\btanggung.jawab\b",
    # Moneter
    r"\brp\.?\s*\d", r"\bmiliar\b", r"\bjuta\b", r"\bribu\b",
    r"\bhari.kerja\b", r"\bbulan\b",
]

_NON_SOP_PATTERNS = [
    r"^halo\b", r"^hai\b", r"^selamat\s+(pagi|siang|malam|sore)",
    r"^terima.kasih", r"^maaf\b", r"^oke\b", r"^ya\b",
    r"^\d+$", r"^[a-z]{1,5}$",
]

_SOP_COMPILED     = [re.compile(p, re.IGNORECASE) for p in _SOP_KEYWORDS]
_NON_SOP_COMPILED = [re.compile(p, re.IGNORECASE) for p in _NON_SOP_PATTERNS]


class RuleBasedGate(BaseSOPGate):
    model_name = "rule_based"

    def predict(self, text: str) -> GateResult:
        text = text.strip()

        if len(text) < 20:
            return GateResult(is_sop=False, confidence=0.95, model=self.model_name, raw_label="BUKAN_SOP")

        for pat in _NON_SOP_COMPILED:
            if pat.search(text):
                return GateResult(is_sop=False, confidence=0.90, model=self.model_name, raw_label="BUKAN_SOP")

        matches = sum(1 for pat in _SOP_COMPILED if pat.search(text))
        total   = len(_SOP_COMPILED)
        score   = min(matches / max(total * 0.15, 1), 1.0)

        is_sop     = score >= 0.3 or matches >= 2
        confidence = score if is_sop else (1.0 - score)
        confidence = max(0.5, min(0.99, confidence))

        return GateResult(
            is_sop=is_sop,
            confidence=confidence,
            model=self.model_name,
            raw_label="SOP" if is_sop else "BUKAN_SOP",
        )


# ── Gate B: IndoBERT fine-tuned ───────────────────────────────────────────────

class IndoBERTGate(BaseSOPGate):
    model_name = "indobert"

    def __init__(self, model_dir: Optional[Path] = None):
        self._model_dir = model_dir or (MODEL_DIR / "indobert_gate")
        self._model = None
        self._tokenizer = None

    def is_available(self) -> bool:
        return (self._model_dir / "config.json").exists()

    def _load(self):
        if self._model is not None:
            return
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch
            self._tokenizer = AutoTokenizer.from_pretrained(str(self._model_dir))
            self._model = AutoModelForSequenceClassification.from_pretrained(str(self._model_dir))
            self._model.eval()
            self._torch = torch
        except Exception as e:
            raise RuntimeError(f"Gagal load IndoBERT model dari {self._model_dir}: {e}")

    def predict(self, text: str) -> GateResult:
        self._load()
        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True, max_length=128, padding=True
        )
        with self._torch.no_grad():
            logits = self._model(**inputs).logits
            probs  = self._torch.softmax(logits, dim=-1)[0]

        label_id  = probs.argmax().item()
        id2label  = self._model.config.id2label
        raw_label = id2label.get(label_id, str(label_id))
        confidence = float(probs[label_id])

        is_sop = raw_label == "SOP"
        return GateResult(is_sop=is_sop, confidence=confidence, model=self.model_name, raw_label=raw_label)


# ── Gate C: GPT fine-tuned ────────────────────────────────────────────────────

class GPTFineTunedGate(BaseSOPGate):
    model_name = "gpt_finetuned"

    def __init__(self, model_id: Optional[str] = None, api_key: Optional[str] = None):
        self._model_id = model_id or os.getenv("GPT_FINETUNED_MODEL_ID", "")
        self._api_key  = api_key or os.getenv("OPENAI_API_KEY", "")
        self._client   = None

    def is_available(self) -> bool:
        return bool(self._model_id) and bool(self._api_key)

    def _load(self):
        if self._client is not None:
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)
        except ImportError:
            raise RuntimeError("openai package tidak terinstall.")

    def predict(self, text: str) -> GateResult:
        self._load()
        response = self._client.chat.completions.create(
            model=self._model_id,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Kamu adalah classifier yang menentukan apakah sebuah teks adalah "
                        "klausa SOP atau dokumen T&C layanan keuangan digital yang valid, atau bukan. "
                        "Jawab hanya dengan satu kata: 'SOP' atau 'BUKAN_SOP'."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Klasifikasikan teks berikut:\n\n{text}",
                },
            ],
            max_tokens=5,
            temperature=0,
        )
        raw = response.choices[0].message.content.strip().upper()
        is_sop = "SOP" in raw and "BUKAN" not in raw
        return GateResult(
            is_sop=is_sop,
            confidence=0.95 if is_sop else 0.95,
            model=self.model_name,
            raw_label="SOP" if is_sop else "BUKAN_SOP",
        )


# ── Factory ───────────────────────────────────────────────────────────────────

def load_gate(model_type: str = "rule_based", threshold: float = 0.8) -> BaseSOPGate:
    """
    Load the appropriate gate based on model_type config.
    Falls back to RuleBasedGate if requested model not available.
    """
    if model_type == "indobert":
        gate = IndoBERTGate()
        if gate.is_available():
            return gate
        print("[SOPGate] IndoBERT model tidak ditemukan, fallback ke rule_based.")
    elif model_type == "gpt_finetuned":
        gate = GPTFineTunedGate()
        if gate.is_available():
            return gate
        print("[SOPGate] GPT fine-tuned model ID tidak ditemukan, fallback ke rule_based.")

    return RuleBasedGate()
