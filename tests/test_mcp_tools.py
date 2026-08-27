import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

import paperloom.ingest as ingest_mod
from paperloom.mcp_server import mcp

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_MINERU = FIXTURES / "fake_mineru.py"


@pytest.fixture
def vault(tmp_path, monkeypatch):
    (tmp_path / ".paperloom").mkdir()
    for d in ("sources/research", "sources/raw", "sources/contributors", "logs", "artifacts"):
        (tmp_path / d).mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


async def _call(name: str, **kwargs):
    async with Client(mcp) as client:
        return await client.call_tool(name, kwargs)


# ---------------------------------------------------------------- search ---


async def test_search_happy(vault):
    (vault / "sources/research/i-jepa.md").write_text(
        "---\ntype: paper\n---\n\nI-JEPA predicts target representations.\n"
    )
    result = await _call("search", query="I-JEPA")
    hits = result.data
    assert hits
    assert any(h.path == "sources/research/i-jepa.md" for h in hits)


async def test_search_error(vault, monkeypatch):
    monkeypatch.setattr("paperloom.search.RG_BIN", "definitely-not-a-real-ripgrep-binary")
    with pytest.raises(ToolError):
        await _call("search", query="anything")


# -------------------------------------------------------------- read_page ---


async def test_read_page_happy(vault):
    (vault / "sources/research/foo.md").write_text("---\ntype: paper\n---\n\nHello.\n")
    result = await _call("read_page", path="sources/research/foo.md")
    assert "Hello." in result.data


async def test_read_page_error(vault):
    with pytest.raises(ToolError):
        await _call("read_page", path="sources/research/does-not-exist.md")


# ------------------------------------------------------------- list_pages ---


async def test_list_pages_happy(vault):
    (vault / "sources/research/a.md").write_text(
        "---\ntype: paper\ntags: [ssl]\ntitle: Paper A\n---\n\nbody\n"
    )
    (vault / "sources/research/methods").mkdir()
    (vault / "sources/research/methods/b.md").write_text(
        "---\ntype: method\ntags: [vit]\ntitle: Method B\n---\n\nbody\n"
    )
    result = await _call("list_pages")
    pages = result.data
    paths = {p.path for p in pages}
    assert "sources/research/a.md" in paths
    assert "sources/research/methods/b.md" in paths
    a = next(p for p in pages if p.path == "sources/research/a.md")
    assert a.type == "paper"
    assert a.tags == ["ssl"]
    assert a.title == "Paper A"


async def test_list_pages_error(vault):
    with pytest.raises(ToolError):
        await _call("list_pages", subdir="../outside")


# ------------------------------------------------------------ create_note ---


async def test_create_note_happy(vault):
    result = await _call(
        "create_note",
        path="sources/research/new-page.md",
        title="New Page",
        content="Some content.",
        tags=["ssl"],
    )
    assert result.data.status == "created"
    written = (vault / "sources/research/new-page.md").read_text()
    assert "title: New Page" in written
    assert "Some content." in written


async def test_create_note_error(vault):
    (vault / "sources/research/exists.md").write_text("---\n---\nexisting\n")
    with pytest.raises(ToolError):
        await _call(
            "create_note",
            path="sources/research/exists.md",
            title="Dup",
            content="x",
        )


# -------------------------------------------------------- append_to_page ---


async def test_append_to_page_happy(vault):
    (vault / "sources/research/page.md").write_text(
        "---\ntype: paper\n---\n\n## Contributions\n\nFirst point.\n\n## Open questions\n\nNone yet.\n"
    )
    await _call("append_to_page", path="sources/research/page.md", content="Second point.")
    result = await _call(
        "append_to_page",
        path="sources/research/page.md",
        content="Third point.",
        section="Contributions",
    )
    assert result.data.status == "appended"
    text = (vault / "sources/research/page.md").read_text()
    assert "Second point." in text
    # Section-targeted content must land inside Contributions, before Open questions.
    contrib_idx = text.index("## Contributions")
    open_idx = text.index("## Open questions")
    third_idx = text.index("Third point.")
    assert contrib_idx < third_idx < open_idx


async def test_append_to_page_guard_refuses_human_edited(vault):
    (vault / "sources/research/locked.md").write_text(
        "---\ntype: paper\nhuman_edited: true\n---\n\nOriginal.\n"
    )
    result = await _call("append_to_page", path="sources/research/locked.md", content="New.")
    assert result.data.status == "refused"
    assert "New." not in (vault / "sources/research/locked.md").read_text()


