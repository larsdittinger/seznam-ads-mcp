import pytest

from sklik_mcp.core.errors import (
    AccessError,
    ArgumentError,
    InvalidDataError,
    NotFoundError,
    SessionError,
    SklikError,
    error_for_status,
)


def test_error_hierarchy():
    assert issubclass(ArgumentError, SklikError)
    assert issubclass(SessionError, SklikError)
    assert issubclass(AccessError, SklikError)
    assert issubclass(NotFoundError, SklikError)
    assert issubclass(InvalidDataError, SklikError)


@pytest.mark.parametrize(
    "status,expected",
    [
        (400, ArgumentError),
        (401, SessionError),
        (403, AccessError),
        (404, NotFoundError),
        (406, InvalidDataError),
        (500, SklikError),
    ],
)
def test_error_for_status_returns_correct_class(status, expected):
    err = error_for_status(status, "msg", details=None)
    assert isinstance(err, expected)
    assert "msg" in str(err)


def test_error_for_status_returns_none_for_2xx():
    assert error_for_status(200, "OK", None) is None
    assert error_for_status(206, "Partial", None) is None
