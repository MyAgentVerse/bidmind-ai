"""Lightweight OpenAI usage tracker — file-based, no DB changes.

Logs every OpenAI API call with token counts and estimated cost.
Stores in a JSON-lines file that the admin dashboard can read.
Thread-safe via file append (each line is one JSON record).

Pricing (as of 2024, gpt-4o-mini):
  - Input:  $0.15 / 1M tokens
  - Output: $0.60 / 1M tokens
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Where to store the usage log
USAGE_LOG_PATH = Path(os.environ.get(
    "OPENAI_USAGE_LOG", "/tmp/bidmind_openai_usage.jsonl"
))

# Pricing per 1M tokens (gpt-4o-mini defaults)
PRICING = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
}

_lock = threading.Lock()


def log_openai_usage(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    endpoint: str = "chat.completions",
    project_id: Optional[str] = None,
    section: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a single OpenAI API call. Returns the record written."""
    total_tokens = prompt_tokens + completion_tokens
    pricing = PRICING.get(model, PRICING.get("gpt-4o-mini"))
    cost = (
        (prompt_tokens / 1_000_000) * pricing["input"]
        + (completion_tokens / 1_000_000) * pricing["output"]
    )

    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "model": model,
        "endpoint": endpoint,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": round(cost, 6),
        "project_id": project_id,
        "section": section,
    }

    try:
        with _lock:
            with open(USAGE_LOG_PATH, "a") as f:
                f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.warning(f"Could not write OpenAI usage log: {e}")

    return record


def get_usage_summary() -> Dict[str, Any]:
    """Read the usage log and return aggregated stats."""
    records = _read_log()

    if not records:
        return {
            "total_calls": 0,
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_tokens": 0,
            "total_estimated_cost_usd": 0.0,
            "calls_today": 0,
            "cost_today_usd": 0.0,
            "by_model": {},
            "by_endpoint": {},
            "recent_calls": [],
        }

    today = datetime.utcnow().date().isoformat()

    total_prompt = sum(r.get("prompt_tokens", 0) for r in records)
    total_completion = sum(r.get("completion_tokens", 0) for r in records)
    total_cost = sum(r.get("estimated_cost_usd", 0) for r in records)

    today_records = [r for r in records if r.get("timestamp", "").startswith(today)]
    cost_today = sum(r.get("estimated_cost_usd", 0) for r in today_records)

    # By model
    by_model = {}
    for r in records:
        m = r.get("model", "unknown")
        if m not in by_model:
            by_model[m] = {"calls": 0, "tokens": 0, "cost_usd": 0.0}
        by_model[m]["calls"] += 1
        by_model[m]["tokens"] += r.get("total_tokens", 0)
        by_model[m]["cost_usd"] += r.get("estimated_cost_usd", 0)

    # By endpoint
    by_endpoint = {}
    for r in records:
        ep = r.get("endpoint", "unknown")
        if ep not in by_endpoint:
            by_endpoint[ep] = {"calls": 0, "tokens": 0}
        by_endpoint[ep]["calls"] += 1
        by_endpoint[ep]["tokens"] += r.get("total_tokens", 0)

    return {
        "total_calls": len(records),
        "total_prompt_tokens": total_prompt,
        "total_completion_tokens": total_completion,
        "total_tokens": total_prompt + total_completion,
        "total_estimated_cost_usd": round(total_cost, 4),
        "calls_today": len(today_records),
        "cost_today_usd": round(cost_today, 4),
        "by_model": by_model,
        "by_endpoint": by_endpoint,
        "recent_calls": records[-20:][::-1],  # Last 20, newest first
    }


def _read_log() -> List[Dict]:
    """Read all records from the usage log."""
    if not USAGE_LOG_PATH.exists():
        return []
    try:
        records = []
        with open(USAGE_LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return records
    except Exception as e:
        logger.warning(f"Could not read OpenAI usage log: {e}")
        return []
