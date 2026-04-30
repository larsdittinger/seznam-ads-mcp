"""Sklik API error hierarchy and HTTP status mapping."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar


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


F = TypeVar("F", bound=Callable[..., Any])

_CZECH_HINTS: dict[type[SklikError], str] = {
    SessionError: "Sklik API session vypršela nebo je neplatná. Zkontrolujte SKLIK_API_TOKEN.",
    AccessError: (
        "Nemáte oprávnění k tomuto účtu nebo zdroji. "
        "Zkontrolujte aktivní účet (current_account) nebo oprávnění tokenu."
    ),
    NotFoundError: "Požadovaný objekt v Skliku neexistuje (možná smazán nebo špatné ID).",
    ArgumentError: "Argumenty volání jsou neplatné. Detaily v poli 'errors'.",
    InvalidDataError: "Data nejsou validní pro tuto operaci.",
}


def with_sklik_error_handling(func: F) -> F:
    """Decorator: catch SklikError, return error dict with Czech hint + raw details.

    MCP tools wrapped with this turn typed Sklik errors into a structured error
    response the LLM can reason about, instead of propagating opaque exceptions.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except SklikError as e:
            hint = _CZECH_HINTS.get(type(e), "Sklik API vrátil chybu.")
            return {
                "error": True,
                "error_type": type(e).__name__,
                "message": str(e),
                "status": e.status,
                "details": e.details,
                "hint_cs": hint,
            }

    return wrapper  # type: ignore[return-value]
