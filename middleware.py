"""Tests for API gateway middleware: rate limiting, authentication, and request validation."""

from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.rate_limiter import (
    RATE_LIMIT_RULES,
    _get_client_ip,
)
from app.middleware.authentication import (
    _is_public_path,
    _decode_token,
    PUBLIC_PATHS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jwt(payload: dict, secret: str = settings.JWT_SECRET, algorithm: str = settings.JWT_ALGORITHM) -> str:
    """Create a signed JWT for testing."""
    return jwt.encode(payload, secret, algorithm=algorithm)


# ---------------------------------------------------------------------------
# Rate Limiter Tests
# ---------------------------------------------------------------------------

class TestRateLimiterConfig:
    """Verify rate limit rules match the requirements."""

    def test_login_rate_limit_config(self):
        assert "/api/auth/login" in RATE_LIMIT_RULES
        max_req, window = RATE_LIMIT_RULES["/api/auth/login"]
        assert max_req == 10
        assert window == 60

    def test_otp_resend_rate_limit_config(self):
        assert "/api/auth/resend-otp" in RATE_LIMIT_RULES
        max_req, window = RATE_LIMIT_RULES["/api/auth/resend-otp"]
        assert max_req == 3
        assert window == 900  # 15 minutes

    def test_fraud_check_rate_limit_config(self):
        assert "/api/fraud/check-link" in RATE_LIMIT_RULES
        max_req, window = RATE_LIMIT_RULES["/api/fraud/check-link"]
        assert max_req == 30
        assert window == 60


class TestRateLimiterMiddleware:
    """Test rate limiting enforcement via Redis."""

    @patch("app.middleware.authentication.cache_get", return_value=None)
    @patch("app.middleware.rate_limiter.redis_client")
    def test_allows_requests_under_limit(self, mock_redis, mock_cache_get):
        mock_redis.incr.return_value = 1
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        token = _make_jwt({"sub": "user1", "exp": datetime.now(timezone.utc) + timedelta(hours=1)})
        resp = client.post("/api/fraud/check-link", headers={"Authorization": f"Bearer {token}"})
        # 404 is expected since no actual route handler exists for this in main app,
        # but the point is it wasn't blocked by rate limiter (not 429)
        assert resp.status_code != 429

    @patch("app.middleware.authentication.cache_get", return_value=None)
    @patch("app.middleware.rate_limiter.redis_client")
    def test_blocks_requests_over_login_limit(self, mock_redis, mock_cache_get):
        mock_redis.incr.return_value = 11  # Over the 10-request login limit
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post("/api/auth/login")
        assert resp.status_code == 429

    @patch("app.middleware.authentication.cache_get", return_value=None)
    @patch("app.middleware.rate_limiter.redis_client")
    def test_sets_expiry_on_first_request(self, mock_redis, mock_cache_get):
        mock_redis.incr.return_value = 1
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        client.post("/api/auth/login")
        mock_redis.expire.assert_called_once()

    @patch("app.middleware.authentication.cache_get", return_value=None)
    @patch("app.middleware.rate_limiter.redis_client")
    def test_does_not_reset_expiry_on_subsequent_requests(self, mock_redis, mock_cache_get):
        mock_redis.incr.return_value = 5  # Not the first request
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        client.post("/api/auth/login")
        mock_redis.expire.assert_not_called()

    @patch("app.middleware.rate_limiter.redis_client")
    def test_non_rate_limited_path_passes_through(self, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/health")
        assert resp.status_code == 200
        mock_redis.incr.assert_not_called()


class TestGetClientIp:
    """Test IP extraction from requests."""

    def test_extracts_from_x_forwarded_for(self):
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"x-forwarded-for": "1.2.3.4, 5.6.7.8"}
        assert _get_client_ip(mock_request) == "1.2.3.4"

    def test_falls_back_to_client_host(self):
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client.host = "10.0.0.1"
        assert _get_client_ip(mock_request) == "10.0.0.1"

    def test_returns_unknown_when_no_client(self):
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}
        mock_request.client = None
        assert _get_client_ip(mock_request) == "unknown"


# ---------------------------------------------------------------------------
# Authentication Middleware Tests
# ---------------------------------------------------------------------------

