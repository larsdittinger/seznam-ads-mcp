import pytest
import responses

from sklik_mcp.core.client import SklikClient
from sklik_mcp.core.errors import ArgumentError, SessionError


@pytest.fixture
def client():
    return SklikClient(token="test-token", endpoint="https://api.sklik.cz/drak/json/v5")


@responses.activate
def test_login_stores_session(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "statusMessage": "OK", "session": "sess-xyz"},
    )
    client.login()
    assert client.session.session_token == "sess-xyz"
    assert client.session.is_authenticated


@responses.activate
def test_login_failure_raises(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 401, "statusMessage": "Invalid token"},
    )
    with pytest.raises(SessionError):
        client.login()


@responses.activate
def test_call_lazy_logs_in(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-xyz"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 200, "campaigns": [{"id": 1}]},
    )
    result = client.call("campaigns.list", {})
    assert result == {"status": 200, "campaigns": [{"id": 1}]}
    assert client.session.is_authenticated


@responses.activate
def test_call_sends_auth_struct_first(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-xyz"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 200, "campaigns": []},
    )
    client.call("campaigns.list", {"name": "x"})
    assert len(responses.calls) == 2
    body = responses.calls[1].request.body
    import json as _json
    payload = _json.loads(body)
    # Sklik convention: first param is auth struct, rest follow
    assert payload[0] == {"session": "sess-xyz"}
    assert payload[1] == {"name": "x"}


@responses.activate
def test_call_400_raises_argument_error(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-xyz"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 400, "statusMessage": "Bad arg", "errors": ["x is required"]},
    )
    with pytest.raises(ArgumentError) as exc:
        client.call("campaigns.list", {})
    assert exc.value.details == ["x is required"]
