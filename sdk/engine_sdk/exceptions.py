"""Engine SDK exceptions.

Hierarchy:
    EngineError
    +-- ConnectionError
    +-- AuthenticationError
    +-- NotFoundError
    +-- ValidationError
    +-- ServerError
    +-- TimeoutError
"""

from __future__ import annotations


class EngineError(Exception):
    """Base exception for all Engine SDK errors.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code from the server (if applicable).
        body: Raw response body (if applicable).
    """

    def __init__(
        self,
        message: str = "An error occurred",
        *,
        status_code: int | None = None,
        body: dict | str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.body = body

    def __repr__(self) -> str:
        cls = type(self).__name__
        parts = [repr(self.message)]
        if self.status_code is not None:
            parts.append(f"status_code={self.status_code}")
        return f"{cls}({', '.join(parts)})"


class ConnectionError(EngineError):
    """Raised when the SDK cannot reach the Engine Service."""


class AuthenticationError(EngineError):
    """Raised when the API key is missing or invalid (HTTP 401/403)."""


class NotFoundError(EngineError):
    """Raised when a requested resource does not exist (HTTP 404)."""


class ValidationError(EngineError):
    """Raised when the request payload is invalid (HTTP 422)."""


class ServerError(EngineError):
    """Raised when the server returns a 5xx error."""


class TimeoutError(EngineError):
    """Raised when a request exceeds the configured timeout."""
