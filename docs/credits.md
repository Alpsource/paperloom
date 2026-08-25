# Credits

Paperloom stands on two shoulders.

## Andrej Karpathy — the `llm-wiki` pattern

Paperloom implements the pattern described in Andrej Karpathy's
[`llm-wiki` gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f):
a folder of markdown files, maintained by an LLM coding agent driven by a
schema file (`CLAUDE.md`) that lives in the same folder. No database, no
server, no vendor lock-in — the wiki is just files, and the "smart" part is
entirely in how the schema instructs the agent to read and write them.

Everything about paperloom's core design — the file layout, the idea that
the tool itself should be "dumb" and the schema should be "smart," the
provenance-linking discipline — is a direct instantiation of that pattern,
specialized for one domain: batches of scientific papers.

## Frank Chu's MindBase — proving it could be a product

[MindBase](https://github.com/frankchu91/mindbase-llm-wiki) took Karpathy's
pattern and productized it: an MCP server exposing wiki-manipulation tools,
a project-scoped data layout, contributor daily logs, and CLAUDE.md schema
conventions (page frontmatter shapes, the "three layers" split between
immutable sources and agent-maintained pages, provenance markers like
`{{synthesis}}` and `{{unclear-in-source}}`) that paperloom borrows and
extends rather than reinventing from scratch.

See [Appendix A of the build spec](https://github.com/Alpsource/paperloom/blob/main/paperloom.md)
for a full tool-by-tool mapping from MindBase's surface to paperloom's.

## What paperloom changes

Three specific differences, all driven by the scientific-paper use case:

1. **Batch PDF ingest with MinerU pre-parsing.** MindBase's ingestion is
   file-at-a-time; paperloom is built around `paperloom ingest
   ~/Downloads/papers/` handling 50-1000 PDFs in one run, with a resumable
   checkpoint and per-paper failure isolation.
2. **One vault per working directory, no global data folder.** MindBase
   keeps a `~/mindbase-data/projects/<name>/` layout outside your repo;
   paperloom vaults are fully self-contained — `git init && paperloom init`
   in any folder produces a complete, portable knowledge base.
3. **Zero required LLM API keys.** The host coding agent (Claude Code,
   Gemini CLI, whatever you're already paying for) supplies all the
   intelligence. The Ollama plugin (v0.2) is opt-in for fully-offline
   headless jobs, never a requirement.

Nothing MindBase does that isn't reflected here is lost for a paperloom
user working with Claude Code — it's either a smart feature now handled by
the host agent instead of a bespoke tool, or UI-layer functionality that
doesn't apply to a CLI-first tool. See the build spec's Appendix A for the
detailed mapping.
