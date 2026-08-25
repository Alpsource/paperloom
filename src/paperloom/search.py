"""Vault search: a ripgrep wrapper. See §17 item 5 of paperloom.md — SQLite
FTS5 is a possible follow-up if ripgrep turns out to be limiting, not
attempted here. Backs both the `search` MCP tool (§9) and `paperloom
search` (§5)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from paperloom.supervisor import spawn

RG_BIN = "rg"


class RipgrepNotFoundError(Exception):
    def __init__(self):
        super().__init__(
            "ripgrep (`rg`) not found on PATH. Install it — "
            "https://github.com/BurntSushi/ripgrep#installation — "
            "paperloom's search relies on it."
        )


@dataclass
class SearchHit:
    path: str
    line: int
    snippet: str
    score: float


def hybrid_search(
    vault_root: Path,
    query: str,
    top_k: int = 10,
    path_prefix: str | None = None,
) -> list[SearchHit]:
    """Full-text search across the vault. Empty/whitespace query returns []
    without invoking ripgrep (an empty pattern would otherwise match every
    line — the opposite of a graceful empty result)."""
    if not query or not query.strip():
        return []

    vault_root = Path(vault_root)
    search_root = vault_root / path_prefix if path_prefix else vault_root

    try:
        proc = spawn(
            [RG_BIN, "--json", "--fixed-strings", "--", query, str(search_root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        raise RipgrepNotFoundError() from None

    stdout, _ = proc.communicate()

    # rg exits 1 (not an error) when the path exists but has zero matches,
    # and 2 on a real error (e.g. search_root doesn't exist).
    if proc.returncode not in (0, 1):
        return []

    matches: dict[str, list[tuple[int, str]]] = {}
    for line in stdout.splitlines():
        if not line:
            continue
        event = json.loads(line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        path = Path(data["path"]["text"]).relative_to(vault_root).as_posix()
        line_number = data["line_number"]
        snippet = data["lines"]["text"].strip()
        matches.setdefault(path, []).append((line_number, snippet))

    hits = [
        SearchHit(path=path, line=line_number, snippet=snippet, score=float(len(lines)))
        for path, lines in matches.items()
        for line_number, snippet in lines
    ]
    hits.sort(key=lambda h: (-h.score, h.path, h.line))
    return hits[:top_k]
