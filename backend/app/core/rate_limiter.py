import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict
import logging

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    requests: int = 0
    tokens: int = 0
    window_start: float = 0.0


class RateLimiter:
    def __init__(self):
        self.requests_per_minute = settings.RATE_LIMIT_REQUESTS_PER_MINUTE
        self.tokens_per_minute = settings.RATE_LIMIT_TOKENS_PER_MINUTE
        self.window_seconds = 60
        self._clients: Dict[str, RateLimitState] = defaultdict(RateLimitState)
        self._lock = asyncio.Lock()
    
    async def _cleanup_old_windows(self, current_time: float) -> None:
        for client_id in list(self._clients.keys()):
            state = self._clients[client_id]
            if current_time - state.window_start > self.window_seconds:
                del self._clients[client_id]
    
    async def check_rate_limit(
        self, 
        client_id: str = "default",
        estimated_tokens: int = 1000
    ) -> tuple[bool, Dict]:
        async with self._lock:
            current_time = time.time()
            await self._cleanup_old_windows(current_time)
            
            state = self._clients[client_id]
            
            if current_time - state.window_start > self.window_seconds:
                state.requests = 0
                state.tokens = 0
                state.window_start = current_time
            
            requests_remaining = self.requests_per_minute - state.requests
            tokens_remaining = self.tokens_per_minute - state.tokens
            
            if requests_remaining <= 0:
                retry_after = int(self.window_seconds - (current_time - state.window_start))
                logger.warning(
                    f"Rate limit exceeded for {client_id}: "
                    f"{state.requests}/{self.requests_per_minute} requests"
                )
                return False, {
                    "error": "rate_limit_exceeded",
                    "retry_after_seconds": retry_after,
                    "limit_type": "requests"
                }
            
            if tokens_remaining < estimated_tokens:
                retry_after = int(self.window_seconds - (current_time - state.window_start))
                logger.warning(
                    f"Token limit exceeded for {client_id}: "
                    f"{state.tokens}/{self.tokens_per_minute} tokens"
                )
                return False, {
                    "error": "token_limit_exceeded",
                    "retry_after_seconds": retry_after,
                    "limit_type": "tokens"
                }
            
            state.requests += 1
            state.tokens += estimated_tokens
            
            return True, {
                "requests_remaining": requests_remaining - 1,
                "tokens_remaining": tokens_remaining - estimated_tokens,
                "reset_in_seconds": int(self.window_seconds - (current_time - state.window_start))
            }
    
    async def wait_if_needed(
        self,
        client_id: str = "default",
        estimated_tokens: int = 1000,
        max_wait_seconds: int = 30
    ) -> bool:
        is_allowed, info = await self.check_rate_limit(client_id, estimated_tokens)
        
        if is_allowed:
            return True
        
        retry_after = info.get("retry_after_seconds", 60)
        if retry_after > max_wait_seconds:
            return False
        
        logger.info(f"Rate limited, waiting {retry_after} seconds...")
        await asyncio.sleep(retry_after)
        return True
    
    def get_stats(self) -> Dict:
        current_time = time.time()
        active_clients = []
        
        for client_id, state in self._clients.items():
            if current_time - state.window_start <= self.window_seconds:
                active_clients.append({
                    "client_id": client_id,
                    "requests": state.requests,
                    "tokens": state.tokens,
                    "window_start": state.window_start
                })
        
        return {
            "requests_per_minute": self.requests_per_minute,
            "tokens_per_minute": self.tokens_per_minute,
            "active_clients": active_clients
        }


rate_limiter = RateLimiter()