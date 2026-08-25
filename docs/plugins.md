# Writing a plugin

The 9 core MCP tools are a hard limit — paperloom's build spec pins that
list deliberately. If you want a new tool (a `find_related` helper, a
citation-graph exporter, a Slack-notify-on-ingest hook), you write a
plugin instead of touching core.

## The contract

A plugin is a Python module exposing one function:

```python
def register(mcp) -> None: ...
```

Inside `register`, define and register tools the normal FastMCP way:

```python
# paperloom/plugins/example_plugin.py — shipped as the reference plugin
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
            if f"[[{stem}]]" not in all_text and f"[[{stem}|" not in all_text:
                orphans.append(str(p.relative_to(root)))
        return orphans
```

Note that `find_vault_root()` is called *inside* each tool function, not
at module import time — a plugin module gets imported once, at server
startup, but its tools may be called many times across different sessions
(or, for a shared/third-party plugin, against whatever vault happens to be
current when a specific tool call runs).

## Three places a plugin can live

1. **Built-in** (`src/paperloom/plugins/*.py`) — ships with paperloom
   itself. `example_plugin.py` is the reference implementation.
2. **Third-party** — a regular pip package declaring an entry point:

   ```toml
   # your package's pyproject.toml
   [project.entry-points."paperloom.plugins"]
   awesome_plugin = "my_paperloom_plugin"
   ```

   `pip install my-paperloom-plugin`, and `paperloom mcp` picks it up
   automatically — no paperloom-side registration needed.
3. **Vault-local** (`<vault>/.paperloom/plugins/*.py`) — the highest-trust
   tier. No install step; the file lives in your vault and travels with it
   under git. Good for one-off tools specific to a single research project.

## Loading order and overrides

`paperloom mcp` loads built-in plugins first, then third-party, then
vault-local. If two plugins register a tool with the same name, the later
one wins — FastMCP logs a warning when this happens, so an accidental
collision is visible, never silent. In practice this means: vault-local
plugins can override anything (yours, always wins in your own vault),
third-party plugins can override built-ins, and built-ins are the
fallback.

A plugin that fails to import (syntax error, missing dependency, whatever)
is logged and skipped — it never takes down the rest of the server or the
other plugins.

## What NOT to build as a plugin

If you're duplicating a workflow `CLAUDE.md` already describes
(`/contribute`, `/ask`, `/lint`, `/rebuild-context`), you probably want a
[schema change](schema.md) instead — those are meant to be agent
judgment calls, not tool calls. Plugins are for new *file-manipulation
primitives*, the same category as the 9 core tools.
