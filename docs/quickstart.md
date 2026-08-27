# Quickstart

## 1. Install

Not yet on PyPI — install from source with
[uv](https://docs.astral.sh/uv/getting-started/installation/), not plain
`pip` (a fresh `pip install .` genuinely fails with `resolution-too-deep` —
pip's resolver can't handle `mineru[core]` + `fastmcp` together; `uv`
resolves the same graph fine):

```bash
git clone https://github.com/Alpsource/paperloom
uv tool install ./paperloom
```

`paperloom` is now a plain global command — no venv to activate, works
from any directory. (If you're developing paperloom itself rather than
just using it, use a project venv instead — see `CONTRIBUTING.md`.)

You'll also need [ripgrep](https://github.com/BurntSushi/ripgrep#installation)
(`apt install ripgrep` / `brew install ripgrep` / etc.) — it's a system
binary `search` shells out to, not a pip package.

`mineru[core]` (the PDF parser, pulled in automatically) is a heavy
dependency — it installs PyTorch and, on first real use, downloads several
GB of model weights. See [Install](https://github.com/Alpsource/paperloom#install)
in the README for the full details and optional extras.

## 2. Create a vault

```bash
mkdir my-research && cd my-research
paperloom init
```

This copies the `scientific-paper-vault` template into place — `CLAUDE.md`,
an empty `context.md`/`index.md`, the `sources/`/`artifacts/`/`logs/`
skeleton — creates `.paperloom/config.yaml`, and runs `git init` if the
directory isn't already a repo. It does *not* create `.mcp.json` — that's
a separate one-time step, next.

## 3. Ingest some papers

```bash
paperloom ingest ~/Downloads/papers/
```

Every PDF in that folder gets parsed by MinerU into
`sources/raw/<paper-id>/paper.md` + `meta.json`. This step is deliberately
separate from wiki-writing: it only ever touches `sources/raw/`, never
`sources/research/`. Re-running `ingest` skips anything already parsed.

## 4. Point your coding agent at the vault

Create `.mcp.json` in the vault root yourself (one-time, per vault):

```json
{ "mcpServers": { "paperloom": { "command": "paperloom", "args": ["mcp"] } } }
```

Then, from inside the vault directory:

```bash
claude "/contribute the paper at sources/raw/2301.08243"
claude "What does my wiki know about JEPA?"
```

(Want a fully offline, no-API-key setup instead? Run
`ollmcp --servers-json .mcp.json --model qwen3.5:4b` in place of `claude`
— same `.mcp.json`, same vault, no editor required. See
[Local / offline models](quickstart-local.md).)

The agent reads `CLAUDE.md`, decides what pages to create or update, shows
you a plan, and — on your approval — writes real wiki pages via the MCP
tools (`create_note`, `append_to_page`, `search`, ...). See
[Schema](schema.md) for what those pages actually look like, and the
worked example in
[`examples/ml-robotics-vault/`](https://github.com/Alpsource/paperloom/tree/main/examples/ml-robotics-vault)
in the repo for a fully populated one.
