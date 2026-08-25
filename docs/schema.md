# The `CLAUDE.md` schema

`CLAUDE.md`, at the root of every vault, is what makes the wiki "smart."
Paperloom's own code — the CLI, the MCP server — never summarizes,
synthesizes, or decides what a page should say. All of that intelligence
lives in this one file, which your coding agent reads at the start of a
session and follows for the rest of it.

**Paperloom writes this file once, at `paperloom init`, and never touches
it again.** It's yours to edit. There's no migration system, no "schema
version" the tool enforces — if a future paperloom release changes the
recommended schema, that shows up in `CHANGELOG.md` for you to adopt
manually, not as a silent overwrite.

## What's in the shipped template

The default `CLAUDE.md` (from the `scientific-paper-vault` template)
covers:

- **The maintainer's role** — explicitly *not* to write research, but to
  maintain the substrate: read papers, integrate them into the wiki,
  answer questions grounded in it, audit for drift.
- **Domain focus** — a placeholder section marked `(EDIT THIS)` listing
  default topics/venues (self-supervised learning, JEPA architectures,
  drug-target interaction, ...). Change this first — it's the one section
  guaranteed to need editing for your actual field.
- **The three layers** — which parts of the vault are immutable
  (`sources/raw/`), agent-owned (`sources/research/`), and user-owned
  (`sources/contributors/`).
- **Provenance discipline** — the hard rule that every non-trivial claim in
  a wiki page links back to a raw source (`[[raw:2301.08243#sec-3-1]]`),
  with three explicit, marked exceptions for common knowledge, cross-source
  synthesis, and unclear/garbled source text.
- **Page shapes** — the exact YAML frontmatter and body structure for
  paper, method, dataset, concept, and synthesis pages. Field names matter:
  some tooling (search scoping, the plugin `find_orphans`/`word_count`
  helpers, future lint tooling) reads them directly.
- **The four operations** — `/contribute`, `/ask`, `/lint`,
  `/rebuild-context` — each a workflow description the agent follows, not
  code paperloom executes.

## Customizing it for your field

Realistically, most edits fall into one of these:

- **Domain focus** — swap the topics/venues list for your own field.
- **Page shapes** — add a new page type (e.g. a `benchmark` page) by
  writing its frontmatter fields and body-section convention the same way
  the existing five are documented. The MCP tools (`create_note`,
  `list_pages`) don't care what `type:` values exist — they're generic.
- **Provenance rules** — tighten or loosen the citation discipline for
  your field's norms.
- **Operations** — add a fifth workflow, or change what `/lint` checks for.

Nothing here requires touching paperloom's own code. The tool exposes
primitives (`search`, `read_page`, `create_note`, `append_to_page`,
`tag_note`, `log_entry`, `list_pages`, `ingest_pdf`, `vault_info`) — see
the [full tool table in the README](https://github.com/Alpsource/paperloom#the-9-tools) — and `CLAUDE.md` is
entirely responsible for how they get used.

## If you need a new *tool*, not just a schema change

That's what [plugins](plugins.md) are for.
