import pytest
from pydantic import ValidationError

from sklik_mcp.core.config import Settings


def test_settings_loads_from_env(monkeypatch):
    monkeypatch.setenv("SKLIK_API_TOKEN", "abc-123")
    s = Settings()
    assert s.api_token == "abc-123"
    assert s.endpoint == "https://api.sklik.cz/drak/json/v5"
    assert s.fenix_endpoint == "https://api.sklik.cz/fenix/v1"
    assert s.request_timeout_s == 30


def test_settings_requires_token(monkeypatch):
    monkeypatch.delenv("SKLIK_API_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_overrides(monkeypatch):
    monkeypatch.setenv("SKLIK_API_TOKEN", "x")
    monkeypatch.setenv("SKLIK_REQUEST_TIMEOUT_S", "60")
    s = Settings()
    assert s.request_timeout_s == 60
