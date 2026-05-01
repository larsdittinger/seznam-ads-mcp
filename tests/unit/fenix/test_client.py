import time

import pytest
import responses

from sklik_mcp.tools.fenix.client import FenixClient


@pytest.fixture
def client():
    return FenixClient(refresh_token="REFRESH", endpoint="https://api.sklik.cz/v1")


def _stub_token_exchange(access: str = "ACCESS", expires_in: int = 3600) -> None:
    responses.post(
        "https://api.sklik.cz/v1/user/token",
        json={"access_token": access, "token_type": "Bearer", "expires_in": expires_in},
    )


@responses.activate
def test_get_exchanges_refresh_for_access_then_uses_bearer(client):
    _stub_token_exchange("ACCESS123")
    responses.get(
        "https://api.sklik.cz/v1/nakupy/shop-items/",
        json={"items": []},
    )

    out = client.get("/nakupy/shop-items/", premiseId=42)
    assert out == {"items": []}

    # First call exchanges the refresh token (with the refresh in the
    # Authorization header and grant_type in the form body).
    token_call = responses.calls[0].request
    assert token_call.url == "https://api.sklik.cz/v1/user/token"
    assert token_call.headers.get("Authorization") == "Bearer REFRESH"
    body = token_call.body
    body_text = body.decode() if isinstance(body, bytes) else body
    assert "grant_type=client_credentials" in body_text

    # Second call uses the freshly issued access token.
    resource_call = responses.calls[1].request
    assert resource_call.headers.get("Authorization") == "Bearer ACCESS123"
    # Optional query param survives.
    assert "premiseId=42" in resource_call.url


@responses.activate
def test_caches_access_token_across_calls(client):
    _stub_token_exchange("ACC", expires_in=3600)
    responses.get("https://api.sklik.cz/v1/user/me", json={"userId": 1})
    responses.get(
        "https://api.sklik.cz/v1/nakupy/campaigns/",
        json={"campaigns": []},
    )

    client.get("/user/me")
    client.get("/nakupy/campaigns/", premiseId=42)

    # Only one token exchange happened — the access token was cached.
    token_exchanges = [c for c in responses.calls if c.request.url.endswith("/user/token")]
    assert len(token_exchanges) == 1


@responses.activate
def test_drops_none_query_params(client):
    _stub_token_exchange()
    responses.get("https://api.sklik.cz/v1/nakupy/shop-items/", json={"items": []})

    client.get("/nakupy/shop-items/", premiseId=1, itemId=None, paired=None)

    resource_call = next(c for c in responses.calls if "shop-items" in c.request.url)
    # None-valued kwargs are stripped, only premiseId is sent.
    assert "itemId" not in resource_call.request.url
    assert "premiseId=1" in resource_call.request.url


@responses.activate
def test_re_exchanges_on_expiry(client):
    # First exchange: token expires immediately.
    _stub_token_exchange("OLD", expires_in=1)
    responses.get("https://api.sklik.cz/v1/user/me", json={"userId": 1})

    client.get("/user/me")
    # Force the cache to look stale.
    client._access_expires_at = time.time() - 1

    # Second exchange returns a different token.
    _stub_token_exchange("NEW")
    responses.get("https://api.sklik.cz/v1/user/me", json={"userId": 2})

    client.get("/user/me")
    token_exchanges = [c for c in responses.calls if c.request.url.endswith("/user/token")]
    assert len(token_exchanges) == 2
    # Final resource call uses the refreshed token.
    final = responses.calls[-1].request
    assert final.headers.get("Authorization") == "Bearer NEW"


@responses.activate
def test_raises_clear_error_when_token_exchange_fails(client):
    responses.post(
        "https://api.sklik.cz/v1/user/token",
        json={"detail": [{"msg": "Token is not valid.", "type": "unauthorized"}]},
        status=401,
    )

    from sklik_mcp.core.errors import SklikError

    with pytest.raises(SklikError) as excinfo:
        client.get("/user/me")
    assert "Token exchange failed" in str(excinfo.value)
