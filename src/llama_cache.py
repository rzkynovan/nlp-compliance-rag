"""
llama_cache.py — LlamaParse Caching untuk Optimasi Biaya
=========================================================
Cache hasil parsing PDF untuk menghindari biaya berulang.

LlamaParse Free Tier: 1000 pages/month
LlamaParse Pro Tier: $0.003/page
"""

import os
import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class LlamaParseCache:
    """
    Cache untuk hasil parsing LlamaParse.
    
    Menyimpan hasil parsing ke disk untuk menghindari:
    - Re-parsing PDF yang sama
    - Biaya API berulang
    - Latensi parsing
    
    Usage:
        cache = LlamaParseCache()
        
        # Check cache first
        cached = cache.get(pdf_path)
        if cached:
            return cached
        
        # Parse only if not cached
        result = llama_parse.parse(pdf_path)
        cache.set(pdf_path, result)
    """
    
    def __init__(
        self,
        cache_dir: str = "./data/llama_cache",
        max_age_days: int = 30
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(days=max_age_days)
        self.manifest_path = self.cache_dir / "manifest.json"
        self.manifest = self._load_manifest()
    
    def _load_manifest(self) -> Dict[str, Any]:
        """Load cache manifest."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"files": {}, "stats": {"total_pages": 0, "total_saved": 0}}
    
    def _save_manifest(self):
        """Save cache manifest."""
        with open(self.manifest_path, "w") as f:
            json.dump(self.manifest, f, indent=2)
    
    def _compute_file_hash(self, file_path: str) -> str:
        """Compute SHA256 hash of file for cache key."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
    
    def _get_cache_path(self, file_hash: str) -> Path:
        """Get cache file path for a hash."""
        return self.cache_dir / f"{file_hash}.json"
    
    def get(self, file_path: str) -> Optional[List[Dict]]:
        """
        Get cached result for a PDF file.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            Cached documents or None if not cached/expired
        """
        file_hash = self._compute_file_hash(file_path)
        cache_path = self._get_cache_path(file_hash)
        
        if not cache_path.exists():
            logger.debug(f"Cache miss: {file_path}")
            return None
        
        # Check manifest for metadata
        if file_hash in self.manifest["files"]:
            entry = self.manifest["files"][file_hash]
            cached_time = datetime.fromisoformat(entry["timestamp"])
            
            if datetime.utcnow() - cached_time > self.max_age:
                logger.info(f"Cache expired: {file_path} (age: {(datetime.utcnow() - cached_time).days} days)")
                return None
            
            # Load cached data
            try:
                with open(cache_path, "r") as f:
                    data = json.load(f)
                
                logger.info(f"Cache hit: {file_path} ({entry.get('pages', 0)} pages)")
                return data.get("documents", [])
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
                return None
        
        return None
    
    def set(
        self,
        file_path: str,
        documents: List[Any],
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Cache parsing result for a PDF file.
        
        Args:
            file_path: Path to PDF file
            documents: List of LlamaIndex Document objects
            metadata: Optional metadata (pages, regulator, etc.)
        """
        file_hash = self._compute_file_hash(file_path)
        cache_path = self._get_cache_path(file_hash)
        
        # Convert documents to serializable format
        serializable_docs = []
        total_pages = 0
        
        for doc in documents:
            doc_dict = {
                "text": doc.text if hasattr(doc, "text") else str(doc),
                "metadata": doc.metadata if hasattr(doc, "metadata") else {},
            }
            serializable_docs.append(doc_dict)
            total_pages += 1
        
        # Save to cache
        cache_data = {
            "source_file": os.path.basename(file_path),
            "file_hash": file_hash,
            "timestamp": datetime.utcnow().isoformat(),
            "pages": total_pages,
            "documents": serializable_docs,
            "metadata": metadata or {}
        }
        
        try:
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
            
            # Update manifest
            self.manifest["files"][file_hash] = {
                "source_file": os.path.basename(file_path),
                "timestamp": datetime.utcnow().isoformat(),
                "pages": total_pages,
                "metadata": metadata or {}
            }
            self.manifest["stats"]["total_pages"] += total_pages
            self.manifest["stats"]["total_saved"] += 1
            self._save_manifest()
            
            logger.info(f"Cached: {file_path} -> {cache_path} ({total_pages} pages)")
            
            # Calculate saved cost
            saved_cost = total_pages * 0.003  # Pro tier price
            logger.info(f"Estimated savings: ${saved_cost:.4f}")
            
        except Exception as e:
            logger.error(f"Cache write error: {e}")
    
    def clear(self, older_than_days: Optional[int] = None):
        """
        Clear cache entries.
        
        Args:
            older_than_days: Only clear entries older than N days. If None, clear all.
        """
        if older_than_days is None:
            # Clear all
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
            self.manifest = {"files": {}, "stats": {"total_pages": 0, "total_saved": 0}}
            self._save_manifest()
            logger.info("Cache cleared completely")
        else:
            # Clear old entries only
            cutoff = datetime.utcnow() - timedelta(days=older_than_days)
            to_remove = []
            
            for file_hash, entry in self.manifest["files"].items():
                cached_time = datetime.fromisoformat(entry["timestamp"])
                if cached_time < cutoff:
                    cache_path = self._get_cache_path(file_hash)
                    if cache_path.exists():
                        cache_path.unlink()
                    to_remove.append(file_hash)
            
            for file_hash in to_remove:
                del self.manifest["files"][file_hash]
            
            self._save_manifest()
            logger.info(f"Cleared {len(to_remove)} cache entries older than {older_than_days} days")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.manifest["files"])
        total_pages = self.manifest["stats"]["total_pages"]
        estimated_saved_usd = total_pages * 0.003  # Pro tier pricing
        
        return {
            "cache_dir": str(self.cache_dir),
            "total_entries": total_entries,
            "total_pages_cached": total_pages,
            "estimated_savings_usd": round(estimated_saved_usd, 4),
            "max_age_days": self.max_age.days,
            "entries": [
                {
                    "file": entry["source_file"],
                    "pages": entry.get("pages", 0),
                    "cached_at": entry["timestamp"]
                }
                for entry in self.manifest["files"].values()
            ]
        }
    
    def estimate_cost(self, pages: int, tier: str = "pro") -> float:
        """
        Estimate parsing cost.
        
        Args:
            pages: Number of pages to parse
            tier: "free" or "pro"
        
        Returns:
            Estimated cost in USD
        """
        if tier == "free":
            # Free tier: 1000 pages/month, then can't parse
            remaining_free = 1000 - self.manifest["stats"]["total_pages"]
            if pages <= remaining_free:
                return 0.0
            else:
                # Would need Pro tier
                return (pages - remaining_free) * 0.003
        else:
            # Pro tier: $0.003/page + $30/month
            return pages * 0.003


# Singleton instance
_cache_instance: Optional[LlamaParseCache] = None


def get_cache() -> LlamaParseCache:
    """Get or create singleton cache instance."""
    global _cache_instance
    if _cache_instance is None:
        cache_dir = os.getenv("LLAMA_CACHE_DIR", "./data/llama_cache")
        _cache_instance = LlamaParseCache(cache_dir=cache_dir)
    return _cache_instance