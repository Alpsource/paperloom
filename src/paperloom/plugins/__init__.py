"""Plugin discovery. See §10 of paperloom.md. A plugin module exposes
`register(mcp: FastMCP) -> None`; inside, it registers new tools with
`@mcp.tool`.

Loading order is built-in -> third-party -> vault-local. FastMCP itself
already warns and lets the later registration win on a name collision
(confirmed directly against the installed fastmcp: a duplicate `@mcp.tool`
name logs "Component already exists" and the second definition is what
actually runs) — so §10's "third-party overrides built-ins; vault-local
overrides both, warn don't silently shadow" falls out of this loading
order for free, with no custom override-tracking needed here."""

import importlib
import importlib.util
import sys
from importlib.metadata import entry_points
from pathlib import Path


def _warn_failed(name: str, e: Exception) -> None:
    print(f"[paperloom] plugin {name} failed to load: {e}", file=sys.stderr)


def load_all(mcp) -> list[str]:
    """Discover and load all plugins. Returns list of loaded plugin names.
    Never raises — a broken plugin (syntax error, bad import, whatever) is
    logged and skipped, the rest still load."""
    loaded: list[str] = []

    # 1) Built-in plugins (this directory)
    plugins_dir = Path(__file__).parent
    for f in sorted(plugins_dir.glob("*.py")):
        if f.name.startswith("_") or f.name == "__init__.py":
            continue
        name = f"paperloom.plugins.{f.stem}"
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, "register"):
                mod.register(mcp)
                loaded.append(f.stem)
        except Exception as e:
            _warn_failed(f.stem, e)

    # 2) Third-party plugins via entry points
    for ep in entry_points(group="paperloom.plugins"):
        try:
            mod = ep.load()
            if hasattr(mod, "register"):
                mod.register(mcp)
                loaded.append(ep.name)
        except Exception as e:
            _warn_failed(ep.name, e)

    # 3) Vault-local plugins (highest trust, from .paperloom/plugins/)
    try:
        from paperloom.vault import find_vault_root

        vault_plugins = find_vault_root() / ".paperloom" / "plugins"
        if vault_plugins.is_dir():
            for f in sorted(vault_plugins.glob("*.py")):
                try:
                    spec = importlib.util.spec_from_file_location(f.stem, f)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"could not load plugin spec for {f}")
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "register"):
                        mod.register(mcp)
                        loaded.append(f"vault:{f.stem}")
                except Exception as e:
                    _warn_failed(f"vault:{f.stem}", e)
    except Exception:
        pass  # No vault in scope; skip vault plugins.

    return loaded
