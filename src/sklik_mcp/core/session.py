"""Session state for Sklik client — holds session token + impersonation target."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionState:
    session_token: str | None = None
    active_user_id: int | None = None
    token_owner_user_id: int | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.session_token is not None

    def auth_struct(self) -> dict[str, object]:
        """Return the first-parameter struct that every Sklik call requires."""
        if self.session_token is None:
            raise RuntimeError("Sklik session not authenticated; call client.login() first")
        struct: dict[str, object] = {"session": self.session_token}
        if self.active_user_id is not None:
            struct["userId"] = self.active_user_id
        return struct

    def clear(self) -> None:
        """Clear the session token (keeps token_owner_user_id for re-login)."""
        self.session_token = None
        self.active_user_id = None
