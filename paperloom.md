# Paperloom — implementation spec

> **A folder-scoped, LLM-maintained research wiki. MCP server + CLI + starter schema, ~500 lines of Python. Zero API keys, one directory per knowledge base, batch PDF ingest built in.**

**For the implementing agent:** this document is a build spec. Follow it literally. Do not re-litigate design decisions marked "decided." When Section 9 says "10 tools, no more," that is a hard constraint. Ask before adding anything not in this doc.

**Product positioning:** Paperloom implements Andrej Karpathy's [`llm-wiki` pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), inspired by [MindBase](https://github.com/frankchu91/mindbase-llm-wiki)'s productization of it, with three specific improvements for scientific-paper research: (1) batch PDF ingest with MinerU pre-parsing, (2) one KB per working directory (no global data folder), (3) zero required LLM API keys — the host coding agent (Claude Code, Gemini CLI, etc.) is the LLM.

**License:** Apache-2.0. Credit both Karpathy and MindBase prominently in the README.

**Language:** Python 3.11+. Pure stdlib where possible; ~10 direct dependencies max.

---

## 1. Non-negotiable design principles

These are the invariants the implementation must preserve. Every change to the codebase should be checked against them.

1. **The MCP server is dumb; the CLAUDE.md schema is smart.** The server exposes file-manipulation primitives. It does not synthesize, summarize, or reason. All intelligence lives in the host agent (Claude Code, Gemini CLI) driven by the vault's `CLAUDE.md`.

2. **One vault per directory, no global state.** Every command derives the vault root from the current working directory (walking up until it finds a `.paperloom/` marker). No `~/.paperloom-data/`, no `~/.config/paperloom/`, no environment-variable indirection. `git init && paperloom init` in any folder produces a fully self-contained KB.

3. **Markdown files on disk are the source of truth.** No SQLite index, no cached JSON, no `.paperloom.db`. If a file exists in `sources/research/foo.md`, that's what the tool sees. If the user deletes it, it's gone. If the user runs `git checkout`, the vault reflects that. The `.paperloom/` folder holds only ephemeral cache (search index, MinerU parse cache) that can be safely deleted and rebuilt.

4. **No LLM API keys, ever, and no LLM calls of any kind — including local ones.** The tool must never require `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, or any equivalent to function, and it must never call Ollama or any other model directly either. The tool exposes file operations; the host agent supplies the intelligence via whatever subscription or local model the user already has. Users who want fully-offline synthesis point a local-model-capable host agent (Continue.dev, Cline, Aider, ...) at paperloom's MCP server — see Section 11.

5. **Every subprocess is supervised.** Ingestion spawns MinerU (which spawns Python subprocesses which spawn PyTorch which spawns CUDA workers). Every one of these gets registered with a supervisor that guarantees termination via `atexit`, signal handlers, and process-group kills. A `KeyboardInterrupt`, an unhandled exception, an OOM, or a machine power-off must never leave orphan processes. This is a first-class invariant with tests, not a nice-to-have.

6. **Batch is a first-class primitive.** `paperloom ingest <folder>` handles a directory of 50+ PDFs. No sequential per-file agent conversations. Progress bar, resumable checkpoint, skip-if-already-parsed.

7. **Modular, additive extensions.** New features are new files (`src/paperloom/plugins/<name>.py`), not modifications to core. The MCP tool list is `core_tools + plugin_tools` where plugins register themselves via a discovery mechanism.

8. **The CLAUDE.md is a template, not code.** Users edit their own copy. The tool never overwrites `CLAUDE.md` after `paperloom init` completes. Schema changes are documented in `CHANGELOG.md` for users to opt into manually.

---

## 2. Repository layout

```
paperloom/
├── pyproject.toml
├── README.md                          # Credits Karpathy + MindBase prominently
├── LICENSE                            # Apache-2.0
├── CHANGELOG.md
├── .gitignore
├── src/paperloom/
│   ├── __init__.py                    # __version__
│   ├── cli.py                         # Typer entry point: init, ingest, mcp, doctor, version
│   ├── vault.py                       # Vault discovery, path resolution, frontmatter I/O
│   ├── ingest.py                      # PDF → MinerU → sources/raw/<id>/
│   ├── search.py                      # ripgrep wrapper + optional sqlite-fts5 index
│   ├── supervisor.py                  # Subprocess supervision (Section 6)
│   ├── mcp_server.py                  # FastMCP server exposing the 10 tools
│   ├── plugins/
│   │   ├── __init__.py                # Plugin discovery (Section 10)
│   │   └── example_plugin.py          # Reference plugin for docs
│   ├── workflows/                     # describe_workflow's recipes (Section 9, tool 10)
│   │   ├── contribute.md
│   │   ├── ask.md
│   │   ├── lint.md
│   │   ├── rebuild_context.md
│   │   └── ingest.md
│   └── templates/
│       └── scientific-paper-vault/    # Copied verbatim by `paperloom init`
│           ├── CLAUDE.md              # The schema (Section 8)
│           ├── README.md              # User-editable, describes their vault
│           ├── context.md             # Empty; the agent will fill it
│           ├── index.md               # Empty; the agent will fill it
│           ├── log.md                 # Header only
│           ├── sources/
│           │   ├── research/.gitkeep  # Agent writes wiki pages here
│           │   ├── contributors/.gitkeep
│           │   └── raw/.gitkeep       # `paperloom ingest` writes here
│           ├── artifacts/.gitkeep     # Generated outputs (Marp decks, drafts)
│           └── logs/.gitkeep          # Per-day operation logs
├── tests/
│   ├── test_vault.py
│   ├── test_ingest.py
│   ├── test_supervisor.py             # Kill-9 the parent, assert no orphans
│   ├── test_search.py
│   ├── test_mcp_tools.py              # Each of the 10 tools, happy + error paths
│   ├── test_plugins.py                # Plugin discovery + registration
│   └── qualitative/
│       └── three_question_eval.md     # Reference eval for model-quality tiers (Section 11)
├── docs/
│   ├── index.md                       # mkdocs entry
│   ├── quickstart.md
│   ├── quickstart-local.md            # Local/offline models, host-agent recommendations (Section 11)
│   ├── schema.md                      # How to customize CLAUDE.md
│   ├── plugins.md                     # How to write a plugin
│   └── credits.md                     # Karpathy pattern + MindBase attribution
├── examples/
│   └── ml-robotics-vault/             # Fully-populated demo vault (small, ~5 papers)
└── .github/workflows/
    ├── ci.yml                         # ruff, mypy, pytest, pip-audit
    └── release.yml                    # uv build + publish to PyPI on tag
