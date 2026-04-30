"""Sklik API error hierarchy and HTTP status mapping."""

from __future__ import annotations

from typing import Any


class SklikError(Exception):
    """Base class for all Sklik API errors."""

    def __init__(self, message: str, *, status: int | None = None, details: Any = None):
        super().__init__(message)
        self.status = status
        self.details = details


class ArgumentError(SklikError):
    """400 — request arguments invalid."""


class SessionError(SklikError):
    """401 — session expired or invalid."""


class AccessError(SklikError):
    """403 — access denied."""


class NotFoundError(SklikError):
    """404 — resource not found."""


class InvalidDataError(SklikError):
    """406 — data invalid for the requested operation."""


_STATUS_MAP: dict[int, type[SklikError]] = {
    400: ArgumentError,
    401: SessionError,
    403: AccessError,
    404: NotFoundError,
    406: InvalidDataError,
}


def error_for_status(status: int, message: str, details: Any) -> SklikError | None:
    """Return an exception instance for non-success Sklik statuses, else None.

    2xx (including 206 partial-success) returns None. 409 no-action returns None
    too; the caller can surface it as a warning.
    """
    if 200 <= status < 300 or status == 409:
        return None
    cls = _STATUS_MAP.get(status, SklikError)
    return cls(message, status=status, details=details)
