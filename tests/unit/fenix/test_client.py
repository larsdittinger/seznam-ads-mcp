import pytest
import responses

from sklik_mcp.tools.fenix.client import FenixClient


@pytest.fixture
def client():
    return FenixClient(token="t", endpoint="https://api.sklik.cz/fenix/v1")


@responses.activate
def test_get_sends_bearer_auth(client):
    responses.get(
        "https://api.sklik.cz/fenix/v1/productGroups",
        json={"items": []},
    )
    out = client.get("productGroups")
    assert out == {"items": []}
    auth = responses.calls[0].request.headers.get("Authorization")
    assert auth == "Bearer t"


@responses.activate
def test_post_sends_json(client):
    responses.post(
        "https://api.sklik.cz/fenix/v1/productGroups/123/bid",
        json={"updated": True},
    )
    out = client.post("productGroups/123/bid", {"maxCpc": 500})
    assert out["updated"] is True
