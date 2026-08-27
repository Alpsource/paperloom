# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — Unreleased

Initial build, implementing §17 items 1-8, 10, 11, 12 of the build spec
(`paperloom.md`). Item 9 (MindBase migration) is v0.2.

Item 10 was redefined by `paperloom_ollama_correction.md` after the
initial build: no `plugins/ollama_synth.py` (paperloom never calls an LLM,
including local ones) — instead, a `describe_workflow` MCP tool, mode-aware
`CLAUDE.md` (`capable`/`local`), and local-model host-agent docs.

### Added
- Vault discovery (`paperloom.vault`): `.paperloom/` marker walk-up, path
  resolution, frontmatter I/O.
- Subprocess supervision (`paperloom.supervisor`): guaranteed cleanup on
  any exit path, including `os._exit`/`SIGKILL`/OOM via `PR_SET_PDEATHSIG`
  on Linux.
- CLI (`paperloom.cli`): `init`, `ingest`, `search`, `mcp`, `version`.
- Batch PDF ingestion (`paperloom.ingest`) via MinerU, with arXiv/DOI-aware
  ID detection, best-effort Semantic Scholar metadata enrichment, and
  per-paper failure isolation.
- Ripgrep-backed vault search (`paperloom.search`).
- The MCP server (`paperloom.mcp_server`): all 10 tools — `search`,
  `read_page`, `list_pages`, `create_note`, `append_to_page`, `tag_note`,
  `log_entry`, `ingest_pdf`, `vault_info`, `describe_workflow`.
- Plugin system (`paperloom.plugins`): built-in, third-party (entry
  points), and vault-local plugin loading, with the built-in
  `example_plugin` (`word_count`, `find_orphans`).
- The `scientific-paper-vault` template, including the full `CLAUDE.md`
  maintainer schema — mode-aware (`capable`/`local`) per
  `paperloom_ollama_correction.md`, with matching `describe_workflow`
  recipes shipped in `paperloom.workflows`.
- Docs, README, and a real populated example vault
  (`examples/ml-robotics-vault/`).
- `docs/quickstart-local.md` and `tests/qualitative/three_question_eval.md`
  — local-model host-agent guidance and the qualitative eval reference.
- CI (lint, type-check, tests, dependency audit, a subprocess-supervision
  guardrail) and a PyPI release workflow.

[0.1.0]: https://github.com/Alpsource/paperloom/releases/tag/v0.1.0
