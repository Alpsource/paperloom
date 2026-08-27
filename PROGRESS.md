# Paperloom — build progress

Tracks §17 ("Implementation order") of `paperloom.md` as it's actually
built, item by item. Not part of the shipped product — just our own working
log so the sequence of what's done and verified doesn't only live in chat
history.

---

## Item 1 — `vault.py` + `find_vault_root` + tests

**Status: done.** Verified natively on Windows (`pytest tests/test_vault.py -v`, 5/5 passed).

**Files:**
- `pyproject.toml`, `README.md` (placeholder), `.gitignore`,
  `src/paperloom/__init__.py` — minimal scaffold needed to make the package
  installable/importable.
- `src/paperloom/vault.py` — the whole point of vault discovery: every
  paperloom command needs to find "the vault" from wherever the user's
  shell happens to be sitting. `find_vault_root()` walks up from the
  current directory (or an explicit `start`) checking each ancestor for a
  `.paperloom/` marker folder, and returns the first one found. Raises
  `VaultNotFoundError` if it walks all the way to the filesystem root
  without finding one. Also takes an optional `vault_dir` override — the
  hook the future CLI's `--vault-dir` escape hatch will call into, so you
  can point at a vault directly instead of relying on cwd.
- `tests/test_vault.py` — found-at-root, walks-up-from-nested-subdir,
  raises-outside-any-vault, and both directions of the `vault_dir` override.

---

## Item 2 — `supervisor.py` + kill-9 tests

**Status: done.** Verified in WSL2 (Ubuntu 24.04) per §15's own recommendation
— native Windows can't express the graceful-SIGTERM tests the same way,
since `os.kill(pid, SIGTERM)` there hard-kills via `TerminateProcess`
without running a Python handler. `pytest tests/test_supervisor.py -v`,
4/4 passed; `tests/test_vault.py` re-confirmed passing there too (9/9 total).

