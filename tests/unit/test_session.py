from sklik_mcp.core.session import SessionState


def test_session_starts_empty():
    s = SessionState()
    assert s.session_token is None
    assert s.active_user_id is None
    assert s.token_owner_user_id is None
    assert s.is_authenticated is False


def test_session_authenticated_after_token_set():
    s = SessionState()
    s.session_token = "abc"
    assert s.is_authenticated is True


def test_auth_struct_minimum():
    s = SessionState(session_token="abc")
    assert s.auth_struct() == {"session": "abc"}


def test_auth_struct_with_impersonation():
    s = SessionState(session_token="abc", active_user_id=42)
    assert s.auth_struct() == {"session": "abc", "userId": 42}


def test_auth_struct_raises_when_unauthenticated():
    s = SessionState()
    try:
        s.auth_struct()
    except RuntimeError as e:
        assert "not authenticated" in str(e).lower()
    else:
        raise AssertionError("expected RuntimeError")


def test_clear_resets_state():
    s = SessionState(session_token="abc", active_user_id=42, token_owner_user_id=7)
    s.clear()
    assert s.session_token is None
    assert s.active_user_id is None
    # token_owner_user_id is preserved across re-login
    assert s.token_owner_user_id == 7
