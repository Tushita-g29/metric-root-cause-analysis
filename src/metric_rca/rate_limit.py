from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import DefaultDict, Deque

from fastapi import HTTPException, Request

DEFAULT_EXPLANATION_RATE_LIMIT = 3
DEFAULT_EXPLANATION_RATE_WINDOW_SECONDS = 3600

_limit_lock = threading.Lock()
_client_request_times: DefaultDict[str, Deque[float]] = defaultdict(deque)


def _get_explanation_rate_limit() -> int:
    value = os.getenv("EXPLANATION_RATE_LIMIT")
    if value is None:
        return DEFAULT_EXPLANATION_RATE_LIMIT
    try:
        limit = int(value)
    except ValueError:
        return DEFAULT_EXPLANATION_RATE_LIMIT
    return limit if limit > 0 else DEFAULT_EXPLANATION_RATE_LIMIT


def _get_explanation_rate_window_seconds() -> int:
    value = os.getenv("EXPLANATION_RATE_WINDOW_SECONDS")
    if value is None:
        return DEFAULT_EXPLANATION_RATE_WINDOW_SECONDS
    try:
        window_seconds = int(value)
    except ValueError:
        return DEFAULT_EXPLANATION_RATE_WINDOW_SECONDS
    return window_seconds if window_seconds > 0 else DEFAULT_EXPLANATION_RATE_WINDOW_SECONDS


def get_client_ip(request: Request) -> str:
    """Return the client IP derived from X-Forwarded-For when available, otherwise the request socket host."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_ip = forwarded_for.split(",", 1)[0].strip()
        if first_ip:
            return first_ip

    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def reset_limiters() -> None:
    """Clear in-memory rate-limit state for tests and cleanup."""
    with _limit_lock:
        _client_request_times.clear()


def enforce_explanation_rate_limit(request: Request) -> None:
    """Protect the public explanation endpoint with a thread-safe sliding-window rate limit."""
    client_ip = get_client_ip(request)
    limit = _get_explanation_rate_limit()
    window_seconds = _get_explanation_rate_window_seconds()
    now = time.monotonic()
    cutoff = now - window_seconds

    with _limit_lock:
        timestamps = _client_request_times[client_ip]
        while timestamps and timestamps[0] <= cutoff:
            timestamps.popleft()

        if len(timestamps) >= limit:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Too many explanation requests for this IP. Please wait a moment and try again "
                    f"within the next {window_seconds} seconds."
                ),
            )

        timestamps.append(now)