class TestPublicPaths:
    """Verify public path configuration."""

    @pytest.mark.parametrize("path", [
        "/health",
        "/api/auth/register",
        "/api/auth/login",
        "/api/auth/verify-otp",
        "/api/auth/verify-login-otp",
        "/api/auth/verify-biometric",
        "/api/auth/register-biometric",
        "/api/auth/resend-otp",
        "/api/auth/refresh",
        "/api/webhooks/phonepe",
        "/docs",
        "/redoc",
        "/openapi.json",
    ])
    def test_public_paths_are_configured(self, path):
        assert _is_public_path(path)

    @pytest.mark.parametrize("path", [
        "/api/dashboard/summary",
        "/api/transactions",
        "/api/notifications",
        "/api/fraud/check-link",
    ])
    def test_protected_paths_are_not_public(self, path):
        assert not _is_public_path(path)

    def test_docs_subpaths_are_public(self):
        assert _is_public_path("/docs/oauth2-redirect")
        assert _is_public_path("/redoc/")


class TestAuthMiddleware:
    """Test JWT authentication middleware."""

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_public_path_no_auth_required(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_protected_path_requires_auth(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_expired_token_returns_401(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        token = _make_jwt({
            "sub": "user-123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        })
        resp = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_invalid_token_returns_401(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": "Bearer not-a-valid-token"},
        )
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_missing_auth_header_returns_401(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_malformed_auth_header_returns_401(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get")
    def test_blacklisted_token_returns_401(self, mock_cache_get, mock_redis):
        """A token in the blacklist (e.g. after logout) should be rejected."""
        mock_cache_get.return_value = "1"  # Token is blacklisted

        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        token = _make_jwt({
            "sub": "user-123",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        })
        resp = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_wrong_secret_token_returns_401(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        token = _make_jwt(
            {"sub": "user-123", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            secret="wrong-secret",
        )
        resp = client.get(
            "/api/dashboard/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_webhook_path_is_public(self, mock_cache_get, mock_redis):
        from app.main import app
        client = TestClient(app, raise_server_exceptions=False)

        resp = client.post("/api/webhooks/phonepe")
        # The webhook endpoint is public (auth middleware doesn't block it).
        # The handler itself may return 401 for invalid webhook signatures,
        # but that's the handler's own signature check — not the auth middleware.
        # We verify the auth middleware didn't block it by checking the error
        # message is NOT the auth middleware's "Missing or invalid authorization header."
        if resp.status_code == 401:
            body = resp.json()
            assert body.get("detail") != "Missing or invalid authorization header."


# ---------------------------------------------------------------------------
# Request Validation Middleware Tests
# ---------------------------------------------------------------------------

class TestRequestValidation:
    """Test Pydantic request validation error handling via the main app."""

    @patch("app.middleware.rate_limiter.redis_client")
    @patch("app.middleware.authentication.cache_get", return_value=None)
    def test_validation_error_returns_422_with_structured_errors(self, mock_cache_get, mock_redis):
        """FastAPI + Pydantic validation errors should return structured 422 responses."""
        from app.main import app

        # Add a temporary test route that requires a Pydantic body
        class TestBody(BaseModel):
            name: str = Field(..., min_length=1)
            age: int = Field(..., gt=0)

        # Use a unique path to avoid conflicts
        @app.post("/test-validation-endpoint")
        async def test_route(body: TestBody):
            return {"name": body.name}

        client = TestClient(app, raise_server_exceptions=False)
        token = _make_jwt({
            "sub": "user-test",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        })
        resp = client.post(
            "/test-validation-endpoint",
            json={"name": "", "age": -1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["detail"] == "Validation error"
        assert "errors" in body
        assert len(body["errors"]) > 0
        # Each error should have field, message, type
        for error in body["errors"]:
            assert "field" in error
            assert "message" in error
            assert "type" in error


# ---------------------------------------------------------------------------
# Token Decode Unit Tests
# ---------------------------------------------------------------------------

class TestDecodeToken:
    """Unit tests for the _decode_token helper."""

    def test_decodes_valid_token(self):
        token = _make_jwt({
            "sub": "user-abc",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        })
        payload = _decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-abc"

    def test_returns_none_on_expired_token(self):
        token = _make_jwt({
            "sub": "user-abc",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        })
        result = _decode_token(token)
        assert result is None

    def test_returns_none_on_invalid_token(self):
        result = _decode_token("garbage.token.value")
        assert result is None

    def test_returns_none_on_wrong_algorithm(self):
        # Encode with HS384 but middleware expects HS256
        token = jwt.encode(
            {"sub": "user-abc", "exp": datetime.now(timezone.utc) + timedelta(minutes=15)},
            settings.JWT_SECRET,
            algorithm="HS384",
        )
        result = _decode_token(token)
        assert result is None
