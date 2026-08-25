"""The MCP server: 9 tools, no more. See §9 of paperloom.md. The server is
dumb — it exposes file-manipulation primitives; it never synthesizes or
summarizes. All intelligence lives in the host agent, driven by the vault's
CLAUDE.md."""

from __future__ import annotations

import fnmatch
from datetime import datetime
from pathlib import Path

import yaml
from fastmcp import FastMCP
from pydantic import BaseModel

from paperloom import ingest as ingest_mod
from paperloom import search as search_mod
from paperloom import vault as vault_mod
from paperloom.plugins import load_all
from paperloom.vault import find_vault_root

mcp = FastMCP("paperloom")


class SearchHit(BaseModel):
    path: str
    line: int
    snippet: str
    score: float


class PageInfo(BaseModel):
    path: str
    type: str | None = None
    tags: list[str] = []
    title: str | None = None


class WriteResult(BaseModel):
    status: str  # "created" | "appended" | "refused" | "tagged" | "logged"
    path: str
    message: str | None = None


class IngestPdfResult(BaseModel):
    id: str
    raw_path: str
    n_pages: int | None = None
    status: str
    message: str | None = None


class VaultInfo(BaseModel):
    root: str
    config: dict
    n_raw: int
    n_research: int
    n_logs: int
    plugins_loaded: list[str] = []


@mcp.tool
def search(query: str, top_k: int = 10, path_prefix: str | None = None) -> list[SearchHit]:
    """Full-text search across the vault. Returns paths + snippet + line number."""
    root = find_vault_root()
    hits = search_mod.hybrid_search(root, query, top_k=top_k, path_prefix=path_prefix)
    return [SearchHit(path=h.path, line=h.line, snippet=h.snippet, score=h.score) for h in hits]


@mcp.tool
def read_page(path: str) -> str:
    """Read a markdown file relative to the vault root. Full contents,
    including frontmatter."""
    root = find_vault_root()
    resolved = vault_mod.resolve_path(root, path)
    if not resolved.is_file():
        raise FileNotFoundError(f"No such file in vault: {path!r}")
    return resolved.read_text(encoding="utf-8")


@mcp.tool
def list_pages(subdir: str = "sources/research", pattern: str = "*.md") -> list[PageInfo]:
    """List files under `subdir` with basic frontmatter (type, tags, title).
    Fast — reads frontmatter only, not full page bodies."""
    root = find_vault_root()
    base = vault_mod.resolve_path(root, subdir)
    if not base.is_dir():
        return []

    pages = []
    for p in sorted(base.rglob("*")):
        if not p.is_file() or not fnmatch.fnmatch(p.name, pattern):
            continue
        frontmatter, _ = vault_mod.read_frontmatter(p)
        pages.append(
            PageInfo(
                path=p.relative_to(root).as_posix(),
                type=frontmatter.get("type"),
                tags=frontmatter.get("tags") or [],
                title=frontmatter.get("title"),
            )
        )
    return pages


@mcp.tool
def create_note(
    path: str,
    title: str,
    content: str,
    tags: list[str] | None = None,
    frontmatter: dict | None = None,
) -> WriteResult:
    """Create a new markdown file with YAML frontmatter. Fails if the path
    already exists (use append_to_page to modify). Refuses to write outside
    sources/, artifacts/, or logs/."""
    root = find_vault_root()
    vault_mod.check_writable(path)
    resolved = vault_mod.resolve_path(root, path)
    if resolved.exists():
        raise FileExistsError(f"{path!r} already exists — use append_to_page to modify it")

    fm = dict(frontmatter or {})
    fm.setdefault("title", title)
    if tags:
        fm.setdefault("tags", tags)

    vault_mod.write_frontmatter(resolved, fm, content)
    return WriteResult(status="created", path=path)


@mcp.tool
def append_to_page(
    path: str,
    content: str,
    section: str | None = None,
    guard: str = "auto",
) -> WriteResult:
    """Append content to an existing page. If `section` is given, append
    under that H2/H3 header (creating it at the end of the page if it
    doesn't already exist). `guard`: "auto" refuses when the page's
    frontmatter has human_edited: true; "force" appends regardless;
    "human-safe" wraps the appended text in <!-- agent-added --> sentinels."""
    root = find_vault_root()
    vault_mod.check_writable(path)
    resolved = vault_mod.resolve_path(root, path)
    if not resolved.is_file():
        raise FileNotFoundError(f"No such page: {path!r} — use create_note to make it first")

    frontmatter, body = vault_mod.read_frontmatter(resolved)

    if guard not in ("auto", "force", "human-safe"):
        raise ValueError(f"guard must be one of auto/force/human-safe, got {guard!r}")

    if guard == "auto" and frontmatter.get("human_edited"):
        return WriteResult(
            status="refused",
            path=path,
            message="page has human_edited: true — pass guard='force' to override",
        )

    text_to_add = content
    if guard == "human-safe":
        text_to_add = f"<!-- agent-added -->\n{content}\n<!-- /agent-added -->"

    if section is None:
        new_body = body.rstrip("\n") + "\n\n" + text_to_add + "\n"
    else:
        new_body = _insert_under_section(body, section, text_to_add)

    vault_mod.write_frontmatter(resolved, frontmatter, new_body)
    return WriteResult(status="appended", path=path)


