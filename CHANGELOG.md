# Changelog

All notable changes to this project are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/).

## [0.1.0] — Unreleased

Initial build, implementing §17 items 1-8, 11, 12 of the build spec
(`paperloom.md`). Items 9-10 (MindBase migration, Ollama plugin) are v0.2.

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
- The MCP server (`paperloom.mcp_server`): all 9 tools — `search`,
  `read_page`, `list_pages`, `create_note`, `append_to_page`, `tag_note`,
  `log_entry`, `ingest_pdf`, `vault_info`.
- Plugin system (`paperloom.plugins`): built-in, third-party (entry
  points), and vault-local plugin loading, with the built-in
  `example_plugin` (`word_count`, `find_orphans`).
- The `scientific-paper-vault` template, including the full `CLAUDE.md`
  maintainer schema.
- Docs, README, and a real populated example vault
  (`examples/ml-robotics-vault/`).
- CI (lint, type-check, tests, dependency audit, a subprocess-supervision
  guardrail) and a PyPI release workflow.

[0.1.0]: https://github.com/Alpsource/paperloom/releases/tag/v0.1.0
