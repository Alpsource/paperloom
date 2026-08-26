---
description: Answer a question from the wiki, grounded with citations
argument-hint: <your question>
---

Run the `/ask` operation defined in this vault's `CLAUDE.md` for this
question:

$ARGUMENTS

Follow that section's workflow exactly — search, read the top pages,
follow `[[wikilinks]]` up to 2 hops, verify exact numbers/quotes against
the raw source before stating them, and cite every non-trivial claim. At
the end, ask whether to save the answer as a synthesis page.
