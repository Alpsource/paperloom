from typer.testing import CliRunner

from paperloom.cli import app

runner = CliRunner()


def test_claude_md_is_the_real_schema_not_the_placeholder(tmp_path):
    """§17 item 3 shipped a placeholder CLAUDE.md with a visible TODO marker;
    item 8 replaces it with §8's real schema verbatim. Guards against a
    future edit accidentally reverting to the placeholder."""
    vault = tmp_path / "vault"
    result = runner.invoke(app, ["init", str(vault)])
    assert result.exit_code == 0, result.output

    claude_md = (vault / "CLAUDE.md").read_text(encoding="utf-8")

    assert "TODO" not in claude_md
    assert "placeholder" not in claude_md.lower()

    # A few anchors that only exist in the real §8 schema.
    assert "/contribute" in claude_md
    assert "/ask" in claude_md
    assert "/lint" in claude_md
    assert "/rebuild-context" in claude_md
    assert "sources/raw/<paper-id>/" in claude_md
    assert "{{common-knowledge}}" in claude_md

    # paperloom_ollama_correction.md's mode-aware rewrite — guards against
    # a future edit dropping the operating-mode section or the local-model
    # accommodation (describe_workflow), which is the one concession
    # paperloom makes to weak local models per that correction.
    assert "Operating mode" in claude_md
    assert "mode: capable" in claude_md
    assert "mode: local" in claude_md
    assert "describe_workflow" in claude_md
    assert "[capable mode]" in claude_md
    assert "[local mode]" in claude_md


def test_workflows_dir_matches_what_describe_workflow_serves():
    """describe_workflow reads src/paperloom/workflows/<operation>.md.
    Guards the shipped recipe files and the tool's expected operation names
    from drifting apart (they're duplicated by design — see mcp_server.py's
    describe_workflow docstring and paperloom_ollama_correction.md)."""
    from paperloom.mcp_server import WORKFLOWS_DIR

    expected = {"contribute", "ask", "lint", "rebuild_context", "ingest"}
    actual = {f.stem for f in WORKFLOWS_DIR.glob("*.md")}
    assert actual == expected

    for name in expected:
        text = (WORKFLOWS_DIR / f"{name}.md").read_text(encoding="utf-8")
        assert "Step 1" in text or "usually run by the user" in text


def test_init_ships_real_slash_commands_for_the_four_operations(tmp_path):
    """/contribute, /ask, /lint, /rebuild-context are workflow names defined
    in CLAUDE.md, not built-in Claude Code commands — without a real
    .claude/commands/*.md per operation they silently don't autocomplete,
    which is exactly the confusion a real user hit. Guards against losing
    these on a future template edit."""
    vault = tmp_path / "vault"
    result = runner.invoke(app, ["init", str(vault)])
    assert result.exit_code == 0, result.output

    commands_dir = vault / ".claude" / "commands"
    for name in ("contribute", "ask", "lint", "rebuild-context"):
        path = commands_dir / f"{name}.md"
        assert path.is_file(), f"missing {path}"
        assert "description:" in path.read_text(encoding="utf-8")