```

**Critical directory conventions:**
- `.paperloom/` (created by `paperloom init`) is the vault marker. Contains `config.yaml`, `cache/`, and nothing else. Safe to delete.
- `sources/raw/<paper-id>/` holds `paper.pdf`, `paper.md` (MinerU output), `references.xml` (GROBID output, optional), `meta.json`. Immutable after ingest.
- `sources/research/` holds wiki pages the agent writes. Flat directory; filenames are kebab-case slugs. No subdirectories at first — add them only if `CLAUDE.md` schema calls for them.
- `sources/contributors/<username>/YYYY-MM-DD.md` holds per-user daily notes appended by `contribute`.

---

## 3. Vault discovery

The single most important architectural decision: **every operation resolves the vault root by walking up from `os.getcwd()` until it finds a `.paperloom/` marker directory.** If none is found, the command errors with a clear message.

```python
# src/paperloom/vault.py
from pathlib import Path


class VaultNotFoundError(Exception): ...


def find_vault_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: cwd) until a .paperloom/ dir is found."""
    p = (start or Path.cwd()).resolve()
    for candidate in [p, *p.parents]:
        if (candidate / ".paperloom").is_dir():
            return candidate
    raise VaultNotFoundError(
        f"No paperloom vault found from {p}. Run `paperloom init` here or in a parent directory."
    )
```

Every tool, every command, every plugin calls `find_vault_root()` at the top. There is no other way to locate the vault. `--vault-dir` flag exists on the CLI as an escape hatch but is not the primary path.

---

## 4. Dependencies (pyproject.toml)

```toml
[project]
name = "paperloom"
version = "0.1.0"
description = "Folder-scoped LLM-maintained research wiki for scientific papers"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "Apache-2.0" }
authors = [{ name = "your-name" }]
keywords = ["llm-wiki", "karpathy", "mindbase", "knowledge-base", "mcp", "research"]

dependencies = [
  # CLI + config
  "typer>=0.12",
  "rich>=13.7",
  "pyyaml>=6.0",
  "pydantic>=2.7",

  # MCP server
  "fastmcp>=2.0",

  # PDF parsing (primary)
  "mineru>=3.1",

  # HTTP for optional metadata enrichment (Semantic Scholar)
  "httpx>=0.27",

  # File watching for optional live-reindex plugin
  "watchdog>=4.0",
]

[project.optional-dependencies]
# No `ollama` extra — see §11: paperloom never calls an LLM itself,
# including local ones (paperloom_ollama_correction.md).
grobid = ["grobid-tei-xml>=0.1"]    # for bibliography extraction
fts    = ["sqlite-fts5"]            # NOT REAL — use stdlib sqlite3 which has FTS5 built in
dev    = ["pytest>=8.3", "pytest-xdist", "ruff>=0.6", "mypy>=1.11",
          "pre-commit", "mkdocs-material", "pip-audit"]

[project.scripts]
paperloom = "paperloom.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Note to implementer:** stdlib `sqlite3` already includes FTS5. Do not add a separate FTS package. The `fts` extra above is a placeholder for future upgrade paths only.

**Note on `mineru`:** it's a heavy dep (pulls PyTorch, ~2 GB). Consider making it an optional extra `[parse]` if users want a lightweight install, with `paperloom ingest` erroring cleanly if not present. Decide during implementation; default to including it.

---

## 5. CLI commands

Implement with Typer. Every command works from anywhere inside a vault (uses `find_vault_root`).

```
paperloom init [DIR] [--template scientific-paper-vault] [--force]
    Create a new vault at DIR (default: cwd). Copies the template into place,
    creates .paperloom/config.yaml, initializes git if not already a repo.
    Refuses to overwrite existing files unless --force.

paperloom ingest FOLDER [--pattern "*.pdf"] [--jobs 1] [--skip-existing]
    Batch-ingest every PDF in FOLDER matching --pattern.
    Runs MinerU on each, writes sources/raw/<id>/paper.md + meta.json.
    Shows a rich progress bar. Resumable: skips PDFs whose <id>/paper.md exists.
    --jobs > 1 runs MinerU in parallel (supervised, see §6).

paperloom mcp
    Start the MCP server on stdio. Blocks. Ctrl-C to stop.
    This is what .mcp.json points to.

paperloom doctor
    Check environment: python version, mineru installed, ripgrep on PATH,
    disk space, subprocess-supervisor test. Prints a report. Exit 0 if all green.
    (No Ollama check — paperloom has no awareness of what LLM, if any, the
    host agent uses. See §11.)

paperloom search QUERY [--top 10]
    Command-line search over the vault. Uses the same backend as the search MCP tool.
    Useful for scripting and debugging.

paperloom version
    Print version, python version, key dep versions.
```

**Design note:** no `paperloom contribute`, no `paperloom ask`, no `paperloom lint`. Those are agent workflows driven by CLAUDE.md, not CLI commands. Keep the CLI surface minimal. Users interact via their host coding agent.

---

## 6. Subprocess supervisor (critical)

This is the invariant most likely to break in the wild. Implement it carefully.

**Requirements:**
- Every subprocess spawned by paperloom is registered with a global supervisor.
- On any exit path — normal completion, `KeyboardInterrupt`, `SIGTERM`, `SIGHUP`, unhandled exception, `os._exit`, parent crash — all registered subprocesses and their descendants are terminated.
- Uses process groups (`os.setsid` on POSIX, `CREATE_NEW_PROCESS_GROUP` on Windows) so killing the parent takes the whole tree.
- Escalation: `SIGTERM` → wait 5s → `SIGKILL`.

```python
# src/paperloom/supervisor.py
import atexit, os, signal, subprocess, sys, threading, weakref
from contextlib import contextmanager


class Supervisor:
    def __init__(self):
        self._procs: set[weakref.ref[subprocess.Popen]] = set()
        self._lock = threading.Lock()
        atexit.register(self.shutdown)
        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            try:
                signal.signal(sig, self._on_signal)
            except (ValueError, AttributeError):
                pass  # SIGHUP not on Windows, signals not settable in threads

    def spawn(self, cmd: list[str], **kwargs) -> subprocess.Popen:
        popen_kwargs = dict(kwargs)
        if os.name == "posix":
            popen_kwargs.setdefault("start_new_session", True)
        else:
            popen_kwargs.setdefault(
                "creationflags",
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
            )
        proc = subprocess.Popen(cmd, **popen_kwargs)
        with self._lock:
            self._procs.add(weakref.ref(proc))
        return proc

    def _terminate(self, proc: subprocess.Popen) -> None:
        if proc.poll() is not None:
            return
        try:
            if os.name == "posix":
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            else:
                proc.send_signal(signal.CTRL_BREAK_EVENT)
        except (ProcessLookupError, OSError):
            return
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                else:
                    proc.kill()
            except (ProcessLookupError, OSError):
                pass

    def shutdown(self) -> None:
        with self._lock:
            refs = list(self._procs)
            self._procs.clear()
        for ref in refs:
            proc = ref()
            if proc is not None:
                self._terminate(proc)

    def _on_signal(self, signum, frame):
        self.shutdown()
        sys.exit(128 + signum)


_supervisor = Supervisor()


def spawn(cmd: list[str], **kwargs) -> subprocess.Popen:
    """Only entry point for spawning subprocesses in paperloom."""
    return _supervisor.spawn(cmd, **kwargs)


@contextmanager
def child(cmd: list[str], **kwargs):
    """Context manager: spawn, yield, terminate on exit even if user code raises."""
    proc = spawn(cmd, **kwargs)
    try:
        yield proc
    finally:
        _supervisor._terminate(proc)
```

**Tests in `test_supervisor.py`:**
1. Spawn a long-running child, `SIGTERM` the parent test process, assert child is gone within 10s.
2. Spawn a child, raise inside the `with child(...)` block, assert child is gone.
3. Spawn a child that itself spawns a grandchild, kill parent, assert grandchild is gone (validates process-group).
4. Spawn 10 children in parallel, `os._exit(1)` the parent (bypasses atexit), assert all children are gone within 10s of parent death. (This may require a small Bash test harness.)

**Every `subprocess.Popen` call in the codebase must go through `paperloom.supervisor.spawn` or the `child()` context manager. Add a CI check (grep) that fails PRs adding raw `subprocess.Popen`.**

---

## 7. Ingestion pipeline

```
paperloom ingest ~/Downloads/papers/
```

1. **Discover PDFs.** Glob `FOLDER/**/*.pdf` (or `--pattern`).
2. **Compute IDs.** For each PDF, derive a stable ID:
   - If filename or first-page text matches arXiv regex (`\d{4}\.\d{4,5}`), use that.
   - Else, if DOI is present in first-page text, use DOI slugified.
   - Else, use `sha256(pdf_bytes)[:12]`.
3. **Check for existing.** If `sources/raw/<id>/paper.md` exists and `--skip-existing` (default), skip.
4. **Parse with MinerU** (supervised via `paperloom.supervisor.spawn`):
   - Write PDF to `sources/raw/<id>/paper.pdf` (copy, don't move — user keeps original).
   - Run `mineru -p sources/raw/<id>/paper.pdf -o sources/raw/<id>/mineru-out --formula-enable true --table-enable true`.
   - Move `mineru-out/<basename>/auto/<basename>.md` → `sources/raw/<id>/paper.md`.
   - Clean up `mineru-out/`.
5. **Optionally parse bibliography with GROBID** (if `[grobid]` extra installed and `GROBID_URL` env var set): POST to `/api/processFulltextDocument`, save `references.xml`.
6. **Build `meta.json`.** Fields: `id`, `title`, `authors[]`, `year`, `venue`, `doi`, `arxiv_id`, `sha256`, `ingested_at`, `n_pages`, `n_refs`. Populate from MinerU output, then optionally enrich via Semantic Scholar `/paper/DOI:<doi>` or `/paper/ARXIV:<id>` (best-effort, no key required at low volume).
7. **Append log entry** to `logs/<today>.md`: `- INGEST <id> (<title>) — <n> pages parsed`.
8. **Progress bar** via Rich, one line per PDF.

**Parallelism.** With `--jobs N`, run up to N MinerU invocations concurrently. Each is a separate subprocess (supervised). MinerU itself uses GPU/CPU internally; typical parallelism is 1 on GPU, 2–4 on CPU.

**Failure modes:**
- MinerU crash on a PDF → log the error, write `sources/raw/<id>/PARSE_FAILED.txt` with the traceback, continue to next PDF. Do not abort the batch.
- MinerU produces no output → same as crash.
- Disk full → abort with a clear message, do not corrupt existing state.
- User Ctrl-Cs → supervisor kills all in-flight MinerU processes cleanly, prints "aborted after N/M papers", exit 130.

**Ingestion is deliberately separate from wiki writing.** `paperloom ingest` produces raw markdown in `sources/raw/`. The host agent (Claude Code) reads that raw markdown and produces wiki pages in `sources/research/` when the user runs `/contribute` or similar. This separation is intentional — it means you can re-parse without touching the wiki, and you can re-generate the wiki without re-parsing.

---

## 8. The CLAUDE.md schema (shipped in templates/scientific-paper-vault/CLAUDE.md)

Copy this verbatim into `src/paperloom/templates/scientific-paper-vault/CLAUDE.md`. Users edit it after `paperloom init`. The tool never overwrites it.

````markdown
# CLAUDE.md — Paperloom scientific-paper vault

You are the maintainer of a personal research wiki for a working scientist
(defaults to ML/robotics, edit below for your domain). Your job is to read
papers the user ingests, integrate them into a persistent markdown wiki,
answer research questions grounded in that wiki, and periodically audit it
for drift.

You do NOT write research; you maintain the substrate the user writes
research on top of. You are the librarian, cross-referencer, and bookkeeper.
The user curates sources, asks the questions, and thinks.

## Domain focus (EDIT THIS)

- Primary topics: self-supervised representation learning, JEPA-family
  architectures, drug-target interaction, visual-inertial odometry.
- Favored venues: NeurIPS, ICML, ICLR, CVPR, RSS, ICRA, Nature Methods.
- Adjacent topics I care about: MLSys, foundation models for biology,
  world models.

## The three layers

- `sources/raw/<paper-id>/` is IMMUTABLE. Contains the original PDF, the
  MinerU-parsed `paper.md`, and `meta.json`. You READ from it, quote from
  it, link to it. You NEVER edit anything here. If a parse looks wrong,
  tell the user and stop.
- `sources/research/` is YOURS. You create, update, and cross-link markdown
  pages here. Every page follows one of the shapes in "Page shapes" below.
- `sources/contributors/<user>/YYYY-MM-DD.md` is the USER's daily log.
  You append entries when the user says "add to today" or via /contribute.
  You never rewrite past entries.

## Provenance discipline (hard rule)

Every non-trivial claim in `sources/research/` MUST link back to the raw
source that supports it. Format:

  > I-JEPA predicts representations of target blocks rather than pixels
  > [[raw:2301.08243#sec-3-1]].

The anchor after `#` corresponds to a section header in the MinerU-parsed
markdown. If no exact section fits, use the nearest enclosing section and
quote a short (<15-word) verbatim span in a blockquote.

Three exceptions, marked explicitly:
1. `{{common-knowledge}}` — standard facts every researcher knows.
2. `{{synthesis: [[raw:A]], [[raw:B]]}}` — your inferences across sources.
3. `{{unclear-in-source}}` — the raw text is ambiguous or MinerU garbled it.

If none of these apply and you can't cite a raw source, DO NOT write the
claim. Tell the user instead.

## Page shapes

Every page in `sources/research/` uses YAML frontmatter. Field names are
exact — some tooling reads them.

### paper page — `sources/research/<paper-id>-<lastname>-<slug>.md`

```yaml
---
type: paper
id: 2301.08243
title: Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture
authors: [Assran, Duval, Misra, ...]
year: 2023
venue: CVPR
tags: [ssl, jepa, computer-vision]
raw: sources/raw/2301.08243/paper.md
---
```

Body sections: TLDR (1 paragraph) → Contributions (bulleted, each with a
[[raw:...]] anchor) → Method summary (2-4 paragraphs, LaTeX inline) →
Datasets & metrics (bulleted, linking [[method:...]] and [[dataset:...]])
→ Related work in this vault (bulleted [[paper:...]]) → Open questions.

### method page — `sources/research/methods/<slug>.md`

```yaml
---
type: method
canonical: I-JEPA
aliases: [Image JEPA]
kind: architecture  # architecture | algorithm | objective | framework
introduced_by: [paper:2301.08243]
uses: [method:vit, method:ema-target-encoder]
applied_to: [concept:self-supervised-representation-learning]
---
```

Body: 1-paragraph definition; the core equation in LaTeX; a "how it works"
summary in 3-5 sentences; a table of variants (linked to their papers).

### dataset page — `sources/research/datasets/<slug>.md`

```yaml
---
type: dataset
canonical: ImageNet-1k
aliases: [ILSVRC-2012, IN-1k]
modality: images
size: 1.28M train / 50k val
---
```

### concept page — `sources/research/concepts/<slug>.md`

Body: definition; when it matters; papers that shaped current understanding;
sibling concepts.

### synthesis page — `sources/research/syntheses/<date>-<slug>.md`

You write these when the user asks a cross-paper question whose answer is
worth keeping. Body starts with the question verbatim, then the answer,
then a "sources touched" list linking every [[paper:...]] and [[raw:...]]
you consulted.

## The four operations

### /contribute — process new input

Trigger phrases: "add to wiki", "ingest this", "process paper X",
"remember Y".

Workflow:
1. If the input is a short thought: append to
   `sources/contributors/<user>/<today>.md`. Done.
2. If the input references a `sources/raw/<id>/` that was ingested by
   `paperloom ingest`:
   a. Read `sources/raw/<id>/paper.md` and `meta.json`.
   b. Call `search` for existing pages whose canonical names or aliases
      appear in the paper. This prevents duplicate methods/datasets.
   c. Draft a PLAN: papers/methods/datasets/concepts to CREATE, existing
      pages to UPDATE (state what you'll add — one line each).
   d. Show the plan. WAIT for approval unless the user explicitly said
      "batch mode".
   e. On approval, write every file via `create_note` / `append_to_page`.
      Use [[wikilinks]] liberally. Append log entry.
3. If the input is text pasted by the user (not from raw/): treat as a
   thought → append to contributors/.

### /ask — answer a question from the wiki

Workflow:
1. Call `search` for candidate pages by keyword.
2. Read the top pages via `read_page`.
3. Follow [[wikilinks]] at most 2 hops deep, reading each.
4. If a claim needs an exact number or quote, read the underlying raw file
   via `read_page` on the `raw:` path — never quote from a research page,
   always verify against the raw source.
5. Answer with citations. Every non-trivial claim carries [[wikilink]] or
   [[raw:...]].
6. Ask the user: file this answer as `sources/research/syntheses/`? If yes,
   write it and log.

### /lint — health check

Weekly (or on request).

Walk `sources/research/**/*.md`. Report:
- Orphan pages (no inbound [[wikilinks]]).
- Dangling links ([[X]] where X doesn't exist).
- Missing pages (methods/datasets mentioned in paper pages but no own page).
- Paragraphs in `sources/research/` without [[raw:...]] or
  {{common-knowledge}} / {{synthesis}} / {{unclear-in-source}} markers.
- Contradictions: two pages making opposite claims about the same entity.

Present findings to user. DO NOT auto-fix.

### /rebuild-context — regenerate context.md

Read all recent contributor entries + all research pages. Rewrite
`context.md` as the current synthesized truth across the vault — 500-2000
words, no citations required (context.md is a landing page, not a
reference). Snapshot the old context.md into `.paperloom/cache/snapshots/`
first for rollback.

## Tools available

Read `.paperloom/config.yaml` for the full list. Core tools you'll use most:
`search`, `read_page`, `create_note`, `append_to_page`, `tag_note`,
`log_entry`, `list_pages`. Ingestion (`ingest_pdf`) is usually run by the
user via CLI, not by you.

Do not install packages, spin up services, or write outside `sources/` or
`logs/` or `artifacts/`.

## Style

- Preserve equations in LaTeX ($$...$$ for display, $...$ for inline).
- Never invent hyperparameters, dataset sizes, or metrics. If you need a
  number and it isn't in the source, say "not reported".
- Quote verbatim for theorems and key definitions (<15 words, in >
  blockquotes).
- Every synthesis page links at least three [[paper:...]].

## What compounds

The value is the density of the graph. Every /contribute should add at
least one new cross-link between existing pages. Every synthesis should
link three or more papers. Every /lint should reduce orphan count. The
user will notice when the graph is dense enough to be genuinely useful —
that's when the pattern is working.
````

### Mode-aware CLAUDE.md (added by `paperloom_ollama_correction.md`)

Add these subsections to `templates/scientific-paper-vault/CLAUDE.md` right after the "Domain focus" section.

````markdown
## Operating mode (EDIT THIS ONCE)

Set one of the following based on what host agent you use with this vault:

- `mode: capable` — you use Claude Code with Sonnet-tier or better, Gemini
  CLI with Gemini 2.5 Pro, or GPT-5-tier via Codex/similar. The agent is
  expected to follow this schema in full, use judgment about when to
  synthesize, walk the graph 2 hops deep, and proactively offer to file
  answers as synthesis pages.

- `mode: local` — you use Continue.dev / Cline / Aider pointed at a local
  Ollama model (Qwen3-14B, Llama 3-8B, or similar). The agent gets
  step-by-step recipes for every operation, does not attempt multi-hop
  reasoning, asks for confirmation before every write, and reads fewer
  pages per query to fit smaller context windows.

**Current mode: capable**    ← edit to `local` if using local models

The rest of this file has sections marked "[all modes]", "[capable only]",
and "[local only]". Follow the sections that match your mode.
````

Then, throughout the CLAUDE.md, tag each behavioral rule in "The four operations" with `[capable mode]` / `[local mode]` variants, following the exact pattern shown for `/ask` in `paperloom_ollama_correction.md` (search → read top hit → cite → offer synthesis for local mode, vs. multi-hop reasoning for capable mode) — extended consistently to `/contribute`, `/lint`, and `/rebuild-context` too. Every workflow section gets both variants, clearly labeled; the agent follows the one matching its mode.

**Why this beats two separate files:** one source of truth (schema changes propagate to both modes automatically), the user can switch modes any time by editing one line, diffs stay readable (a workflow change shows up in both variants side-by-side), and small models don't get confused by irrelevant capable-mode instructions because the section header tells them to skip.

---

## 9. The MCP server: 10 tools, no more

Implement with FastMCP. Every tool takes a `vault_root` implicitly via `find_vault_root()`. Every tool returns Pydantic-typed JSON. Every tool is ~20 lines.

**The 10 tools (final list — do not add more without changing this spec):**

1. **`search(query: str, top_k: int = 10, path_prefix: str = None) -> list[SearchHit]`**
   Ripgrep across the vault (or SQLite FTS5 if enabled). Returns paths + snippet + line number. `path_prefix` scopes to e.g. `sources/research/methods/`.

2. **`read_page(path: str) -> str`**
   Read a markdown file relative to vault root. Full contents including frontmatter. Path examples: `sources/research/methods/i-jepa.md`, `sources/raw/2301.08243/paper.md`.

3. **`list_pages(subdir: str = "sources/research", pattern: str = "*.md") -> list[PageInfo]`**
   List files with basic frontmatter (type, tags, title). Fast; no full-content read.

4. **`create_note(path: str, title: str, content: str, tags: list[str] = None, frontmatter: dict = None) -> dict`**
   Create a new markdown file with YAML frontmatter. Fails if path exists (use `append_to_page` to modify). Refuses to write outside `sources/`, `artifacts/`, or `logs/`.

5. **`append_to_page(path: str, content: str, section: str = None, guard: str = "auto") -> dict`**
   Append content to an existing page. If `section` is given, append under that H2/H3 header. `guard` in `{"auto", "force", "human-safe"}`:
   - `"auto"` (default): if the page has `human_edited: true` in frontmatter, refuse.
   - `"force"`: append regardless.
   - `"human-safe"`: append but wrap in `<!-- agent-added ... -->` sentinels so the user can see what changed.

6. **`tag_note(path: str, tags: list[str], mode: str = "merge") -> dict`**
   Add tags to a page's frontmatter. `mode` in `{"merge", "replace"}`.

7. **`log_entry(kind: str, text: str, contributor: str = None) -> dict`**
   Append a line to today's log (`logs/YYYY-MM-DD.md`) or contributor's daily file if `contributor` given. Format: `- HH:MM [KIND] text`. Creates the file if missing.

8. **`ingest_pdf(pdf_path: str, id_hint: str = None) -> dict`**
   Same as `paperloom ingest` but for a single PDF, callable from the agent. Returns `{"id": "...", "raw_path": "sources/raw/<id>/paper.md", "n_pages": N}`. Supervised subprocess for MinerU.

9. **`vault_info() -> dict`**
   Return `{"root": "...", "config": {...}, "n_raw": ..., "n_research": ..., "n_logs": ..., "plugins_loaded": [...]}`. Useful for the agent's first read of the session.

10. **`describe_workflow(operation: str) -> str`** *(added by `paperloom_ollama_correction.md`)*
    Return a step-by-step recipe for a paperloom workflow (`"contribute"`, `"ask"`, `"lint"`, `"rebuild_context"`, `"ingest"`, or `"list_all"`). Reads from `src/paperloom/workflows/<operation>.md`, shipped with the package. Used primarily by small local models that need workflow guidance beyond what CLAUDE.md provides — frontier models typically don't need this.

**Not on the list, and not to be added:**
- No `ask_wiki` / `run_wiki_health` / `ingest_plan` / `ingest_execute` — the agent does these itself using the tools above.
- No `find_related` / `find_orphans` / `find_contradictions` / `find_gaps` — the agent can compute these from `search` + `list_pages` + `read_page`.
- No `semantic_search` — ripgrep + agent reasoning covers it. Add later as a plugin if needed.
- No `daily_brief` / `review_card` / `RSS` — plugin territory (§10).
- No auth, no multi-user, no team features. This is a personal tool.

**Skeleton:**

```python
# src/paperloom/mcp_server.py
from fastmcp import FastMCP
from pydantic import BaseModel
from pathlib import Path
from paperloom.vault import find_vault_root
from paperloom import search, vault, ingest

mcp = FastMCP("paperloom")


class SearchHit(BaseModel):
    path: str
    line: int
    snippet: str
    score: float


@mcp.tool
def search(query: str, top_k: int = 10, path_prefix: str | None = None) -> list[SearchHit]:
    """Full-text search across the vault. Returns paths + snippets."""
    root = find_vault_root()
    return search.hybrid_search(root, query, top_k=top_k, path_prefix=path_prefix)


# ... other 8 tools follow the same pattern

# Load plugins (§10)
from paperloom.plugins import load_all

load_all(mcp)

if __name__ == "__main__":
    mcp.run()  # stdio by default
```

**MCP config the user drops in `.mcp.json` at their vault root:**

```json
{
  "mcpServers": {
    "paperloom": {
      "command": "paperloom",
      "args": ["mcp"]
    }
  }
}
```

For Gemini CLI, `.gemini/settings.json`:

```json
{ "mcpServers": { "paperloom": { "command": "paperloom", "args": ["mcp"] } } }
```

---

## 10. Plugin system

**Requirement:** users (and you, later) can add new tools without modifying core.

**Implementation.** Plugins are Python modules under `src/paperloom/plugins/` (built-in) or discovered via the `paperloom.plugins` entry point group (third-party, installed as regular pip packages).

```python
# src/paperloom/plugins/__init__.py
from importlib.metadata import entry_points
from pathlib import Path
import importlib.util
import sys


def load_all(mcp) -> list[str]:
    """Discover and load all plugins. Returns list of loaded plugin names."""
    loaded = []

    # 1) Built-in plugins (this directory)
    plugins_dir = Path(__file__).parent
    for f in plugins_dir.glob("*.py"):
        if f.name.startswith("_") or f.name == "__init__.py":
            continue
        name = f"paperloom.plugins.{f.stem}"
        mod = importlib.import_module(name)
        if hasattr(mod, "register"):
            mod.register(mcp)
            loaded.append(f.stem)

    # 2) Third-party plugins via entry points
    for ep in entry_points(group="paperloom.plugins"):
        try:
            mod = ep.load()
            if hasattr(mod, "register"):
                mod.register(mcp)
                loaded.append(ep.name)
        except Exception as e:
            print(f"[paperloom] plugin {ep.name} failed to load: {e}", file=sys.stderr)

    # 3) Vault-local plugins (highest trust, from .paperloom/plugins/)
    try:
        from paperloom.vault import find_vault_root

        vault_plugins = find_vault_root() / ".paperloom" / "plugins"
        if vault_plugins.is_dir():
            for f in vault_plugins.glob("*.py"):
                spec = importlib.util.spec_from_file_location(f.stem, f)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "register"):
                    mod.register(mcp)
                    loaded.append(f"vault:{f.stem}")
    except Exception:
        pass  # No vault in scope; skip vault plugins.

    return loaded
```

**Plugin contract:** a plugin module exposes `register(mcp: FastMCP) -> None`. Inside, it defines and registers new tools with `@mcp.tool`.

**Example plugin (ship as `plugins/example_plugin.py`):**

```python
# src/paperloom/plugins/example_plugin.py
"""Example plugin: exposes `word_count` and `find_orphans` tools."""

from pathlib import Path
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
```

**Users write their own plugins** in `<vault>/.paperloom/plugins/*.py` — highest trust, no install needed, versioned with their vault via git.

**Third-party plugins** register via `pyproject.toml`:

```toml
[project.entry-points."paperloom.plugins"]
awesome_plugin = "my_paperloom_plugin"
```

Then `pip install my-paperloom-plugin` and `paperloom mcp` picks it up automatically.

**Planned first-party plugins (not to build initially, but reserve space in the plugins/ dir):**

- `arxiv_watcher` — poll arXiv for new papers matching saved queries, prompt user to ingest.
- `marp_export` — turn a synthesis page into a Marp slide deck under `artifacts/`.
- `graph_export` — export the [[wikilink]] graph as GraphViz DOT or JSON for visualization.
- `citekey_lint` — validate that every `\cite{...}` in draft artifacts resolves to a paper in the vault.

**Loading precedence:** third-party plugins override built-ins with the same tool name; vault-local plugins override both. Warn on override, don't silently shadow.

---

## 11. Model-agnostic architecture

**Non-goal: paperloom does not call an LLM.** Ever. Not for synthesis, not for classification, not for embedding. The MCP server is pure file operations. This is design principle #1 and #4 from Section 1; this section explains what that means for users who want to run paperloom against local models.

*(This section replaces an earlier "Ollama backend" design — see `paperloom_ollama_correction.md` for the full rationale if you're wondering why there's no `ollama_synth` plugin here.)*

### The correct boundary

```
┌──────────────────────────────────────────────────────────┐
│  HOST AGENT (any MCP-compatible client)                  │
│  - Claude Code           → Anthropic API                 │
│  - Continue.dev          → any model incl. Ollama         │
│  - Cline (VSCode)        → any model incl. Ollama         │
│  - Aider                 → any model incl. Ollama         │
│  - Gemini CLI            → Google API                    │
│  - Codex CLI              → OpenAI API                    │
│  - Custom Agent SDK apps → anything                      │
│                                                          │
│  THIS IS WHERE THE LLM LIVES. Paperloom doesn't know     │
│  which one; paperloom doesn't care.                      │
└─────────────────────────┬────────────────────────────────┘
                          │  MCP protocol over stdio
                          │  (identical regardless of host or model)
                          ▼
┌──────────────────────────────────────────────────────────┐
│  PAPERLOOM MCP SERVER                                    │
│  10 tools, pure file operations, no LLM code path.       │
└──────────────────────────────────────────────────────────┘
```

**Consequence:** paperloom's code is identical whether the user runs Claude Sonnet, Gemini Pro, GPT-5, or Qwen3-14B on Ollama. There is no `--model` flag on `paperloom mcp`. There is no `ANTHROPIC_API_KEY` or `OLLAMA_HOST` in paperloom's config. The host agent handles all of that.

### For users who want offline / local models

Recommend one of these agent products in the docs (in `docs/quickstart-local.md`). Do not bundle any of them; do not depend on any of them; just tell users which one to install:

| Host agent | Local model support | Setup difficulty | Notes |
|---|---|---|---|
| **Continue.dev** | Excellent, first-class Ollama | Easy | VSCode/JetBrains extension. Best local-first UX. |
| **Cline** | Excellent, native Ollama config | Easy | VSCode extension. Per-tool confirmation dialogs. |
| **Aider** | Good; `--model ollama/qwen3:14b` | Easy | CLI, git-aware. |
| **OpenCode** | Good, model-agnostic | Medium | Newer, actively developed. |
| **Custom app** | Whatever you build | Hard | Claude Agent SDK or MCP Python SDK. |

**Do not recommend:** running LiteLLM in front of anything (security), or building your own agent (not paperloom's job).

### Model quality tiers and what to expect

This is the honest guidance to put in the docs. The three-question test in `tests/qualitative/three_question_eval.md` is the reference for what "works well" looks like.

| Model class | Examples | Expected quality against three-question test |
|---|---|---|
| **Frontier** | Claude Sonnet 4.5+, GPT-5, Gemini 2.5 Pro | Excellent — this is the reference bar |
| **Strong local** | Qwen3-32B, Llama 3.3-70B (on capable hardware) | Good — noticeable quality gap but usable |
| **Medium local** | Qwen3-14B, Llama 3.1-8B | Acceptable for factual retrieval; weaker at synthesis; use `mode: local` schema |
| **Small local** | Llama 3.2-3B, Qwen3-4B | Retrieval only; do not expect synthesis quality. Use as a fallback. |

Do not promise more than this. Do not hide the tier gap in the README.

### The one accommodation paperloom makes for small models

Add exactly one MCP tool (Section 9) that returns an explicit step-by-step workflow recipe: `describe_workflow`. Small models that would otherwise lose the thread across a multi-step operation call this tool as their first move and follow the recipe verbatim. Frontier models ignore it because CLAUDE.md is already sufficient guidance.

This is the *only* concession paperloom makes to model capability. Everything else stays in the schema.

### Three principles that hold this design together

Any deviation should be checked against them:

1. **Paperloom's value is its schema and its file operations, not its intelligence.** The intelligence lives in the host agent. Adding LLM calls inside paperloom would make the same product MindBase already is, complete with the API-key requirement explicitly rejected in Section 1.
2. **Model capability should affect the schema, not the code.** The tool interface is invariant. Only the CLAUDE.md instructions change per mode (Section 8's "Operating mode"). This keeps the code testable (one code path) while letting the user experience adapt to model capability (via schema).
3. **Small-model support is best-effort, not core.** Frontier models are the primary target because they produce the demo-worthy answers that drive adoption. Small-model support is a graceful degradation path for users who need offline or free operation. Do not compromise the frontier experience to make small models work better.

If you find yourself adding a second CLAUDE.md, a `run_llm` tool, an OpenRouter integration, or a "smart" server-side pipeline, stop. Choose the version that doesn't do those things.

---

## 12. Migration guide from MindBase

For users coming from MindBase (and there will be some — the ecosystem is small), ship a one-command migrator:

```
paperloom migrate-from-mindbase ~/mindbase-data/projects/my-research/
```

Behavior:
1. Create a new paperloom vault at `./<mindbase-project-name>/` (or `--out`).
2. Copy `~/mindbase-data/.../sources/raw/*` → `sources/raw/` (may need ID re-derivation).
3. Copy `~/mindbase-data/.../sources/research/*` → `sources/research/`.
4. Copy `~/mindbase-data/.../sources/contributors/*` → `sources/contributors/`.
5. Copy `context.md`, `README.md`, `logs/` verbatim.
6. Copy `~/mindbase-data/.../index.yaml` → `.paperloom/mindbase-index.yaml` for reference; don't use it (paperloom regenerates indices from disk).
7. Print a summary of what was migrated and what wasn't (e.g. mindbase-specific state in `state/`).

**Do not modify the MindBase source directory.** Always copy, never move.

---

## 13. Tests to write on Day 1

Testing infrastructure is not optional. Ship these tests with the initial implementation.

**`test_vault.py`:**
- `find_vault_root` finds a vault when cwd is inside it.
- Walks up correctly (`sources/research/methods/` → vault root).
- Raises `VaultNotFoundError` outside any vault.
- Handles `--vault-dir` override.

**`test_ingest.py`:**
- Ingest a fixture PDF (small, 2-page test paper checked into `tests/fixtures/`), assert `sources/raw/<id>/paper.md` exists.
- Re-ingest same PDF with `--skip-existing`, assert MinerU is NOT invoked (mock or subprocess-count check).
- Ingest a malformed PDF, assert `PARSE_FAILED.txt` is written and batch continues.
- Ingest 3 PDFs with `--jobs 2`, assert all 3 land + no orphan subprocesses.

**`test_supervisor.py`:** see §6.

**`test_search.py`:**
- Search a fixture vault, assert relevant hits.
- Search with `path_prefix`, assert scoping.
- Search on empty query, assert graceful empty result.

**`test_mcp_tools.py`:** for each of the 10 tools, one happy-path test and one error-path test. `describe_workflow` additionally gets a `list_all` test and an unknown-operation test (must return a helpful message, not raise — a weak local model mistyping an operation name shouldn't crash).

**`test_plugins.py`:**
- Built-in `example_plugin` registers tools successfully.
- Vault-local plugin in `.paperloom/plugins/foo.py` is loaded.
- Plugin with syntax error doesn't crash the server (logs, skips).
- Plugin tool overrides built-in tool with a warning.

**`test_migration.py`:**
- Given a fixture mindbase directory, `migrate-from-mindbase` produces a valid paperloom vault.

**CI (`.github/workflows/ci.yml`):**
- `ruff check`, `ruff format --check`, `mypy src/`, `pytest -n auto`, `pip-audit`, and a grep check that fails if raw `subprocess.Popen` appears outside `supervisor.py`.

---

## 14. README structure (for the public repo)

Follow this order exactly. It's the pattern that works for developer-tool repos and Claude Code will get it right the first time.

1. **One-line tagline** — "Folder-scoped LLM-maintained research wiki. Karpathy's llm-wiki pattern, for scientific papers."
2. **Hero asciinema or GIF** — `paperloom init`, `paperloom ingest ~/pdfs`, `claude "/contribute the AlphaGenome paper"`. 30 seconds.
3. **TL;DR** — three sentences: what it is, how it differs from MindBase and vanilla llm-wiki tools, who it's for.
4. **Credits section, prominently placed** —
   > Paperloom stands on two shoulders:
   > - **[Andrej Karpathy](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)** for the LLM-wiki pattern that this whole project instantiates.
   > - **[Frank Chu's MindBase](https://github.com/frankchu91/mindbase-llm-wiki)** for proving the pattern could be a product, and for the CLAUDE.md schema conventions we borrow and extend.
   >
   > Paperloom differs by being folder-scoped (one KB per directory, no global state), batch-ingest-first (built for corpora of 50-1000 papers), and never requiring an LLM API key of its own.
5. **Quickstart** — three commands.
6. **What it is / isn't** — bullet lists.
7. **Install** — pip + optional extras.
8. **First vault (5 minutes)** — walkthrough.
9. **Architecture** — the 3-layer diagram from CLAUDE.md.
10. **The 10 tools** — table with descriptions.
11. **Plugins** — how to write one, link to docs.
12. **Local / offline models** — model-agnostic architecture, link to `docs/quickstart-local.md`.
13. **Migrating from MindBase** — one command.
14. **Roadmap** — planned plugins, not core features (core is done).
15. **Contributing** — CONTRIBUTING.md link.
16. **License** — Apache-2.0.
17. **Citation** — BibTeX for the repo itself.

---

## 15. What NOT to build (explicit non-goals)

Every line item here has been considered and rejected for v0.1. If a user asks for one of these, point them at a plugin as the answer.

- **Web UI.** The host agent (Claude Code) is the UI. Users who want a browser can point Obsidian at the vault (§16).
- **Multi-user auth, RBAC, team features.** Paperloom is single-user. Multi-user is a completely different product.
- **Vector database, embeddings, semantic search.** Not in core. Ship as an optional plugin later if users demonstrate need. `search` (ripgrep) is enough up to ~500 papers per Karpathy's own experience and MindBase's evidence.
- **Its own LLM router / abstraction over Claude/Gemini/OpenAI/Ollama.** The host agent is the LLM, always — paperloom never calls one itself, not even a local Ollama model. See §11.
- **Automatic wiki writing without user approval.** `create_note` and `append_to_page` are exposed as tools; the agent decides when to call them based on CLAUDE.md's workflow. There is no autonomous background writer.
- **A daemon / persistent server / SaaS.** `paperloom mcp` is stdio-only, one process per client. No `paperloomd`.
- **Vector-based deduplication of methods/concepts.** The agent handles this via `search` + reasoning. Adding fuzzy-matching logic to the tool is scope creep.
- **Automatic BibTeX generation.** Nice, but a plugin (`bibtex_export`).
- **Citation graph enrichment via S2/OpenAlex.** Belongs in ingestion (as an optional step) or a plugin, not the core tool surface.
- **Notion / Roam / Logseq sync.** Never.
- **Windows-first optimizations.** Cross-platform, but tested primarily on Linux/macOS. Windows works via WSL2 recommended in docs.

---

## 16. Obsidian compatibility (a happy accident)

Because paperloom vaults are plain markdown with `[[wikilinks]]`, Obsidian works out of the box:

```
1. Open Obsidian.
2. "Open folder as vault" → your paperloom vault root.
3. Optionally install Dataview plugin — the YAML frontmatter (§8) is Dataview-queryable.
4. Ctrl-G for the graph view.
```

Document this in README under "Optional: browse your vault visually." Do not depend on Obsidian; do not require it.

---

## 17. Implementation order (build in this sequence)

1. `vault.py` + `find_vault_root` + tests. Ship nothing else until this is solid.
2. `supervisor.py` + tests (including kill-9 tests). Ship nothing that spawns subprocesses until this is solid.
3. `cli.py` scaffold with `init` and `version`. Verify template copy works, config loads.
4. `ingest.py` + `paperloom ingest` command. Verify against 2-3 real PDFs from user's collection.
5. `search.py` — ripgrep wrapper first; SQLite FTS5 as follow-up if ripgrep is limiting.
6. `mcp_server.py` — the 10 tools, including `describe_workflow`. Verify with Claude Code by dropping `.mcp.json` in the vault.
7. `plugins/__init__.py` + `example_plugin.py` + tests. Verify loading order.
8. `templates/scientific-paper-vault/CLAUDE.md` — the mode-aware schema (§8's addition). This is documentation and product.
9. `migrate-from-mindbase` — nice-to-have, ship in v0.2 if not ready.
10. `workflows/*.md` (the `describe_workflow` recipes) + `docs/quickstart-local.md` + `tests/qualitative/three_question_eval.md`. *(Redefined by `paperloom_ollama_correction.md` — no longer `plugins/ollama_synth.py`; ships in v0.1 alongside item 6, since `describe_workflow` is now a core tool, not an opt-in plugin.)*
11. Docs, README, examples/. Ship in v0.1.
12. CI, release automation. Ship in v0.1.

**v0.1 (this weekend + next):** items 1-8, 10, 11, 12. Enough to actually use.
**v0.2:** item 9 + first three planned plugins (arxiv_watcher, marp_export, graph_export).
**v0.3+:** plugin ecosystem, community contributions.

---

## Appendix A: mapping of MindBase tools to paperloom equivalents

For users migrating and for the implementer's mental model. Left column is what MindBase exposes; right column is how the same behavior is achieved in paperloom.

| MindBase tool                | Paperloom equivalent                                    |
|------------------------------|---------------------------------------------------------|
| `create_note`                | `create_note` (identical shape)                         |
| `append_to_page`             | `append_to_page` (extended: `guard` param)              |
| `tag_note`                   | `tag_note`                                              |
| `search_wiki`                | `search`                                                |
| `read_wiki_page`             | `read_page`                                             |
| `list_recent`                | `list_pages(subdir="logs", pattern="*.md")` + read      |
| `find_related`               | Plugin (`example_plugin.find_related`) or agent reasoning |
| `mindbase_ingest_file`       | `ingest_pdf` (single) or `paperloom ingest` (batch)     |
| `mindbase_contribute`        | `log_entry(kind="contribute", ...)` + `append_to_page` on contributors/ |
| `mindbase_init_project`      | `paperloom init` CLI + `.paperloom/config.yaml`         |
| `mindbase_validate_structure`| `paperloom doctor`                                      |
| `mindbase_load_project`      | Not needed — vault is derived from cwd                  |
| `mindbase_status`            | `vault_info`                                            |
| `ingest_plan` / `ingest_execute` | Agent workflow via CLAUDE.md, not a tool            |
| `ask_wiki`                   | Agent workflow via CLAUDE.md (`/ask` operation)         |
| `run_wiki_health`            | Agent workflow via CLAUDE.md (`/lint` operation) OR `find_orphans` plugin |
| `semantic_search`            | Not in core; future plugin                              |
| `save_chat_excerpt`          | `create_note` with the excerpt as content               |
| `mindbase_export`            | Just `tar czf out.tgz <vault>` — everything is markdown |
| `mindbase_migrate`           | `paperloom migrate-from-mindbase`                       |
| `find_orphans` / `find_contradictions` / `find_gaps` | Agent computes via `search` + `list_pages` + reasoning, OR use `example_plugin` |

Everything MindBase does that isn't in this table is either: (a) a smart feature that required an LLM API key and is now handled by the host agent, or (b) UI-layer functionality that doesn't apply to a CLI-first tool. Nothing is lost that the user of paperloom-with-Claude-Code will miss.

---

## Appendix B: minimum-viable Day 1

The single shortest path to a working paperloom, in commands the implementer can execute:

```bash
# 1) Bootstrap the repo
mkdir paperloom && cd paperloom
uv init --package
git init

# 2) pyproject.toml — see §4
$EDITOR pyproject.toml

# 3) Implement the modules in the order of §17

# 4) Install into an isolated env
uv sync
uv pip install -e .

# 5) Create the reference vault
mkdir -p ~/test-vault && cd ~/test-vault
paperloom init --template scientific-paper-vault

# 6) Ingest a few PDFs
paperloom ingest ~/Downloads/papers/

# 7) Register with Claude Code
cat > .mcp.json << 'EOF'
{ "mcpServers": { "paperloom": { "command": "paperloom", "args": ["mcp"] } } }
EOF

# 8) Use it
claude "/contribute sources/raw/2301.08243"
claude "What does my wiki know about JEPA?"
```

If those eight steps produce useful behavior — and they will, because the intelligence is Claude Code's and the schema is your CLAUDE.md — v0.1 is done. Everything else is polish, plugins, and adoption.

