from __future__ import annotations

from fastapi import HTTPException

from metric_rca.rate_limit import (
    DEFAULT_EXPLANATION_RATE_LIMIT,
    DEFAULT_EXPLANATION_RATE_WINDOW_SECONDS,
    enforce_explanation_rate_limit,
    get_client_ip,
    reset_limiters,
)


class DummyClient:
    def __init__(self, host: str):
        self.host = host


class DummyRequest:
    def __init__(self, headers=None, host="127.0.0.1"):
        self.headers = headers or {}
        self.client = DummyClient(host)


def test_requests_within_limit_pass() -> None:
    reset_limiters()
    request = DummyRequest(headers={"x-forwarded-for": "10.0.0.5"})

    for _ in range(DEFAULT_EXPLANATION_RATE_LIMIT):
        enforce_explanation_rate_limit(request)

    assert True


def test_fourth_request_gets_429() -> None:
    reset_limiters()
    request = DummyRequest(headers={"x-forwarded-for": "10.0.0.6"})

    for _ in range(DEFAULT_EXPLANATION_RATE_LIMIT):
        enforce_explanation_rate_limit(request)

    try:
        enforce_explanation_rate_limit(request)
    except HTTPException as exc:
        assert exc.status_code == 429
        assert "Too many explanation requests" in exc.detail
    else:
        raise AssertionError("Expected HTTP 429 after exceeding the explanation rate limit.")


def test_different_client_ips_have_separate_limits() -> None:
    reset_limiters()
    first_ip = DummyRequest(headers={"x-forwarded-for": "10.0.0.7"})
    second_ip = DummyRequest(headers={"x-forwarded-for": "10.0.0.8"})

    for _ in range(DEFAULT_EXPLANATION_RATE_LIMIT):
        enforce_explanation_rate_limit(first_ip)

    try:
        enforce_explanation_rate_limit(first_ip)
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("Expected the first IP to hit its own limit after its third request.")

    for _ in range(DEFAULT_EXPLANATION_RATE_LIMIT):
        enforce_explanation_rate_limit(second_ip)

    try:
        enforce_explanation_rate_limit(second_ip)
    except HTTPException as exc:
        assert exc.status_code == 429
    else:
        raise AssertionError("Expected the second IP to hit its own limit after its third request.")


def test_ip_is_taken_from_x_forwarded_for_header() -> None:
    request = DummyRequest(headers={"x-forwarded-for": "203.0.113.10, 10.0.0.2"})
    assert get_client_ip(request) == "203.0.113.10"


def test_environment_overrides_are_used() -> None:
    reset_limiters()
    import os

    os.environ["EXPLANATION_RATE_LIMIT"] = "2"
    os.environ["EXPLANATION_RATE_WINDOW_SECONDS"] = "60"
    try:
        request = DummyRequest(headers={"x-forwarded-for": "10.0.0.9"})
        enforce_explanation_rate_limit(request)
        enforce_explanation_rate_limit(request)
        try:
            enforce_explanation_rate_limit(request)
        except HTTPException as exc:
            assert exc.status_code == 429
        else:
            raise AssertionError("Expected environment override to trigger a 429 on the third request.")
    finally:
        os.environ.pop("EXPLANATION_RATE_LIMIT", None)
        os.environ.pop("EXPLANATION_RATE_WINDOW_SECONDS", None)
        reset_limiters()


def test_default_values_are_used_when_env_missing() -> None:
    assert DEFAULT_EXPLANATION_RATE_LIMIT == 3
    assert DEFAULT_EXPLANATION_RATE_WINDOW_SECONDS == 3600
