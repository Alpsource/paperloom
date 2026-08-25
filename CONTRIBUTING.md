# Contributing to paperloom

## Before you start

Paperloom follows a build spec (`paperloom.md`) that pins several things
deliberately — the 9 MCP tools ("no more"), the subprocess-supervision
invariant, folder-scoping, zero required API keys. If a change would touch
one of those, open an issue first rather than a PR; see `paperloom.md` §1
and §15 for the full list of non-negotiables and explicit non-goals.

Plugins are the intended extension point for new tools — see
[`docs/plugins.md`](docs/plugins.md) before proposing a new core tool.

## Setup

```bash
git clone https://github.com/Alpsource/paperloom
cd paperloom
uv venv && uv pip install -e ".[dev]"
source .venv/bin/activate
```

Use **uv**, not plain `pip` — a fresh `pip install -e ".[dev]"` genuinely
fails with `resolution-too-deep` (pip's resolver can't handle
`mineru[core]` + `fastmcp` together); `uv` resolves the same dependency
graph fine. See [Install](README.md#install) in the README for the full
story. If you're only working on a module that doesn't touch PDF parsing
or the MCP server, you can often skip those heavy deps entirely with a
narrower `pip install -e . --no-deps` plus whatever specific packages the
module you're touching needs.

## Running tests

```bash
pytest
```

`tests/test_supervisor.py` needs real POSIX signal delivery (`SIGTERM`
that a Python handler can actually catch) and won't behave the same on
native Windows — run it under WSL2 or another real POSIX environment.
Everything else is cross-platform.

## Before opening a PR

```bash
ruff check .
ruff format --check .
mypy src/
pytest
pip-audit
```

All of this runs in CI (`.github/workflows/ci.yml`) on every PR, including
a grep check that fails the build if a raw `subprocess.Popen` call shows
up outside `supervisor.py` — every subprocess paperloom spawns must go
through `paperloom.supervisor.spawn()` or the `child()` context manager,
no exceptions, so it's guaranteed to be cleaned up on every exit path.

## Commit style

Keep commits scoped to one logical change. No hard requirement on message
format, but explain *why*, not just *what* — the diff already shows what
changed.
