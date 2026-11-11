"""Security middleware, HTTP headers hardening, and request rate limiting."""

import time
from collections import defaultdict
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings, get_settings


def _resolve_settings(request: Request) -> Settings:
    """Resolve settings respecting FastAPI dependency overrides if present."""
    if (
        hasattr(request.app, "dependency_overrides")
        and get_settings in request.app.dependency_overrides
    ):
        return request.app.dependency_overrides[get_settings]()
    return get_settings()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware enforcing standard defensive HTTP response security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response: Response = await call_next(request)
        settings = _resolve_settings(request)

        if settings.security_headers_enabled:
            headers = response.headers
            headers.setdefault("X-Content-Type-Options", "nosniff")
            headers.setdefault("X-Frame-Options", "DENY")
            headers.setdefault("X-XSS-Protection", "1; mode=block")
            headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

            # HSTS header for secure transports or production environments
            is_https = (
                request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
            )
            if is_https or settings.app_env == "production":
                headers.setdefault(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains; preload",
                )

        return response


class RateLimiter:
    """In-memory sliding-window request rate limiter indexed by client IP."""

    def __init__(self) -> None:
        # Map: client_ip -> list of epoch timestamps
        self._records: dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(
        self, client_ip: str, limit: int, window_seconds: int = 60
    ) -> tuple[bool, int, int]:
        """Evaluate if client IP is within rate limit.

        Returns:
            tuple[bool, int, int]: (allowed, remaining, retry_after)
        """
        now = time.time()
        cutoff = now - window_seconds

        # Prune expired timestamps
        self._records[client_ip] = [ts for ts in self._records[client_ip] if ts > cutoff]
        history = self._records[client_ip]

        if len(history) >= limit:
            oldest_relevant = history[0]
            retry_after = max(1, int(oldest_relevant + window_seconds - now))
            return False, 0, retry_after

        # Record this request
        history.append(now)
        remaining = max(0, limit - len(history))
        return True, remaining, 0

    def clear(self) -> None:
        """Reset all rate limiter records (useful for test isolation)."""
        self._records.clear()


# Global rate limiter instance
limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware evaluating request rates and applying sliding-window limits."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = _resolve_settings(request)

        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Extract client IP (respecting forward headers from reverse proxies)
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = (
            forwarded.split(",")[0].strip()
            if forwarded
            else (request.client.host if request.client else "127.0.0.1")
        )

        # Apply specific rate limits depending on endpoint sensitivity
        path = request.url.path
        if path.endswith("/download"):
            limit = settings.download_rate_limit_per_minute
        else:
            limit = settings.rate_limit_per_minute

        allowed, remaining, retry_after = limiter.check_rate_limit(
            client_ip=client_ip, limit=limit, window_seconds=60
        )

        if not allowed:
            reset_epoch = int(time.time() + retry_after)
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again later.",
                        "details": {"retry_after_seconds": retry_after},
                    }
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_epoch),
                },
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