def _insert_under_section(body: str, section: str, text: str) -> str:
    """Insert `text` at the end of the named H2/H3 section, or append a new
    `## section` at the end of the page if it isn't found."""
    lines = body.splitlines(keepends=True)
    header_re_2 = f"## {section}"
    header_re_3 = f"### {section}"
    start = None
    start_depth = None
    for i, line in enumerate(lines):
        stripped = line.rstrip("\n")
        if stripped == header_re_2:
            start, start_depth = i, 2
            break
        if stripped == header_re_3:
            start, start_depth = i, 3
            break

    if start is None:
        new_section = f"\n## {section}\n\n{text}\n"
        return body.rstrip("\n") + "\n" + new_section
    assert start_depth is not None  # always set alongside `start`

    end = len(lines)
    for j in range(start + 1, len(lines)):
        stripped = lines[j].rstrip("\n")
        if stripped.startswith("#"):
            depth = len(stripped) - len(stripped.lstrip("#"))
            if depth <= start_depth:
                end = j
                break

    insertion = lines[:end]
    tail = lines[end:]
    insertion.append("\n" + text + "\n")
    return "".join(insertion) + "".join(tail)


@mcp.tool
def tag_note(path: str, tags: list[str], mode: str = "merge") -> WriteResult:
    """Add tags to a page's frontmatter. mode: "merge" (default) or "replace"."""
    root = find_vault_root()
    vault_mod.check_writable(path)
    resolved = vault_mod.resolve_path(root, path)
    if not resolved.is_file():
        raise FileNotFoundError(f"No such page: {path!r}")
    if mode not in ("merge", "replace"):
        raise ValueError(f"mode must be 'merge' or 'replace', got {mode!r}")

    frontmatter, body = vault_mod.read_frontmatter(resolved)
    if mode == "replace":
        frontmatter["tags"] = list(tags)
    else:
        existing = frontmatter.get("tags") or []
        frontmatter["tags"] = sorted(set(existing) | set(tags))

    vault_mod.write_frontmatter(resolved, frontmatter, body)
    return WriteResult(status="tagged", path=path)


@mcp.tool
def log_entry(kind: str, text: str, contributor: str | None = None) -> WriteResult:
    """Append a line to today's log (logs/YYYY-MM-DD.md), or a contributor's
    daily file (sources/contributors/<contributor>/YYYY-MM-DD.md) if given.
    Format: "- HH:MM [KIND] text". Creates the file if missing."""
    root = find_vault_root()
    today = datetime.now()
    line = f"- {today.strftime('%H:%M')} [{kind}] {text}"

    if contributor:
        rel = f"sources/contributors/{contributor}/{today.date().isoformat()}.md"
    else:
        rel = f"logs/{today.date().isoformat()}.md"

    log_path = vault_mod.resolve_path(root, rel)  # guards against a malicious/odd contributor name
    vault_mod.append_log_line(log_path, line)
    return WriteResult(status="logged", path=rel)


@mcp.tool
def ingest_pdf(pdf_path: str, id_hint: str | None = None) -> IngestPdfResult:
    """Ingest a single PDF into sources/raw/. Same pipeline as `paperloom
    ingest`, callable from the agent. Supervised MinerU subprocess."""
    root = find_vault_root()
    result = ingest_mod.ingest_one(Path(pdf_path), root, id_override=id_hint)
    raw_path = f"sources/raw/{result.id}/paper.md"
    return IngestPdfResult(
        id=result.id,
        raw_path=raw_path,
        n_pages=result.n_pages,
        status=result.status,
        message=result.message,
    )


@mcp.tool
def vault_info() -> VaultInfo:
    """Root, config, and file counts for the current vault — useful as the
    agent's first read of a session."""
    root = find_vault_root()
    config_path = root / ".paperloom" / "config.yaml"
    config = yaml.safe_load(config_path.read_text()) if config_path.exists() else {}

    raw_dir = root / "sources" / "raw"
    n_raw = len([p for p in raw_dir.iterdir() if p.is_dir()]) if raw_dir.is_dir() else 0

    research_dir = root / "sources" / "research"
    n_research = len(list(research_dir.rglob("*.md"))) if research_dir.is_dir() else 0

    logs_dir = root / "logs"
    n_logs = len(list(logs_dir.glob("*.md"))) if logs_dir.is_dir() else 0

    return VaultInfo(
        root=str(root),
        config=config or {},
        n_raw=n_raw,
        n_research=n_research,
        n_logs=n_logs,
        plugins_loaded=_loaded_plugins,
    )


# Plugin loading (§10). Runs once, at import time — the CLI's `mcp` command
# imports this module only once cwd is already set to the vault, so
# find_vault_root() inside load_all()'s vault-local step resolves correctly
# for real usage.
_loaded_plugins: list[str] = load_all(mcp)


if __name__ == "__main__":
    mcp.run()  # stdio by default
