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
def test_login_body_is_json_array_with_token_struct(client):
    """Sklik's JSON endpoint expects every call's body to be a positional-args array.

    The login struct must be wrapped in a list, not sent bare.
    """
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "statusMessage": "OK", "session": "sess-xyz"},
    )
    client.login()
    import json as _json

    body = responses.calls[0].request.body
    payload = _json.loads(body)
    assert payload == [{"token": "test-token"}]


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


@responses.activate
def test_call_retries_once_on_401(client):
    # Login twice (initial + retry), real call returns 401 first then success
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-1"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-2"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 401, "statusMessage": "session expired"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 200, "campaigns": []},
    )
    out = client.call("campaigns.list", {})
    assert out["status"] == 200


@responses.activate
def test_call_does_not_retry_twice_on_401(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-1"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-2"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 401, "statusMessage": "session expired"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 401, "statusMessage": "still expired"},
    )
    with pytest.raises(SessionError):
        client.call("campaigns.list", {})


@responses.activate
def test_call_includes_impersonation_user_id(client):
    responses.post(
        "https://api.sklik.cz/drak/json/v5/client.loginByToken",
        json={"status": 200, "session": "sess-1"},
    )
    responses.post(
        "https://api.sklik.cz/drak/json/v5/campaigns.list",
        json={"status": 200, "campaigns": []},
    )
    client.set_active_account(99)
    client.call("campaigns.list", {})
    body = responses.calls[1].request.body
    import json as _json

    payload = _json.loads(body)
    assert payload[0] == {"session": "sess-1", "userId": 99}
