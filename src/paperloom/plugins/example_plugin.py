"""Example plugin: exposes `word_count` and `find_orphans` tools. Reference
implementation for docs — see §10 of paperloom.md."""

from paperloom.vault import find_vault_root


def register(mcp):
    @mcp.tool
    def word_count(path: str) -> int:
        """Count words in a vault file."""
        text = (find_vault_root() / path).read_text()
        return len(text.split())

    @mcp.tool
    def find_orphans(subdir: str = "sources/research") -> list[str]:
        """List pages with zero inbound [[wikilinks]] from anywhere in the vault."""
        root = find_vault_root()
        pages = list((root / subdir).glob("**/*.md"))
        all_text = "\n".join(p.read_text() for p in root.glob("**/*.md"))
        orphans = []
        for p in pages:
            stem = p.stem
            # crude but effective: does anything link to [[stem]] or [[stem|...]]?
            if f"[[{stem}]]" not in all_text and f"[[{stem}|" not in all_text:
                orphans.append(str(p.relative_to(root)))
        return orphans
