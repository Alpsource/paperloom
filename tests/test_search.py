from pathlib import Path

from paperloom.search import hybrid_search


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _make_vault(root: Path) -> Path:
    (root / ".paperloom").mkdir()
    _write(
        root,
        "sources/research/i-jepa.md",
        "---\ntype: paper\n---\n\nI-JEPA predicts representations of target blocks.\n",
    )
    _write(
        root,
        "sources/research/methods/vit.md",
        "---\ntype: method\n---\n\nVision Transformer (ViT) is the backbone used by I-JEPA.\n",
    )
    _write(
        root,
        "sources/contributors/alp/2026-08-24.md",
        "- Read about ViT patches today, unrelated to any paper page.\n",
    )
    return root


def test_search_finds_relevant_hit(tmp_path):
    vault = _make_vault(tmp_path)
    hits = hybrid_search(vault, "I-JEPA")

    assert hits, "expected at least one hit"
    paths = {h.path for h in hits}
    assert "sources/research/i-jepa.md" in paths
    hit = next(h for h in hits if h.path == "sources/research/i-jepa.md")
    assert "I-JEPA" in hit.snippet
    assert hit.line > 0


def test_search_scopes_to_path_prefix(tmp_path):
    vault = _make_vault(tmp_path)

    # "ViT" appears in both sources/research/methods/vit.md and in the
    # contributors daily note — scoping to methods/ must exclude the latter.
    hits = hybrid_search(vault, "ViT", path_prefix="sources/research/methods")

    assert hits
    assert all(h.path.startswith("sources/research/methods") for h in hits)
    assert not any("contributors" in h.path for h in hits)


def test_search_empty_query_returns_empty_gracefully(tmp_path):
    vault = _make_vault(tmp_path)

    assert hybrid_search(vault, "") == []
    assert hybrid_search(vault, "   ") == []
    # Even scoped to a path that doesn't exist, an empty query still
    # short-circuits before ripgrep would ever see (and error on) that path.
    assert hybrid_search(vault, "", path_prefix="sources/does-not-exist") == []
