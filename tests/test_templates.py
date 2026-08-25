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
