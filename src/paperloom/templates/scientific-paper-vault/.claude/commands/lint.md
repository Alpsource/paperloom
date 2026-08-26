---
description: Health check the wiki - orphans, dangling links, unbacked claims, contradictions
---

Run the `/lint` operation defined in this vault's `CLAUDE.md`. Walk
`sources/research/**/*.md` and report orphan pages, dangling `[[links]]`,
methods/datasets mentioned but missing their own page, paragraphs without
a `[[raw:...]]` / `{{common-knowledge}}` / `{{synthesis}}` /
`{{unclear-in-source}}` marker, and any contradictions between pages.
Present findings — do not auto-fix.
