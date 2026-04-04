"""
test_cache.py — unit tests for AuditCache.

Tests: hash consistency, memory cache hit, disk cache hit,
TTL expiry, set/get roundtrip, clear, and stats.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from app.core.cache import AuditCache


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def cache(tmp_path):
    """AuditCache backed by a temporary directory (no real disk state)."""
    return AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=24)


@pytest.fixture
def result_payload():
    return {
        "final_status": "NON_COMPLIANT",
        "overall_confidence": 0.92,
        "violations": ["Pasal 160"],
        "recommendations": ["Kurangi saldo"],
    }


# ── Hash computation ──────────────────────────────────────────────────────────

class TestComputeHash:
    def test_same_input_same_hash(self, cache):
        h1 = cache._compute_hash("clause A", "BI")
        h2 = cache._compute_hash("clause A", "BI")
        assert h1 == h2

    def test_different_clause_different_hash(self, cache):
        h1 = cache._compute_hash("clause A", "BI")
        h2 = cache._compute_hash("clause B", "BI")
        assert h1 != h2

    def test_different_regulator_different_hash(self, cache):
        h1 = cache._compute_hash("same clause", "BI")
        h2 = cache._compute_hash("same clause", "OJK")
        assert h1 != h2

    def test_hash_length_16(self, cache):
        h = cache._compute_hash("any clause", "all")
        assert len(h) == 16

    def test_hash_is_hex(self, cache):
        h = cache._compute_hash("clause", "BI")
        int(h, 16)  # raises ValueError if not valid hex


# ── Cache MISS ────────────────────────────────────────────────────────────────

class TestCacheMiss:
    def test_miss_returns_none(self, cache):
        result = cache.get("unknown clause", "all")
        assert result is None

    def test_miss_on_empty_cache(self, cache, result_payload):
        # Nothing has been set yet
        assert cache.get("clause", "BI") is None


# ── Set + Memory hit ──────────────────────────────────────────────────────────

class TestCacheSet:
    def test_set_then_get_memory_hit(self, cache, result_payload):
        cache.set("clause X", "BI", result_payload)
        retrieved = cache.get("clause X", "BI")
        assert retrieved == result_payload

    def test_set_creates_disk_file(self, cache, result_payload, tmp_path):
        cache.set("clause Y", "OJK", result_payload)
        cache_key = cache._compute_hash("clause Y", "OJK")
        disk_path = cache._get_cache_path(cache_key)
        assert disk_path.exists()

    def test_disk_file_contains_timestamp(self, cache, result_payload, tmp_path):
        cache.set("clause Z", "all", result_payload)
        cache_key = cache._compute_hash("clause Z", "all")
        with open(cache._get_cache_path(cache_key)) as f:
            data = json.load(f)
        assert "timestamp" in data
        assert "result" in data

    def test_memory_cache_populated_after_set(self, cache, result_payload):
        cache.set("clause A", "BI", result_payload)
        cache_key = cache._compute_hash("clause A", "BI")
        assert cache_key in cache._memory_cache


# ── Disk hit (cold start — memory cache empty) ────────────────────────────────

class TestDiskHit:
    def test_disk_hit_after_cold_start(self, tmp_path, result_payload):
        # Write to disk via first cache instance
        c1 = AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=24)
        c1.set("disk clause", "BI", result_payload)

        # Second cache instance has empty memory cache
        c2 = AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=24)
        retrieved = c2.get("disk clause", "BI")
        assert retrieved == result_payload

    def test_disk_hit_populates_memory(self, tmp_path, result_payload):
        c1 = AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=24)
        c1.set("clause", "OJK", result_payload)

        c2 = AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=24)
        c2.get("clause", "OJK")

        cache_key = c2._compute_hash("clause", "OJK")
        assert cache_key in c2._memory_cache


# ── TTL expiry ───────────────────────────────────────���────────────────────────

class TestTTLExpiry:
    def test_expired_entry_returns_none(self, tmp_path, result_payload):
        cache = AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=1)
        cache.set("old clause", "BI", result_payload)

        # Patch datetime so the cached timestamp looks old
        cache_key = cache._compute_hash("old clause", "BI")
        cache_path = cache._get_cache_path(cache_key)

        # Rewrite the file with a timestamp 2 hours ago
        old_timestamp = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        with open(cache_path, "r") as f:
            data = json.load(f)
        data["timestamp"] = old_timestamp
        with open(cache_path, "w") as f:
            json.dump(data, f)

        # Clear memory cache to force disk read
        cache._memory_cache.clear()

        result = cache.get("old clause", "BI")
        assert result is None

    def test_fresh_entry_returns_result(self, cache, result_payload):
        cache.set("fresh clause", "all", result_payload)
        # Clear memory to force disk read
        cache._memory_cache.clear()
        result = cache.get("fresh clause", "all")
        assert result == result_payload


# ── Clear ─────────────────────────────────────────────────────────────────────

class TestCacheClear:
    def test_clear_removes_memory(self, cache, result_payload):
        cache.set("c1", "BI", result_payload)
        cache.set("c2", "OJK", result_payload)
        cache.clear()
        assert len(cache._memory_cache) == 0

    def test_clear_removes_disk_files(self, cache, result_payload, tmp_path):
        cache.set("c1", "BI", result_payload)
        cache.set("c2", "OJK", result_payload)
        cache.clear()
        json_files = list(cache.cache_dir.glob("*.json"))
        assert len(json_files) == 0

    def test_get_after_clear_is_miss(self, cache, result_payload):
        cache.set("clause", "all", result_payload)
        cache.clear()
        assert cache.get("clause", "all") is None


# ── Stats ─────────────────────────────────────────────────────────────────────

class TestCacheStats:
    def test_stats_empty(self, cache):
        stats = cache.get_stats()
        assert stats["memory_cache_size"] == 0
        assert stats["disk_cache_count"] == 0
        assert stats["ttl_hours"] == 24.0

    def test_stats_after_set(self, cache, result_payload):
        cache.set("c1", "BI", result_payload)
        cache.set("c2", "OJK", result_payload)
        stats = cache.get_stats()
        assert stats["memory_cache_size"] == 2
        assert stats["disk_cache_count"] == 2

    def test_stats_after_clear(self, cache, result_payload):
        cache.set("c1", "BI", result_payload)
        cache.clear()
        stats = cache.get_stats()
        assert stats["memory_cache_size"] == 0
        assert stats["disk_cache_count"] == 0


# ── Corrupt disk file (graceful degradation) ──────────────────────────────────

class TestCorruptDiskFile:
    def test_corrupt_json_returns_none(self, tmp_path, result_payload):
        cache = AuditCache(cache_dir=str(tmp_path / "cache"), ttl_hours=24)
        cache.set("clause", "BI", result_payload)

        cache_key = cache._compute_hash("clause", "BI")
        cache_path = cache._get_cache_path(cache_key)

        # Corrupt the file
        cache_path.write_text("{ invalid json }")
        cache._memory_cache.clear()

        # Should not raise, should return None
        result = cache.get("clause", "BI")
        assert result is None
