# Quickstart

## 1. Install

Not yet on PyPI — install from source with
[uv](https://docs.astral.sh/uv/getting-started/installation/), not plain
`pip` (a fresh `pip install .` genuinely fails with `resolution-too-deep` —
pip's resolver can't handle `mineru[core]` + `fastmcp` together; `uv`
resolves the same graph fine):

```bash
git clone https://github.com/Alpsource/paperloom
cd paperloom
uv venv && uv pip install .
source .venv/bin/activate
```

Isolated in its own venv on purpose — paperloom's dependency stack
(PyTorch, transformers, ...) never touches your global Python or any
other project's environment.

*Prefer one command over an explicit venv?* `uv tool install ./paperloom`
gives the same isolation (each tool gets its own private venv under the
hood, same model as `pipx`) without an `activate` step — just a matter of
preference, not a tradeoff.

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
skeleton, `.mcp.json` — creates `.paperloom/config.yaml`, and runs
`git init` if the directory isn't already a repo. Nothing else to
configure before you can point an agent at it.

## 3. Ingest some papers

```bash
paperloom ingest ~/Downloads/papers/
```

Every PDF in that folder gets parsed by MinerU into
`sources/raw/<paper-id>/paper.md` + `meta.json`. This step is deliberately
separate from wiki-writing: it only ever touches `sources/raw/`, never
`sources/research/`. Re-running `ingest` skips anything already parsed.

## 4. Point your coding agent at the vault

`.mcp.json` is already there (from step 2) — nothing to configure. From
inside the vault directory:

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
