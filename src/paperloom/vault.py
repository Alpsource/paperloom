"""Vault discovery, path resolution, and frontmatter I/O (§2's stated scope
for this module). Vault discovery walks up from the current directory until
it finds a `.paperloom/` marker — see §3."""

from pathlib import Path

import yaml


class VaultNotFoundError(Exception): ...


class PathOutsideVaultError(Exception): ...


class NotWritableError(Exception): ...


WRITABLE_PREFIXES = ("sources/", "artifacts/", "logs/")


def find_vault_root(start: Path | None = None, vault_dir: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) until a .paperloom/ dir is found.

    If `vault_dir` is given, it is used as an explicit override (the CLI's
    `--vault-dir` escape hatch): the walk is skipped entirely and `vault_dir`
    is returned as-is after confirming it contains a `.paperloom/` marker.
    """
    if vault_dir is not None:
        v = vault_dir.resolve()
        if not (v / ".paperloom").is_dir():
            raise VaultNotFoundError(f"{v} is not a paperloom vault (no .paperloom/ marker found).")
        return v

    p = (start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".paperloom").is_dir():
            return candidate
    raise VaultNotFoundError(
        f"No paperloom vault found from {p}. Run `paperloom init` here or in a parent directory."
    )


def resolve_path(vault_root: Path, rel_path: str) -> Path:
    """Resolve a vault-relative path, rejecting anything that would escape
    vault_root (e.g. via `../`). Used by every MCP tool that takes a `path`
    argument."""
    vault_root = Path(vault_root).resolve()
    candidate = (vault_root / rel_path).resolve()
    try:
        candidate.relative_to(vault_root)
    except ValueError:
        raise PathOutsideVaultError(f"{rel_path!r} resolves outside the vault") from None
    return candidate


def check_writable(rel_path: str) -> None:
    """Raise NotWritableError unless rel_path is under sources/, artifacts/,
    or logs/ — the write boundary §8's CLAUDE.md and §9's create_note both
    describe."""
    normalized = rel_path.replace("\\", "/")
    if not normalized.startswith(WRITABLE_PREFIXES):
        raise NotWritableError(
            f"Refusing to write outside sources/, artifacts/, or logs/: {rel_path!r}"
        )


def read_frontmatter(path: Path) -> tuple[dict, str]:
    """Split a markdown file into (frontmatter dict, body). Returns an empty
    dict if the file has no `---`-delimited frontmatter block."""
    text = path.read_text(encoding="utf-8")
    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            frontmatter = yaml.safe_load(text[4:end]) or {}
            body = text[end + 5 :]
            return frontmatter, body
    return {}, text


def write_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    """Write a markdown file as `---`-delimited YAML frontmatter + body,
    per §8's page-shape format."""
    fm_text = yaml.safe_dump(frontmatter, sort_keys=False) if frontmatter else ""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{fm_text}---\n{body}", encoding="utf-8")


def append_log_line(log_path: Path, line: str) -> None:
    """Append one line to a log file, creating its parent dir and a
    `# <stem>` header (e.g. `# 2026-08-24`) if the file doesn't exist yet."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if not log_path.exists():
        log_path.write_text(f"# {log_path.stem}\n\n", encoding="utf-8")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
