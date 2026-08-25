import asyncio
import logging

from fastmcp import FastMCP

from paperloom.plugins import load_all

# The exact logger FastMCP's local provider uses for duplicate-registration
# warnings — get_logger(__name__) in fastmcp/server/providers/local_provider/
# local_provider.py. It doesn't propagate to root (fastmcp sets
# propagate=False on itself), so caplog has to be pointed at it directly.
FASTMCP_LOCAL_PROVIDER_LOGGER = "fastmcp.server.providers.local_provider.local_provider"


def _make_vault_with_plugin(tmp_path, filename: str, source: str):
    plugins_dir = tmp_path / ".paperloom" / "plugins"
    plugins_dir.mkdir(parents=True)
    (plugins_dir / filename).write_text(source)
    (tmp_path / ".paperloom").mkdir(exist_ok=True)
    return tmp_path


def test_builtin_example_plugin_registers_successfully():
    mcp = FastMCP("t")
    loaded = load_all(mcp)

    assert "example_plugin" in loaded
    assert asyncio_get_tool(mcp, "word_count") is not None
    assert asyncio_get_tool(mcp, "find_orphans") is not None


def test_vault_local_plugin_is_loaded(tmp_path, monkeypatch):
    vault = _make_vault_with_plugin(
        tmp_path,
        "foo.py",
        "def register(mcp):\n"
        "    @mcp.tool\n"
        "    def hello_from_vault() -> str:\n"
        "        return 'hi'\n",
    )
    monkeypatch.chdir(vault)

    mcp = FastMCP("t")
    loaded = load_all(mcp)

    assert "vault:foo" in loaded
    assert asyncio_get_tool(mcp, "hello_from_vault") is not None


def test_plugin_with_syntax_error_does_not_crash(tmp_path, monkeypatch, capsys):
    vault = tmp_path
    plugins_dir = vault / ".paperloom" / "plugins"
    plugins_dir.mkdir(parents=True)
    (vault / ".paperloom").mkdir(exist_ok=True)
    (plugins_dir / "broken.py").write_text("def register(mcp:\n    this is not valid python\n")
    (plugins_dir / "good.py").write_text(
        "def register(mcp):\n    @mcp.tool\n    def still_works() -> str:\n        return 'ok'\n"
    )
    monkeypatch.chdir(vault)

    mcp = FastMCP("t")
    loaded = load_all(mcp)  # must not raise

    assert "vault:good" in loaded
    assert "vault:broken" not in loaded
    assert asyncio_get_tool(mcp, "still_works") is not None

    err = capsys.readouterr().err
    assert "broken" in err
    assert "failed to load" in err


def test_vault_local_plugin_overrides_builtin_with_warning(tmp_path, monkeypatch, caplog):
    vault = _make_vault_with_plugin(
        tmp_path,
        "override.py",
        "def register(mcp):\n"
        "    @mcp.tool\n"
        "    def word_count(path: str) -> int:\n"
        "        return -1\n",  # deliberately distinct from the built-in's real behavior
    )
    monkeypatch.chdir(vault)

    mcp = FastMCP("t")
    with caplog.at_level(logging.WARNING, logger=FASTMCP_LOCAL_PROVIDER_LOGGER):
        loaded = load_all(mcp)

    assert "example_plugin" in loaded  # built-in loaded first...
    assert "vault:override" in loaded  # ...then overridden by the vault-local one
    assert any("already exists" in r.message.lower() for r in caplog.records)

    result = asyncio_run_tool(mcp, "word_count", {"path": "whatever"})
    assert result == -1  # the vault-local override's behavior won, not the built-in's


# --- small sync-test helpers around fastmcp's async-only tool introspection ---


def asyncio_get_tool(mcp, name: str):
    return asyncio.run(mcp.get_tool(name))


def asyncio_run_tool(mcp, name: str, args: dict):
    async def _call():
        tool = await mcp.get_tool(name)
        result = await tool.run(args)
        return result.structured_content["result"]

    return asyncio.run(_call())
