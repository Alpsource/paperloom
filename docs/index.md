# Paperloom

Folder-scoped, LLM-maintained research wiki for scientific papers.

Paperloom is a small MCP server + CLI that gives a coding agent (Claude
Code, Gemini CLI, ...) the file-manipulation tools it needs to maintain a
personal research wiki — batch PDF ingest, full-text search, note
creation, tagging, logging — while the agent itself supplies all the
actual reading, writing, and reasoning. Paperloom never calls an LLM API
of its own.

It implements Andrej Karpathy's [`llm-wiki`
pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
following [MindBase](https://github.com/frankchu91/mindbase-llm-wiki)'s
lead in productizing it — see [Credits](credits.md) for the full story.

## Where to go next

- **[Quickstart](quickstart.md)** — three commands to a working vault.
- **[Schema](schema.md)** — how `CLAUDE.md` works and how to customize it
  for your own research domain.
- **[Plugins](plugins.md)** — how to add new MCP tools without touching
  core.
- **[Credits](credits.md)** — the two projects paperloom builds on.

## The three layers, at a glance

```
sources/raw/<paper-id>/    immutable — original PDF + MinerU-parsed markdown
sources/research/          agent-owned — the wiki pages themselves
sources/contributors/      your daily notes
```

Everything else — the MCP tools, the CLI, the plugin system — exists to
read and write those three layers safely. See the [schema
docs](schema.md) for what actually goes in each page.