async def test_append_to_page_error(vault):
    with pytest.raises(ToolError):
        await _call("append_to_page", path="sources/research/missing.md", content="x")


# -------------------------------------------------------------- tag_note ---


async def test_tag_note_happy(vault):
    (vault / "sources/research/page.md").write_text("---\ntype: paper\ntags: [ssl]\n---\n\nbody\n")
    result = await _call("tag_note", path="sources/research/page.md", tags=["jepa"])
    assert result.data.status == "tagged"
    text = (vault / "sources/research/page.md").read_text()
    assert "ssl" in text and "jepa" in text


async def test_tag_note_error(vault):
    with pytest.raises(ToolError):
        await _call("tag_note", path="sources/research/missing.md", tags=["x"])


# ------------------------------------------------------------- log_entry ---


async def test_log_entry_happy(vault):
    result = await _call("log_entry", kind="CONTRIBUTE", text="added a thought")
    assert result.data.status == "logged"
    logs = list((vault / "logs").glob("*.md"))
    assert len(logs) == 1
    assert "[CONTRIBUTE] added a thought" in logs[0].read_text()

    await _call("log_entry", kind="NOTE", text="daily thought", contributor="alp")
    contributor_files = list((vault / "sources/contributors/alp").glob("*.md"))
    assert len(contributor_files) == 1
    assert "[NOTE] daily thought" in contributor_files[0].read_text()


async def test_log_entry_error_rejects_path_traversal(vault):
    # "sources/contributors/<contributor>/..." is 2 levels deep, so it takes
    # 3 "../" to actually escape vault_root (2 would just cancel back to it).
    with pytest.raises(ToolError):
        await _call("log_entry", kind="X", text="y", contributor="../../../evil")


# ------------------------------------------------------------ ingest_pdf ---


async def test_ingest_pdf_happy(vault, monkeypatch):
    monkeypatch.setattr(ingest_mod, "DEFAULT_MINERU_CMD", [sys.executable, str(FAKE_MINERU)])
    result = await _call("ingest_pdf", pdf_path=str(FIXTURES / "toy-paper-arxiv.pdf"))
    assert result.data.status == "success"
    assert result.data.id == "2999.00001"
    assert (vault / "sources/raw/2999.00001/paper.md").exists()


async def test_ingest_pdf_error(vault):
    with pytest.raises(ToolError):
        await _call("ingest_pdf", pdf_path=str(FIXTURES / "does-not-exist.pdf"))


# ------------------------------------------------------------ vault_info ---


async def test_vault_info_happy(vault):
    (vault / "sources/raw/2301.08243").mkdir(parents=True)
    (vault / "sources/research/a.md").write_text("---\n---\nbody\n")
    (vault / ".paperloom/config.yaml").write_text("template: scientific-paper-vault\n")

    result = await _call("vault_info")
    info = result.data
    assert Path(info.root) == vault
    assert info.config["template"] == "scientific-paper-vault"
    assert info.n_raw == 1
    assert info.n_research == 1
    # §17 item 7 wires in real plugin loading — the built-in example_plugin
    # always loads (no vault-local plugins exist in this test's vault).
    assert info.plugins_loaded == ["example_plugin"]


async def test_vault_info_error_outside_any_vault(tmp_path, monkeypatch):
    outside = tmp_path / "not-a-vault"
    outside.mkdir()
    monkeypatch.chdir(outside)
    with pytest.raises(ToolError):
        await _call("vault_info")


# ------------------------------------------------------ describe_workflow ---


async def test_describe_workflow_happy(vault):
    result = await _call("describe_workflow", operation="ask")
    recipe = result.data
    assert "Step 1" in recipe
    assert "search" in recipe


async def test_describe_workflow_list_all(vault):
    result = await _call("describe_workflow", operation="list_all")
    names = result.data.splitlines()
    assert names == sorted(names)
    for expected in ("ask", "contribute", "ingest", "lint", "rebuild_context"):
        assert expected in names


async def test_describe_workflow_unknown_operation_returns_message_not_error(vault):
    # Deliberately doesn't raise — a weak local model mistyping the operation
    # name should get something it can read and recover from, not a crash.
    result = await _call("describe_workflow", operation="not-a-real-operation")
    assert "No recipe" in result.data
    assert "ask" in result.data  # lists what's actually available


async def test_describe_workflow_error_outside_any_vault(tmp_path, monkeypatch):
    outside = tmp_path / "not-a-vault"
    outside.mkdir()
    monkeypatch.chdir(outside)
    with pytest.raises(ToolError):
        await _call("describe_workflow", operation="ask")
