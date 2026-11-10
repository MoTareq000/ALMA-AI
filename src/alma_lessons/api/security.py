"""
API Security, Authentication & Guardrails
=========================================
Implements X-API-Key authentication, per-key rate limiting,
active generation concurrency caps, and CORS helpers.
"""

import time
import logging
from typing import Optional, Dict, List
from collections import defaultdict
from fastapi import Request, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader

from ..config import config
from ..storage import job_manager

logger = logging.getLogger(__name__)

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Track warned state so we don't spam logs on every request
_auth_warning_logged = False


def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> Optional[str]:
    """Validate X-API-Key header against configured ALMA_API_KEYS.
    If ALMA_AUTH_DISABLED=true, allows requests through with a warning.
    """
    global _auth_warning_logged
    if config.alma_auth_disabled:
        if not _auth_warning_logged:
            logger.warning("ALMA_AUTH_DISABLED=true is set: API key authentication is DISABLED for development.")
            _auth_warning_logged = True
        return "dev-user"

    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API Key. Include 'X-API-Key' header in your request."
        )

    valid_keys = [k.strip() for k in config.alma_api_keys.split(",") if k.strip()]
    if not valid_keys or api_key not in valid_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key."
        )

    return api_key


class TokenRateLimiter:
    """Sliding-window rate limiter for expensive token-spending endpoints."""

    def __init__(self, requests_per_hour: Optional[int] = None):
        self.limit = requests_per_hour or config.rate_limit_per_hour
        self.window_seconds = 3600
        # In-memory history: key -> list of request timestamps
        self._history: Dict[str, List[float]] = defaultdict(list)

    def __call__(self, request: Request, api_key: Optional[str] = Depends(verify_api_key)):
        client_ident = api_key or request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - self.window_seconds

        # Clean up old timestamps
        timestamps = [t for t in self._history[client_ident] if t > cutoff]
        self._history[client_ident] = timestamps

        if len(timestamps) >= config.rate_limit_per_hour:
            retry_after = int(self.window_seconds - (now - timestamps[0]))
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: maximum {config.rate_limit_per_hour} requests per hour for AI operations. Try again in {max(retry_after, 1)} seconds."
            )

        self._history[client_ident].append(now)


rate_limiter = TokenRateLimiter()


def check_max_active_generations():
    """Guardrail to prevent unbounded concurrent generation jobs piling up."""
    jobs = job_manager.list_jobs()
    active_count = sum(1 for j in jobs if j.status in ("pending", "processing"))
    if active_count >= config.max_active_generations:
        raise HTTPException(
            status_code=429,
            detail=f"Too many active generation jobs ({active_count}/{config.max_active_generations}). Please wait for current jobs to finish."
        )

