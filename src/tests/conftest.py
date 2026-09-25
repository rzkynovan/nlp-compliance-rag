"""
conftest.py — konfigurasi test untuk modul src/ (agents, retrieval, evaluasi).

Dependensi berat (llama_index, chromadb, anthropic) di-stub agar test berjalan
tanpa API key maupun vector store. Jalankan dari root repo:

    python -m pytest src/tests -q
"""

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _stub(name: str):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _stub_if_missing(name: str, attrs=()):
    try:
        __import__(name)
    except Exception:
        parts = name.split(".")
        for i in range(1, len(parts) + 1):
            _stub(".".join(parts[:i]))
        mod = sys.modules[name]
        for attr in attrs:
            setattr(mod, attr, MagicMock(name=f"{name}.{attr}"))


_stub_if_missing("llama_index.core", ["VectorStoreIndex", "Settings", "StorageContext", "Document"])
_stub_if_missing("llama_index.embeddings.openai", ["OpenAIEmbedding"])
_stub_if_missing("llama_index.llms.openai", ["OpenAI"])
_stub_if_missing("llama_index.vector_stores.chroma", ["ChromaVectorStore"])
_stub_if_missing("chromadb", ["PersistentClient"])