**Files:**
- `src/paperloom/supervisor.py` — the module every future subprocess call
  in paperloom (MinerU, git, ...) must go through instead of calling
  `subprocess.Popen` directly. A `Supervisor` singleton tracks every spawned
  process (as weakrefs) and guarantees they all get killed on any exit path:
  normal completion, `KeyboardInterrupt`, `SIGTERM`/`SIGINT`/`SIGHUP`, an
  unhandled exception, or the process itself getting hard-killed. Two
  cleanup mechanisms layer on top of each other:
  - **Graceful path** (`atexit` + signal handlers → `shutdown()` →
    `_terminate()`): on POSIX, sends `SIGTERM` to the whole process group
    (`os.killpg`, since children are spawned with `start_new_session=True`
    so MinerU's own PyTorch/CUDA descendants share the group), waits 5s,
    escalates to `SIGKILL`. On Windows, sends `CTRL_BREAK_EVENT` /
    `.kill()`. This only works if the parent process gets to run code while
    it dies — so it does nothing against `os._exit`, `SIGKILL`, or an OOM
    kill.
  - **Kernel-level path** (`PR_SET_PDEATHSIG`, added beyond §6's literal
    skeleton — a small `ctypes`→libc `prctl()` call set as a pre-exec hook,
    Linux-only): tells the kernel to `SIGKILL` the child the instant *its*
    parent (the paperloom process) dies, for any reason at all, without the
    parent needing to execute any cleanup code. This is what actually
    satisfies §1's "OOM/power-off must never leave orphans" invariant, and
    it's the only thing that makes the `os._exit(1)` test pass. No-ops
    silently outside Linux.
- `tests/fixtures/supervisor_harness.py` — a standalone script that plays
  "the parent process under test," since pytest obviously can't SIGTERM
  itself. Run as a real subprocess with a `mode` argument (`simple` /
  `chain` / `many`); each mode spawns some children via
  `paperloom.supervisor.spawn()`, reports their pids back to the test via a
  JSON file, then either blocks (waiting to be killed) or, for `many`,
  deliberately hard-exits itself via `os._exit(1)`.
- `tests/test_supervisor.py` — the 4 kill-9 cases from §6: SIGTERM the
  harness → child dies; exception inside `with child(...)` → child still
  terminated; SIGTERM the harness → grandchild (spawned outside paperloom's
  own supervisor, simulating MinerU spawning its own workers) also dies,
  proving process-group kill actually propagates; `os._exit(1)` bypassing
  atexit → all 10 children still die, proving `PR_SET_PDEATHSIG` works.

**Bug found & fixed while building item 3** (see below): `signal.SIGHUP`
doesn't exist as an *attribute* on Windows, so referencing it in a tuple
literal raised `AttributeError` before the `try/except` around
`signal.signal()` ever ran — the guard in §6's given code only covered the
call, not the attribute lookup. Fixed by looking signals up via
`getattr(signal, name, None)` and skipping missing ones. This didn't
surface during item 2 because everything was tested in WSL2 (Linux), where
`SIGHUP` exists.

---

## Item 3 — `cli.py` scaffold (`init` + `version`)

**Status: done.** Verified natively on Windows (no signal/kill-9 behavior
involved) — `pytest tests/test_cli.py -v`, 5/5 passed. Re-confirmed items 1
& 2 still pass in WSL2 after the SIGHUP fix (9/9). Manually ran
`paperloom init` against a real scratch directory and inspected the
resulting tree + `config.yaml` by hand.

**Files:**
- `src/paperloom/templates/scientific-paper-vault/` — the directory tree
  `paperloom init` copies into a new vault: `README.md` (user-editable
  placeholder), empty `context.md`/`index.md` (the agent fills these in
  later), `log.md` (header only), `sources/{research,contributors,raw}/`
  and `artifacts/`/`logs/` (each just a `.gitkeep` so git tracks the empty
  dir). `CLAUDE.md` here is a **placeholder** with a visible TODO marker —
  the real schema from §8 is explicitly item 8, not item 3; `init` just
  needed something real to copy so the CLI could be built and tested now.
- `src/paperloom/cli.py` — the Typer app that `pyproject.toml`'s
  `paperloom = "paperloom.cli:app"` entry point points at. Two commands so
  far:
  - `init [DIR] [--template ...] [--force]` — copies the template tree into
    `DIR` (refusing to clobber existing files unless `--force`), writes
    `.paperloom/config.yaml` (records which template, when, and which
    paperloom version created it — this exact schema isn't dictated by the
    spec, just the file's existence, so I kept it to the minimum `init`
    itself needs), then runs `git init` in `DIR` *through
    `paperloom.supervisor.spawn`* (not raw `subprocess.Popen` — this is the
    hard rule from §6, and `cli.py` is the first module to actually spawn
    anything) if it isn't already a repo. Warns and continues if `git`
    isn't on PATH rather than failing vault creation outright.
  - `version` — prints paperloom's own version, the running Python version,
    and installed versions of `typer`/`rich`/`PyYAML`/`pydantic`.
- `tests/test_cli.py` — via `typer.testing.CliRunner`, always against a
  `tmp_path` target (never the paperloom source repo itself, so tests can
  never accidentally `git init` this repo): template files all land where
  expected, `config.yaml` parses with the right keys, `.git/` gets created,
  a second `init` on the same dir without `--force` fails cleanly, the same
  with `--force` succeeds, and `version` prints the right strings.

**Known gap, not yet relevant:** the template directory is only readable
right now because `pip install -e` links straight back to the source tree.
A real wheel build would need `[tool.hatch.build]` package-data config to
bundle non-`.py` files — that belongs with item 12 (release automation),
not here.

---

## Item 4 — `ingest.py` + `paperloom ingest`

**Status: done.** `pytest tests/test_vault.py tests/test_cli.py
tests/test_ingest.py -v` on native Windows, 14/14 passed (re-run 8x back to
back for the new tests specifically to shake out flakiness — see the bug
note below). Real end-to-end verification in WSL2 against 3 of your actual
papers (I-JEPA `2301.08243`, Graph-JEPA `2309.16014`, S-JEPA `2403.11772`,
copied from `mindbase-data`, originals untouched) also passed — real
`mineru[core]` (GPU-accelerated via the RTX 4050 visible from WSL2),
real `paper.md`/`meta.json`/`images/` output inspected by hand. This surfaced
three real bugs the mocked tests couldn't catch — see below.

**Two decisions made with you up front:**
- Added `pypdf` (beyond §4's literal dependency list) so `compute_id()` can
  read page-1 text — without it, your real PDFs (named by title, not arXiv
  ID) would all fall back to opaque sha256 IDs instead of their actual
  arXiv numbers.
- Installing real MinerU in WSL2 (not native Windows) since C: only has
  32GB free vs. WSL2's 948GB, and MinerU pulls PyTorch + several GB of model
  weights.

**Files:**
- `pyproject.toml` — added `pypdf>=4.0`.
- `src/paperloom/ingest.py` — the batch pipeline from §7:
  - `compute_id()` — arXiv regex against filename, then page-1 text (via
    `pypdf`), then DOI regex, then `sha256[:12]` fallback. Returns a small
    `ComputedId` (id / arxiv_id / doi) rather than a bare string, so
    `meta.json` can record arxiv_id and doi as separate fields from `id`
    (a DOI-derived id is a slugified version, not identical to the raw DOI).
  - `ingest_one()` — the per-paper pipeline: skip if already parsed →
    copy PDF into `sources/raw/<id>/paper.pdf` (copy, never move) → run
    `mineru` through `paperloom.supervisor.spawn` (never raw `Popen` — this
    is the first module besides `cli.py`'s `git init` to actually spawn
    anything) → on failure, write `PARSE_FAILED.txt` and return a "failed"
    result without raising, so a batch survives one bad PDF → on success,
    move the parsed markdown into place, build `meta.json`, best-effort
    enrich via the Semantic Scholar API (any failure — network, 404, rate
    limit — silently ignored, no key needed), append a log line.
  - `ingest_folder()` — globs the folder, drives a Rich progress bar,
    sequential when `jobs<=1` or a `ThreadPoolExecutor` when `jobs>1`
    (I/O-bound waiting on subprocesses, so threads suffice — no
    multiprocessing needed). Converts an interrupt into a small
    `IngestAborted(completed, total)` exception so the CLI can print
    "aborted after N/M" — `supervisor`'s own `SIGINT` handler has already
    killed any in-flight MinerU processes by the time this is caught.
    A disk-full `OSError` aborts the batch cleanly.
- `src/paperloom/cli.py` — new `ingest FOLDER [--pattern] [--jobs]
  [--skip-existing/--no-skip-existing]` command, prints a
  succeeded/skipped/failed summary, exits 130 on interrupt.
- `tests/fixtures/_generate_fixtures.py` — one-off generator (not a test
  itself) that hand-writes minimal valid PDF byte structure (objects, xref
  table, trailer) with real extractable text — no PDF-writing dependency
  needed just for tiny fixtures. Produces the three committed fixture PDFs.
- `tests/fixtures/toy-paper.pdf` / `toy-paper-arxiv.pdf` / `toy-paper-2.pdf`
  / `malformed.pdf` — the fixtures themselves.
- `tests/fixtures/fake_mineru.py` — a stub CLI standing in for real MinerU
  in tests: writes the expected output markdown and exits 0, or exits
  nonzero without writing anything when the input bytes don't start with
  the `%PDF` magic header (simulating a parser crash on bad input).
- `tests/test_ingest.py` — the 4 cases from §13, all against `fake_mineru`
  (real `mineru` is never touched by automated tests): paper.md + meta.json
  land correctly; skip-existing genuinely skips (no re-invocation); a
  malformed PDF fails cleanly while the batch continues past it; 3 PDFs
  with `--jobs 2` all land.

**Bug found while writing the fixtures, fixed before it shipped:**
`fake_mineru.py`'s first draft detected "this PDF should fail" by checking
whether `"malformed"` appeared in the input filename — but `ingest_one`
always copies the source PDF to a fixed name (`paper.pdf`) before invoking
MinerU, so that filename check could never actually match anything.
Switched to checking file *content* (missing the `%PDF` magic bytes)
instead, which is also a more realistic stand-in for how a real parser
would actually fail.

**Flaky test found and resolved (not an `ingest.py` bug):** the `--jobs 2`
test originally also asserted an exact MinerU invocation count via a shared
call-log file that concurrent `fake_mineru` *subprocesses* each appended a
line to. That file-append race is genuinely flaky under concurrent
processes on Windows (occasionally lost a line, caught it failing 1-in-5
runs). §13 only requires "assert all 3 land + no orphan subprocesses" — it
never asked for an exact invocation count — so the assertion was dropped
rather than working around the race in the shared log file. Orphan-freedom
for this item is structural, not signal-based: every `ingest_one` call
`.wait()`s on its subprocess (via `proc.communicate()`) before returning,
whether run sequentially or inside a thread-pool worker, so nothing is left
running once `ingest_folder` returns — the kill-9 guarantees for the
*interrupted* case remain `supervisor.py`'s job, already covered by item 2.

**Three real bugs found only by running against actual MinerU (mocked
tests structurally can't catch these — they're about the real dependency's
current CLI, not paperloom's own logic):**
1. **Wrong CLI flags.** §7 specifies `--formula-enable true --table-enable
   true`; the installed `mineru` 3.4.5 doesn't have those flags at all —
   they're `-f`/`--formula` and `-t`/`--table` now. Passing the old names
   didn't get rejected outright; it got past argument parsing and crashed
   deep inside MinerU's own request-building code
   (`TypeError: dict() got multiple values for keyword argument
   'formula_enable'`) after already spinning up a model server — a strange
   enough failure mode that it took a manual `mineru --help` and a direct
   manual invocation to actually diagnose. Fixed by switching to `-f`/`-t`.
2. **Wrong output subdirectory assumed.** §7 says MinerU writes to
   `<outdir>/<basename>/auto/<basename>.md`; the installed version's
   default backend (`hybrid-engine`) actually writes to
   `<basename>/hybrid_auto/<basename>.md`. Rather than hardcode a specific
   backend's folder name (which could change again), `ingest_one` now
   globs `mineru_out/**/<basename>.md` and takes whatever it finds — robust
   to backend/version differences instead of tied to one snapshot of
   MinerU's CLI.
3. **Dangling image links.** MinerU writes extracted figures into an
   `images/` folder sitting next to the markdown; §7's "move the .md, clean
   up mineru-out/" instructions say nothing about them, and the original
   implementation followed that literally — deleting `mineru-out/`
   (images included) right after pulling out just the `.md` file. Every
   `![](images/...)` reference in the "immutable, source of truth"
   `paper.md` ended up a dead link. Confirmed on I-JEPA's real output, then
   fixed by moving the sibling `images/` folder alongside the markdown
   before cleanup (verified by force-re-ingesting S-JEPA: all 8 figures
   landed in `sources/raw/2403.11772/images/`). `fake_mineru.py` and
   `test_ingest_one_creates_paper_md_and_meta` were both updated to cover
   this so a regression here would be caught by the fast mocked suite too,
   not just real E2E runs.

**Also observed, not a bug — noted for later:** Semantic Scholar enrichment
succeeded for 2 of the 3 real papers (Graph-JEPA and S-JEPA got full
authors/year/venue/n_refs; I-JEPA's came back empty). Per §7's own
"best-effort... any failure ignored" contract this is expected/acceptable
behavior, not something to chase down now.

**Environment note for future WSL2 sessions:** invoking `wsl -d Ubuntu --
bash -c '...'` from this Windows-side session has two quirks worth knowing
up front — (1) shell variable assignments made *inside* an inline `-lc`/`-c`
string don't reliably persist for later reference in the same string
(root cause unconfirmed — possibly a WSL/git-bash argument-passing
interaction); write an actual `.sh` file and run `bash /path/to/script.sh`
instead of inlining multi-statement logic. (2) When doing that, prefix the
call with `MSYS_NO_PATHCONV=1` — otherwise Git Bash's automatic path
conversion mangles `/mnt/c/...`-style arguments (rewrites them relative to
the Git installation root) before `wsl.exe` ever sees them.

---

## Item 5 — `search.py` (ripgrep wrapper)

**Status: done.** `pytest tests/test_search.py -v` on native Windows, 3/3
passed; full native suite (excluding the WSL2-only `test_supervisor.py`),
17/17 passed. Manual sanity check via `paperloom search` in a real scratch
vault confirmed both a real hit and a clean "No results." for a term that
doesn't appear anywhere.

**Environment gap found and resolved before any code was written:**
neither native Windows nor WSL2 had a genuine `rg` binary on `PATH`. This
session's own shell has `rg` defined as a Claude-Code-injected shell
*function* that shells out to Claude's own bundled ripgrep — invisible to
`which`, and irrelevant to the real product, since `subprocess.Popen(["rg",
...])` from Python does plain PATH lookup and bypasses shell functions
entirely (confirmed this would fail before writing any code). Installed
real ripgrep via `winget install BurntSushi.ripgrep.MSVC` (fast, official,
no `sudo` round-trip) and confirmed both a direct binary check and a real
Python `subprocess` call resolve it correctly. `search.py` also has its own
`RipgrepNotFoundError` with an actionable message, for real end users who
don't have `rg` installed at all.

**Files:**
- `src/paperloom/search.py`:
  - `SearchHit` — a plain dataclass (`path`/`line`/`snippet`/`score`), not
    `pydantic.BaseModel`. §9's MCP tool skeleton defines its own pydantic
    `SearchHit`, but that's specifically an MCP-boundary concern belonging
    to `mcp_server.py` (item 6, not built yet) — keeping this module free
    of a `fastmcp`/`pydantic` import it doesn't otherwise need.
  - `hybrid_search(vault_root, query, top_k=10, path_prefix=None)` — the
    exact function name/signature §9's skeleton already calls
    (`search.hybrid_search(root, query, top_k=top_k,
    path_prefix=path_prefix)`), so item 6 can wire straight into it later.
    Runs `rg --json --fixed-strings <query> <search-root>` through
    `paperloom.supervisor.spawn` (never raw `Popen` —§6's rule has no
    carve-out for short-lived subprocesses either). `--fixed-strings`:
    queries are literal substrings, not regex, which is the right default
    for searching prose/terms rather than power-user pattern matching.
    `path_prefix` scoping is just ripgrep's own path argument
    (`vault_root / path_prefix`) — no extra filtering needed, and `.git/`/
    `.paperloom/` are both skipped automatically since ripgrep ignores
    dot-directories by default. An empty/whitespace query short-circuits to
    `[]` before ever invoking `rg` (an empty pattern would otherwise match
    *every* line). Scoring is a simple per-file match-count heuristic — no
    real relevance model, consistent with §15 explicitly keeping
    embeddings/semantic search out of core.
- `src/paperloom/cli.py` — new `search QUERY [--top 10]` command per §5,
  printing `path:line: snippet` (or "No results.") via Rich.
- `tests/test_search.py` — the 3 cases from §13, against a small vault tree
  written inline via `tmp_path` (plain `.md` files, no checked-in fixture
  vault needed): a real hit lands with the right path/line; `path_prefix`
  scoping genuinely excludes a same-term match outside the scoped
  directory; an empty query returns `[]` cleanly, including when paired
  with a nonexistent `path_prefix` (proving it's a real short-circuit, not
  just an empty ripgrep result).

**Real bug found and fixed by the test suite itself (not by manual
inspection this time):** the first draft returned `str(Path(...).relative_to(vault_root))`
for each hit's `path`, which on Windows produces backslash-separated paths
(`sources\research\i-jepa.md`). Every other path convention in this
codebase and in the spec itself (frontmatter fields, `[[wikilinks]]`,
`raw:` references) uses forward slashes — a Windows user's search results
would otherwise be subtly incompatible with the rest of the vault. Fixed
with `.as_posix()` instead of bare `str()`.

**Cross-platform gap closed same-day:** the user asked whether everything
built so far actually works on Linux, not just "should work by
construction." `search.py` was the one piece only run on native Windows —
installed real `ripgrep` in WSL2 too (`sudo apt install ripgrep`, run by
the user directly since `sudo` needs a password this session can't supply)
and ran the *entire* suite there: 21/21 passed on real Linux (WSL2 is a
genuine Linux kernel, not an emulation layer). Combined with item 2's
kill-9 tests and item 4's real MinerU run already being WSL2-verified,
every module has now actually executed successfully on both Windows and
Linux, not just Windows with Linux code paths assumed correct.

---

## Item 6 — `mcp_server.py` (the 9 tools)

**Status: done.** `pytest tests/test_mcp_tools.py -v`: 19/19 passed
(18 required by §13 — happy+error per tool × 9 — plus one extra covering
the `human_edited` guard refusal). Full suite: 36/36 native, 40/40 in WSL2
(real Linux). Real protocol-level verification also done: ran `paperloom
mcp` as an actual subprocess and drove it over genuine stdio MCP transport
— the same transport Claude Code itself uses — issuing real `vault_info`,
`create_note`, and `search` calls and confirming the file actually landed
on disk and was found again through a real ripgrep round-trip. A scratch
vault with a real `.mcp.json` was left at
`<scratchpad>/mcp-verify-vault/` in case you want to point your own
separate Claude Code session at it directly (note: its `.mcp.json` uses
`"command": "paperloom"` per §9's exact config — that only resolves if
`paperloom` is on `PATH` for whatever session opens it, e.g. this repo's
venv is active or a global install exists).

**Two things flagged before building, both played out as expected:**
- `fastmcp` really had moved to `3.4.7` (from the `2.x`-era skeleton in
  §9) — `@mcp.tool` (bare decorator) still works unchanged; the test client
  API (`fastmcp.Client`, `call_tool`, `.data`/`.structured_content`) needed
  a quick smoke-test script to nail down before writing real tests, same
  as MinerU's and ripgrep's real-vs-assumed API gaps in items 4-5.
- Plugin loading (§10, item 7) genuinely isn't wired in yet — left a
  clearly marked comment in `mcp_server.py` where `paperloom.plugins.load_all`
  will hook in, and `vault_info`'s `plugins_loaded` stays `[]` until then.

**Files:**
- `src/paperloom/vault.py` (extended, not a new module — §2 already
  assigns "path resolution, frontmatter I/O" here): `resolve_path()`
  (traversal guard — rejects any path that resolves outside `vault_root`),
  `check_writable()` (the "refuses to write outside sources/, artifacts/,
  or logs/" boundary from §8/§9), `read_frontmatter()`/`write_frontmatter()`
  (split/join a page's `---`-delimited YAML block and body), and
  `append_log_line()` (create-with-header-then-append, shared by both
  `ingest.py`'s log lines and the new `log_entry` tool).
- `src/paperloom/ingest.py` — additive `id_override` param on `ingest_one`
  (backs `ingest_pdf`'s `id_hint`; existing callers/tests untouched since
  it defaults to `None`); `_append_log` now delegates to
  `vault.append_log_line` instead of duplicating the same logic.
- `src/paperloom/mcp_server.py` — `FastMCP("paperloom")` with all 9 tools:
  `search` (thin wrapper over item 5's `hybrid_search`), `read_page`,
  `list_pages`, `create_note`, `append_to_page` (section-targeted insertion
  finds the named H2/H3 and inserts before the next same-or-shallower
  heading; if the section doesn't exist yet, appends a new one at the end
  rather than hard-failing — §9 doesn't specify this case, documented in
  the tool's own docstring), `tag_note`, `log_entry`, `ingest_pdf`, and
  `vault_info`. Every tool returns a Pydantic model, including the several
  §9 shows as a bare `-> dict` — consistent with the spec's own "every tool
  returns Pydantic-typed JSON" principle.
- `src/paperloom/cli.py` — new `mcp` command (§5), blocking on stdio.
- `tests/test_mcp_tools.py` — happy+error per tool via `fastmcp.Client`
  talking to the server through the real MCP protocol layer (not calling
  the underlying Python functions directly).
- `pyproject.toml` — added `pytest-asyncio` (dev) + `asyncio_mode = "auto"`,
  needed once `test_mcp_tools.py`'s tests became `async def` (MCP calls are
  inherently async).

**Real security-relevant bug found while designing the log_entry test, not
by writing the implementation carefully enough the first time:** the
`log_entry` tool built its target path as plain `root / rel` instead of
routing it through `resolve_path`'s traversal guard — meaning a
`contributor` argument like `"../../../evil"` could have written a log file
outside the vault entirely. Every other write tool already went through
`resolve_path`; this one didn't, because thinking through what the tool
"should" test caught what reading the code alone hadn't. Fixed, with a test
that confirms it now raises rather than escaping — this is also a reminder
of why §13's "one error path per tool" requirement earns its keep beyond
minimum compliance.

---

## Item 7 — `plugins/__init__.py` + `example_plugin.py`

**Status: done.** `pytest tests/test_plugins.py -v`: 4/4 passed (the exact
§13 list). Full suite: 40/40 native, 44/44 in WSL2 (real Linux) — one
pre-existing item-6 test needed a one-line update once real plugin loading
replaced the hardcoded `plugins_loaded: []` (see below). Real protocol-level
verification: ran `paperloom mcp` as an actual subprocess against a vault
with a genuine `.paperloom/plugins/greeting.py`, over real stdio — the
vault-local tool was listed, callable, returned the right result, and
`vault_info` correctly reported `['example_plugin', 'vault:greeting']`.

**A genuinely useful discovery, found by testing FastMCP directly before
writing any override-handling code:** §10's `load_all()` skeleton has *no*
logic at all for "warn on override, don't silently shadow" — but FastMCP
3.4.7 already does this natively. Registering a second tool under a name
that already exists logs `WARNING Component already exists: tool:<name>@`
and the *second* registration wins (confirmed directly: two `@mcp.tool`
defs with the same name, the later one's behavior is what actually runs).
So §10's stated precedence — built-in → third-party overrides it →
vault-local overrides both — falls straight out of *loading order* with
zero custom override-tracking code needed here. That logger doesn't
propagate to root (`fastmcp`'s own logger sets `propagate = False`), which
only matters for testing it — found by reading FastMCP's
`utilities/logging.py` directly rather than guessing, since a root-logger
capture attempt silently saw nothing on the first try.

**A real gap in the given skeleton, found by checking it against §13's own
test list before writing code:** the skeleton wraps only the *third-party*
entry-points loop in `try/except`; the built-in and vault-local loops had
no error handling at all, which would have crashed `load_all()` entirely
on a syntax-error plugin — directly contradicting §13's "logs, skips."
Fixed by wrapping all three loading paths in the same log-and-continue
pattern the skeleton only showed for one of them.

**Files:**
- `src/paperloom/plugins/__init__.py` — `load_all(mcp) -> list[str]`:
  built-in (`plugins/*.py`, this directory) → third-party (`entry_points(group="paperloom.plugins")`)
  → vault-local (`<vault>/.paperloom/plugins/*.py`, skipped gracefully if
  no vault is in scope). Every path now catches and logs per-plugin
  failures to stderr (`[paperloom] plugin <name> failed to load: <e>`)
  instead of aborting the whole call.
- `src/paperloom/plugins/example_plugin.py` — `word_count` and
  `find_orphans`, copied per §10; both call `find_vault_root()` at call
  time, not registration time, so built-in loading never needs a vault.
- `src/paperloom/mcp_server.py` — the item-6 placeholder comment replaced
  with the real wiring: `_loaded_plugins = load_all(mcp)` at module level
  (runs once, when `paperloom mcp` actually starts with cwd already at the
  vault root — correct timing for real usage), and `vault_info()` now
  returns that list instead of a hardcoded `[]`.
- `tests/test_mcp_tools.py` — one-line fix: `test_vault_info_happy`
  asserted `plugins_loaded == []`, true only because the field was
  hardcoded at the time item 6 was written; now asserts
  `== ["example_plugin"]`, matching real behavior.
- `tests/test_plugins.py` — the 4 cases from §13, each calling
  `paperloom.plugins.load_all` against a **fresh `FastMCP()` instance**,
  not the shared `mcp_server.mcp` singleton (whose plugin loading runs once
  at first import — incompatible with each test wanting its own
  vault/plugin-directory setup): built-in loads successfully; a real
  `.paperloom/plugins/foo.py` loads and its tool is callable; a syntax-error
  plugin alongside a valid one doesn't crash the batch and the valid one
  still loads; a vault-local plugin overriding a built-in tool name shows
  the warning (via `caplog` pointed at FastMCP's actual local-provider
  logger) and the override's behavior is what actually runs.

Third-party entry-points loading is implemented per §10 but has no
dedicated test — §13's four required cases don't ask for one, and standing
up a real installed package with declared entry points just to test the
same loop body the built-in/vault-local tests already exercise wasn't
worth the added weight.

---

## Item 8 — the real `CLAUDE.md` schema

**Status: done.** `pytest tests/test_cli.py tests/test_templates.py -v`,
6/6 passed; full native suite 41/41. Unlike every prior item, no design
decisions here — §8 says "copy this verbatim," so that's what happened,
re-read directly from `paperloom.md` lines 352-556 (not from memory of the
original full read many turns ago) and diffed byte-for-byte against the
written file to confirm — the only difference found was the source
document's own outer ` ```` ` fence delimiter closing *its* code block,
which was never part of the actual CLAUDE.md content.

**Files:**
- `src/paperloom/templates/scientific-paper-vault/CLAUDE.md` — replaced
  item 3's placeholder with §8's real schema: the maintainer-role framing
  ("you do NOT write research; you maintain the substrate"), domain focus,
  the three layers (`sources/raw/` immutable, `sources/research/` agent-owned,
  `sources/contributors/` daily logs), the provenance discipline (every
  claim needs a `[[raw:...]]` anchor or one of three explicit exception
  markers), all five page shapes (paper/method/dataset/concept/synthesis),
  the four operations (`/contribute`, `/ask`, `/lint`, `/rebuild-context`),
  available tools, style rules, and "what compounds."
- `tests/test_templates.py` (new) — a lightweight regression guard rather
  than duplicating the whole schema into an assertion: confirms the
  item-3 placeholder's `TODO` marker is gone and a handful of anchors that
  only exist in the real schema (`/contribute`, `{{common-knowledge}}`,
  etc.) are present.

---

## Items 11 & 12 — Docs/README/examples + CI/release automation

**Status: done.** Full suite: 41/41 native, 45/45 real Linux (WSL2), both
via `pytest -n auto` matching CI's exact invocation. `ruff check`, `ruff
format --check`, and `mypy src/` all pass clean against the real codebase
(not just written and hoped to work — see the real bugs found below).
`pip-audit` clean after upgrading the handful of `mkdocs-material`
transitive deps it flagged. `mkdocs build --strict` succeeds. `git init`
run on the source repo (no commits, per your call).

**Decisions made with you up front:** `git init`-only (no commits, per my
standing instruction to only commit when asked); the example vault built
via genuine re-ingestion of 5 real papers rather than hand-waved stand-in
raw content; GitHub identity confirmed as `Alpsource/paperloom`; and,
after the vault was built, a follow-up call to strip the actual `paper.pdf`
files from the shipped example (keeping `paper.md`/`meta.json`/`images/`)
to avoid redistributing third-party arXiv PDFs in the public repo.

### The real ingestion saga

Building `examples/ml-robotics-vault/` meant actually running 5 real
papers (S-JEPA, Graph-JEPA, GVP-GNN, VL-JEPA, Brain-JEPA — picked small,
copied from `mindbase-data`, originals untouched) through the real
pipeline again. 4 landed cleanly in the first ~20 minute run; the 5th got
interrupted **twice** by a background task getting killed mid-run, with no
error in the logs and no hung processes afterward — genuinely puzzling
until you asked me to actually debug it rather than just retry blindly.

**What debugging it found:** a trivial 20-second `setsid nohup ... &
disown` test *inside* WSL2 didn't survive either, which ruled out
"WSL-internal session/nohup" as the relevant layer — the real dependency
turned out to be the wrapping `wsl.exe` connection from Windows staying
alive, which is exactly what the Bash tool's own `run_in_background: true`
mechanism (not any WSL-internal trick) had been providing successfully in
every earlier long-running job in this project. The task-notification
text itself — "may have been running when the previous Claude Code process
exited" — combined with concrete evidence (the background-task output path
literally switched to a new session ID between calls) pointed to *this
Claude Code session's own process* having restarted mid-run during a very
long session, not anything wrong with MinerU, paperloom's ingestion code,
or WSL2 itself. Retrying with the same `run_in_background: true` mechanism
that had already worked 4 times succeeded on the third attempt. Net
effect: none, since `--skip-existing` made every retry cheap (only the one
remaining paper, ~7 min with the model already cached) — but worth
recording here since it's the kind of environment quirk that'll recur on
any sufficiently long future session.

### Docs, README, examples (item 11)

- **`README.md`** — rewritten from item 3's placeholder, following §14's
  exact 17-section order (tagline through BibTeX citation), including the
  credits section verbatim and a small mermaid diagram of the three-layer
  architecture. The "hero GIF" slot is an honestly-labeled terminal
  transcript rather than a real recording, since I can't record a screen
  capture.
- **`docs/`** — `index.md`, `quickstart.md`, `schema.md`, `plugins.md`,
  `credits.md`, plus a minimal `mkdocs.yml` (material theme) — verified
  with a real `mkdocs build --strict`, which caught two real broken
  relative links (`../README.md` doesn't exist inside mkdocs's `docs_dir`)
  before they shipped.
- **`examples/ml-robotics-vault/`** — a real `paperloom init`'d vault with
  all 5 papers actually ingested (see above), plus hand-written
  `sources/research/` pages covering every one of §8's five page shapes:
  5 paper pages, 2 method pages (`jepa.md` — deliberately synthesized from
  what the 4 downstream JEPA papers say about the framework, since the
  actual originating papers aren't ingested in this vault, with that gap
  documented on the page itself rather than papered over —
  `geometric-vector-perceptron.md`), 1 concept page, and 1 synthesis page
  comparing how each JEPA paper adapts masking for its modality. Also
  populated `context.md` (per the `/rebuild-context` spec), `index.md`, a
  contributor daily-log entry, and a `/contribute`-style log line
  alongside the real `INGEST` lines the pipeline itself already wrote.
- **`LICENSE`** (Apache-2.0) and **`CHANGELOG.md`** — both listed in §2's
  repo layout but never created; needed so the README's own License
  section points at something real. **`CONTRIBUTING.md`** — also added
  rather than leaving the README's "see CONTRIBUTING.md" as a dead link.
- **`pyproject.toml`** — fixed a real bug found while adding
  `[project.urls]`: placing that table before the still-bare `dependencies
  = [...]` key would have silently nested `dependencies` inside
  `[project.urls]` instead of `[project]` (valid TOML, wrong meaning) —
  caught by parsing the file with `tomllib` immediately after editing,
  not by CI later. Also fixed a stale `authors = [{name = "your-name"}]`
  placeholder from item 1's bootstrap.

### CI, release automation (item 12)

- **`.github/workflows/ci.yml`** — `ruff check`, `ruff format --check`,
  `mypy src/`, `pytest -n auto`, `pip-audit`, and the `subprocess.Popen`
  guardrail from §13, all on `ubuntu-latest` only (§15's own "tested
  primarily on Linux/macOS" — `test_supervisor.py` specifically needs real
  POSIX `SIGTERM` delivery native Windows can't provide).
- **`.github/workflows/release.yml`** — `uv build` + PyPI trusted
  publishing (OIDC, `pypa/gh-action-pypi-publish`) on a `v*` tag push.
  Inert until a real tag hits a real GitHub remote with PyPI trusted
  publishing configured on your end — verified by YAML syntax/structure
  only, no live run, no publish, ever, without explicit authorization.
- **Real bugs found by actually running what CI runs, not just writing the
  YAML:**
  1. `ruff check` (once given a sane `[tool.ruff]` config instead of this
     ruff version's much broader real defaults) found 7 genuine issues —
     5x missing `raise ... from` in `cli.py`'s exception handlers, one
     `datetime.utcnow()`-era pattern ruff auto-fixed to `datetime.UTC`,
     one truly-unused import. Fixed all 7.
  2. `mypy src/` on Windows flagged `os.killpg`/`signal.SIGKILL` as
     missing — correctly, since those don't exist in Windows' typeshed
     stubs. Pinning `mypy`'s `platform = "linux"` (matching what CI
     actually targets) flipped the error to the *opposite* branch's
     Windows-only symbols instead of fixing it — the real fix was
     switching `supervisor.py`'s runtime platform checks from
     `os.name == "posix"` to `sys.platform != "win32"`, since mypy has
     special-cased narrowing for `sys.platform` comparisons specifically
     (skipping type-checking the non-matching branch entirely) but not for
     `os.name` comparisons. Verified behavior-identical after the switch:
     all 4 `test_supervisor.py` cases still pass in WSL2.
  3. `pip-audit` found 46 known vulnerabilities across 7 packages — all
     transitive dependencies of the dev-only `mkdocs-material` extra (or
     stale bootstrap `pip`/`setuptools`), none in paperloom's own direct
     dependencies. Upgraded all 7 to patched versions; clean afterward.

---

## Item 10, corrected — model-agnostic architecture (not `ollama_synth.py`)

**Status: done.** `paperloom_ollama_correction.md` superseded §11 of the
build spec after external real-world use (a Linux-machine test session,
22 real papers ingested and queried, `/ask` output quality independently
assessed as genuinely strong) prompted a direct question: could a
schema-less local LLM actually drive paperloom's existing tool loop as
reliably as Claude Code does? The honest answer was no, and the original
plan — a bundled `ollama_synth` plugin calling Ollama directly from inside
paperloom — was flagged as real architectural drift from the spec's own
design principles #1/#4 (zero required API keys, MCP server does file
operations only, never LLM calls).

**What changed:** paperloom never calls an LLM, anywhere, including local
ones. Local-model support comes entirely from *other* MCP-compatible host
agents (Continue.dev, Cline, Aider) already capable of talking to Ollama —
paperloom's server is identical regardless of what's on the other end. The
one concession to weak local models: a new 10th MCP tool,
`describe_workflow(operation) -> str`, returning an explicit step-by-step
recipe from `src/paperloom/workflows/*.md`, plus a mode-aware `CLAUDE.md`
(`mode: capable` / `mode: local`) with dual-variant instructions for all
four operations (`/contribute`, `/ask`, `/lint`, `/rebuild-context`) —
extended to all four from the correction's own single worked example
(`/ask`), keeping every existing `[capable mode]` instruction word-for-word
from the already-validated schema, not rewritten.

**Real bug found while writing the `/rebuild-context` local-mode variant:**
none of paperloom's 10 tools can overwrite a whole file (`append_to_page`
only appends; `create_note` refuses if the file exists), yet
`/rebuild-context`'s own instructions have always said "rewrite
context.md" — a gap present since the *original* §8 schema, never actually
resolved. Fixed by being explicit in both the recipe file and `CLAUDE.md`:
that one step uses the host agent's own native file-write capability, not
a paperloom tool.

**Built:**
- `src/paperloom/mcp_server.py` — `describe_workflow`, following the
  existing tool pattern exactly (including calling `find_vault_root()`
  purely to preserve the "every tool requires vault context" invariant,
  even though the function doesn't otherwise need it — matches the
  correction's own reference implementation).
- `src/paperloom/workflows/{contribute,ask,lint,rebuild_context,ingest}.md`
  — verified these are actually packaged (not just present in the source
  tree) by building a real wheel and inspecting its contents directly,
  same discipline as everything else in this project.
- Mode-aware `CLAUDE.md` in both the template and
  `examples/ml-robotics-vault/` (kept byte-identical between the two, as
  they were before this change).
- `docs/quickstart-local.md` (host-agent comparison table, model-quality
  tiers, honest "don't promise more than this" framing) and
  `tests/qualitative/three_question_eval.md` (built from the three real
  questions already run against the 22-paper vault, generalized into a
  repeatable reference for what "good" looks like at each tier).
- `paperloom.md` itself updated to apply the correction verbatim (§11
  replaced, §8/§9/§17 amended) plus a full sweep for stale references the
  correction didn't explicitly call out: a wrong section cross-reference
  in the preamble (said "Section 12," meant "Section 9"), a `doctor`
  command spec mentioning an Ollama check, and a "9 tools" count left
  over in three more places.
- New tests: `describe_workflow` happy/list_all/unknown-operation/
  outside-vault-error, and a guard test that the shipped `workflows/*.md`
  files match exactly what the tool expects — catches the two from
  drifting apart.

**Verification:** full suite passed clean on both platforms after the
change — 47/47 native (Windows), 51/51 real Linux (WSL2, including
`test_supervisor.py`'s kill-9 tests) — confirming the existing 46 tests
are genuinely unchanged, not just "still passing by coincidence." `ruff
check`, `ruff format --check`, `mypy src/`, `pip-audit` all clean on both
platforms. `mkdocs build --strict` succeeds with the new page wired into
nav. Real wheel build confirmed the new `workflows/` files are actually
packaged. Not done, deliberately, per your own call: installing Ollama and
running the three-question eval against a real local model — that's yours
to do whenever convenient, using `tests/qualitative/three_question_eval.md`
as the reference; nothing about this change touches your existing
22-paper vault.

---

## Making Cline+Ollama actually work smoothly (real-world setup)

**Status: done.** After the model-agnostic architecture landed, you
installed Cline (VS Code extension), Ollama, and pulled `qwen3.5:9b` and
`qwen3.5:4b`, using `4b` for the larger context window given your RAM/
VRAM/storage constraints. This wasn't more infrastructure — the mechanical
pieces already worked — it was making sure the actual setup wouldn't
silently fail.

**Model pick, researched fresh rather than from training-cutoff knowledge**
(you specifically asked for this): the obvious-looking name "Qwen3.8" is
real, but it's an unrelated, much newer flagship line (`Qwen3.8-Max`, a
2.4T-parameter MoE; `Qwen3.8-Flash-Next`, 176B total params, ~110GB even at
4-bit) released the same week as this conversation — nowhere near
local-GPU territory. **Qwen3.5** (Feb 2026, so still current) is the
actual right pick: real dense 4B/9B variants on Ollama's library
(`qwen3.5:9b` = 6.6GB), confirmed native MCP/tool-calling support (the
Qwen3.x line is specifically optimized for MCP agent use, verified via
Qwen-Agent's own docs), which matters a lot here since local-mode's entire
value depends on the model actually calling paperloom's tools correctly,
not just chatting well.

**The real gotcha, found before it could bite you:** Cline's MCP config is
one global file (`cline_mcp_settings.json`, not per-project like
`.mcp.json`), and Cline has a documented history of spawning stdio MCP
servers with the wrong working directory unless `cwd` is set explicitly —
confirmed via Cline's own GitHub PR #2990 and issue #9950, not assumed.
Since `paperloom mcp` finds the vault by walking up from its own cwd
(`find_vault_root()`), a wrong cwd would have meant Cline's `paperloom`
tools either silently fail or resolve the wrong vault, with nothing
obviously pointing at the cause. Fixed by documenting
`"cwd": "${workspaceFolder}"` explicitly in `docs/quickstart-local.md`'s
new Cline setup section, rather than relying on a default that's been
buggy before.

**Scope, deliberately kept small:** no paperloom code changes — this was
purely a docs-accuracy gap (the setup steps that would have made "select
Ollama instead of Claude Code" actually work weren't written down
anywhere). Added: the Cline config location per OS, the exact JSON entry,
the `cwd` explanation, and a short Ollama memory-management note
(`ollama stop <model>` / default 5-minute auto-unload) addressing your
"don't keep models resident" request. Also refreshed
`docs/quickstart-local.md`'s model-tier table to reference Qwen3.5 instead
of the now-superseded Qwen3 names it originally had.

**What's still yours to do:** I can't drive Cline's UI myself (it's a VS
Code extension, not scriptable from here), so the actual end-to-end
smoke test — does Cline's MCP panel show `paperloom` connected, does a
real question through `qwen3.5:4b` in local mode come back sensibly — is
on you, using the steps in `docs/quickstart-local.md`'s new Cline section.

---

## Not started yet (§17 item 9, v0.2)

9. `migrate-from-mindbase` (optional for now).
