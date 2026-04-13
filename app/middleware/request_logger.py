"""Lightweight request/error logger middleware — file-based, no DB.

Logs every API request with method, path, status code, duration,
and any error details. Stores in a JSON-lines file.
"""

import json
import logging
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

REQUEST_LOG_PATH = Path(os.environ.get(
    "REQUEST_LOG_PATH", "/tmp/bidmind_requests.jsonl"
))

# Keep last N errors in memory for fast dashboard access
_recent_errors: List[Dict] = []
_MAX_ERRORS = 200


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Log all requests + errors to a file and in-memory buffer."""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        error_detail = None
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as e:
            error_detail = f"{type(e).__name__}: {str(e)}"
            raise

        finally:
            duration_ms = round((time.time() - start) * 1000, 1)
            path = request.url.path
            method = request.method

            # Skip noisy paths
            if path in ("/api/health", "/api/docs", "/api/openapi.json", "/"):
                return

            record = {
                "timestamp": datetime.utcnow().isoformat(),
                "method": method,
                "path": path,
                "status": status_code,
                "duration_ms": duration_ms,
                "client": request.client.host if request.client else None,
                "error": error_detail,
            }

            # Log errors to memory buffer
            if status_code >= 400 or error_detail:
                record["query"] = str(request.url.query) if request.url.query else None
                _recent_errors.append(record)
                if len(_recent_errors) > _MAX_ERRORS:
                    _recent_errors.pop(0)

            # Write to file (async-safe via append)
            try:
                with open(REQUEST_LOG_PATH, "a") as f:
                    f.write(json.dumps(record) + "\n")
            except Exception:
                pass  # Don't crash the app for logging


def get_recent_errors(limit: int = 50) -> List[Dict]:
    """Get recent errors from in-memory buffer."""
    return list(reversed(_recent_errors[-limit:]))


def get_request_stats() -> Dict[str, Any]:
    """Read request log and return stats."""
    if not REQUEST_LOG_PATH.exists():
        return {"total_requests": 0, "errors": 0, "by_status": {}, "by_path": {}}

    try:
        records = []
        with open(REQUEST_LOG_PATH, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass

        today = datetime.utcnow().date().isoformat()
        today_records = [r for r in records if r.get("timestamp", "").startswith(today)]

        by_status = {}
        for r in records:
            s = str(r.get("status", "?"))
            by_status[s] = by_status.get(s, 0) + 1

        # Top paths by request count
        by_path = {}
        for r in records:
            p = r.get("path", "?")
            by_path[p] = by_path.get(p, 0) + 1
        top_paths = dict(sorted(by_path.items(), key=lambda x: x[1], reverse=True)[:20])

        # Error rate
        total = len(records)
        errors = sum(1 for r in records if r.get("status", 200) >= 400)

        return {
            "total_requests": total,
            "requests_today": len(today_records),
            "total_errors": errors,
            "error_rate_pct": round((errors / total * 100), 1) if total else 0,
            "by_status": by_status,
            "top_paths": top_paths,
            "avg_duration_ms": round(
                sum(r.get("duration_ms", 0) for r in records) / total, 1
            ) if total else 0,
        }
    except Exception as e:
        logger.warning(f"Could not read request log: {e}")
        return {"total_requests": 0, "error": str(e)}
