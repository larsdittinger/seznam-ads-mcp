"""Integration smoke test against a real Sklik account.

Skipped unless SKLIK_API_TOKEN_TEST is set. Run manually:
    SKLIK_API_TOKEN_TEST=xxx uv run pytest -m integration -v
"""

from __future__ import annotations

import os

import pytest

from sklik_mcp.core.client import SklikClient


@pytest.fixture(scope="module")
def real_client() -> SklikClient:
    token = os.environ.get("SKLIK_API_TOKEN_TEST")
    if not token:
        pytest.skip("SKLIK_API_TOKEN_TEST not set")
    return SklikClient(token=token)


@pytest.mark.integration
def test_login_against_real_api(real_client: SklikClient) -> None:
    real_client.login()
    assert real_client.session.is_authenticated


@pytest.mark.integration
def test_list_campaigns_against_real_api(real_client: SklikClient) -> None:
    real_client.login()
    # Sklik requires both limit AND offset in displayOptions
    resp = real_client.call("campaigns.list", {}, {"limit": 5, "offset": 0})
    assert resp["status"] == 200
    assert "campaigns" in resp


@pytest.mark.integration
def test_account_overview_against_real_api(real_client: SklikClient) -> None:
    """Account-level overview is the only synchronous stats endpoint.

    Per-entity stats use Sklik's async report-query model and aren't
    implemented yet (tracked for v0.2).
    """
    real_client.login()
    resp = real_client.call(
        "client.stats",
        {"dateFrom": "2026-04-01", "dateTo": "2026-04-30", "granularity": "total"},
    )
    assert resp["status"] == 200
    assert "report" in resp
