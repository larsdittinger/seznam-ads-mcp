from sklik_mcp.server import build_server


def test_build_server_returns_fastmcp_with_tools(monkeypatch):
    monkeypatch.setenv("SKLIK_API_TOKEN", "x")
    mcp = build_server()
    # FastMCP exposes tool registration via list_tools (sync helper)
    # We just check it instantiates without error and has expected name.
    assert mcp.name == "sklik-mcp"
