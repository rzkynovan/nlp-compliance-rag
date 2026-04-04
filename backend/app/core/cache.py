import hashlib
import json
import logging
from typing import Optional, Any, Dict
from datetime import timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditCache:
    def __init__(
        self, 
        cache_dir: str = "./data/cache",
        ttl_hours: int = 24
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
        self._memory_cache: Dict[str, Any] = {}
    
    def _compute_hash(self, clause: str, regulator: str) -> str:
        content = f"{clause}|{regulator}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def _get_cache_path(self, cache_key: str) -> Path:
        return self.cache_dir / f"{cache_key}.json"
    
    def get(self, clause: str, regulator: str) -> Optional[Dict]:
        cache_key = self._compute_hash(clause, regulator)
        
        if cache_key in self._memory_cache:
            logger.debug(f"Cache HIT (memory): {cache_key}")
            return self._memory_cache[cache_key]
        
        cache_path = self._get_cache_path(cache_key)
        
        if cache_path.exists():
            try:
                with open(cache_path, "r") as f:
                    cached = json.load(f)
                
                from datetime import datetime
                cached_time = datetime.fromisoformat(cached["timestamp"])
                if datetime.utcnow() - cached_time < self.ttl:
                    self._memory_cache[cache_key] = cached["result"]
                    logger.debug(f"Cache HIT (disk): {cache_key}")
                    return cached["result"]
                else:
                    logger.debug(f"Cache EXPIRED: {cache_key}")
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        
        logger.debug(f"Cache MISS: {cache_key}")
        return None
    
    def set(self, clause: str, regulator: str, result: Dict) -> None:
        cache_key = self._compute_hash(clause, regulator)
        
        self._memory_cache[cache_key] = result
        
        cache_path = self._get_cache_path(cache_key)
        try:
            from datetime import datetime
            with open(cache_path, "w") as f:
                json.dump({
                    "timestamp": datetime.utcnow().isoformat(),
                    "clause": clause[:100],
                    "regulator": regulator,
                    "result": result
                }, f)
            logger.debug(f"Cache SET: {cache_key}")
        except Exception as e:
            logger.warning(f"Cache write error: {e}")
    
    def clear(self) -> None:
        self._memory_cache.clear()
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict:
        disk_cache_count = len(list(self.cache_dir.glob("*.json")))
        return {
            "memory_cache_size": len(self._memory_cache),
            "disk_cache_count": disk_cache_count,
            "ttl_hours": self.ttl.total_seconds() / 3600
        }


class EmbeddingCache:
    def __init__(self, cache_dir: str = "./data/embeddings_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _compute_hash(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[list]:
        cache_key = self._compute_hash(text)
        cache_path = self.cache_dir / f"{cache_key}.npy"
        
        if cache_path.exists():
            try:
                import numpy as np
                return np.load(str(cache_path)).tolist()
            except Exception:
                pass
        return None
    
    def set(self, text: str, embedding: list) -> None:
        cache_key = self._compute_hash(text)
        cache_path = self.cache_dir / f"{cache_key}.npy"
        
        try:
            import numpy as np
            np.save(str(cache_path), np.array(embedding))
        except Exception:
            pass