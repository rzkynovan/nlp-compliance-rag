import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field, asdict

from app.config import settings, MODEL_COSTS

logger = logging.getLogger(__name__)


@dataclass
class UsageRecord:
    timestamp: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    endpoint: str
    clause_id: Optional[str] = None


@dataclass
class DailyUsage:
    date: str
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    api_calls: int = 0
    records: list = field(default_factory=list)
    
    def to_dict(self):
        return {
            "date": self.date,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "api_calls": self.api_calls,
        }


class CostTracker:
    def __init__(self, log_dir: str = "./data/costs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.budget_limit = settings.DAILY_BUDGET_LIMIT_USD
        self.enabled = settings.COST_OPTIMIZATION_MODE == "development"
    
    def _get_today_file(self) -> Path:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"usage_{today}.json"
    
    def _load_today_usage(self) -> DailyUsage:
        today_file = self._get_today_file()
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        if today_file.exists():
            try:
                with open(today_file, "r") as f:
                    data = json.load(f)
                return DailyUsage(
                    date=data["date"],
                    total_tokens=data["total_tokens"],
                    total_cost_usd=data["total_cost_usd"],
                    api_calls=data["api_calls"],
                    records=data.get("records", [])
                )
            except Exception:
                pass
        
        return DailyUsage(date=today_str)
    
    def _save_usage(self, usage: DailyUsage) -> None:
        today_file = self._get_today_file()
        with open(today_file, "w") as f:
            json.dump(asdict(usage), f, indent=2)
    
    def calculate_cost(
        self, 
        model: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> float:
        costs = MODEL_COSTS.get(model, {"input": 0, "output": 0})
        input_cost = (input_tokens / 1_000_000) * costs["input"]
        output_cost = (output_tokens / 1_000_000) * costs["output"]
        return round(input_cost + output_cost, 6)
    
    def estimate_cost(
        self,
        model: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int = 500
    ) -> float:
        return self.calculate_cost(model, estimated_input_tokens, estimated_output_tokens)
    
    def check_budget(self, estimated_cost: float = 0) -> bool:
        usage = self._load_today_usage()
        remaining = self.budget_limit - usage.total_cost_usd
        return remaining >= estimated_cost
    
    def record_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        endpoint: str,
        clause_id: Optional[str] = None
    ) -> UsageRecord:
        usage = self._load_today_usage()
        
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        record = UsageRecord(
            timestamp=datetime.utcnow().isoformat(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            endpoint=endpoint,
            clause_id=clause_id
        )
        
        usage.total_tokens += input_tokens + output_tokens
        usage.total_cost_usd += cost
        usage.api_calls += 1
        usage.records.append(asdict(record))
        
        self._save_usage(usage)
        
        if usage.total_cost_usd >= self.budget_limit * 0.8:
            logger.warning(f"BUDGET WARNING: ${usage.total_cost_usd:.2f} / ${self.budget_limit:.2f} used today")
        
        if usage.total_cost_usd >= self.budget_limit:
            logger.error(f"BUDGET EXCEEDED: ${usage.total_cost_usd:.2f} / ${self.budget_limit:.2f}")
        
        return record
    
    def get_today_stats(self) -> Dict:
        usage = self._load_today_usage()
        remaining = max(0, self.budget_limit - usage.total_cost_usd)
        
        return {
            "date": usage.date,
            "total_tokens": usage.total_tokens,
            "total_cost_usd": round(usage.total_cost_usd, 4),
            "api_calls": usage.api_calls,
            "budget_limit_usd": self.budget_limit,
            "remaining_usd": round(remaining, 4),
            "budget_percentage": round(usage.total_cost_usd / self.budget_limit * 100, 1)
        }
    
    def get_monthly_stats(self) -> Dict:
        monthly_cost = 0.0
        monthly_calls = 0
        
        for usage_file in self.log_dir.glob("usage_*.json"):
            try:
                with open(usage_file, "r") as f:
                    data = json.load(f)
                monthly_cost += data["total_cost_usd"]
                monthly_calls += data["api_calls"]
            except Exception:
                continue
        
        return {
            "monthly_cost_usd": round(monthly_cost, 4),
            "monthly_api_calls": monthly_calls
        }


cost_tracker = CostTracker()