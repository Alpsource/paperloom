# Three-question eval

Referenced by §11 of `paperloom.md` as the reference for what "works well"
looks like against a real vault, at each model-quality tier. There's no
automated pass/fail here — this is a human-judged qualitative check, run
against your own vault, comparing what you get to what's described below.

## How to run it

Pick three questions of your own that actually require pulling from
multiple pages in your vault (not something answerable from a single
page's first paragraph — see "what makes a good question" below). Ask
each one through whichever host agent/model you're evaluating. Read the
answer against the checklist for the relevant tier.

## What makes a good eval question

A question that only needs one page doesn't test anything interesting —
any model can grep-and-summarize. The good ones require the agent to:
- pull facts from **2+ pages** and connect them,
- notice a **gap** the vault doesn't directly answer (and say so, rather
  than inventing an answer), or
- **compare or contrast** two sources on the same axis.

## Reference example: what frontier-tier output looks like

These three questions were actually run against a real 22-paper vault
(JEPA-family papers, drug-target interaction, genomics, generative
tokenization) using Claude Code. Full transcripts aren't reproduced here
(they're vault-specific), but the shape of what made them *good* answers,
generalizes:

**Q1 — "Given what my wiki knows about [paper A], [paper B], and [paper
C], is there a [novel combination] that would apply to [some target
domain]? Cite specifically."**

What the frontier-tier answer did right:
- Explicitly marked the whole answer `{{synthesis}}` — no single source
  makes this claim, and it said so up front rather than implying one did.
- Cited specific sections (`[[raw:<id>#section-name]]`), not just paper
  names — a claim like "AToken only fills $t{=}0$ for the 3D case" is
  falsifiable against the source, a vague gesture at "the paper" isn't.
- Pulled in **two pages the source papers themselves never cite** (spotted
  the actual gap, not just restated what the papers already say about
  each other).
- Ended by offering to file the answer as a synthesis page — didn't just
  answer and stop.

**Q2 — "What's the strongest argument in my wiki for [X]? What's the
strongest argument against?"**

What the frontier-tier answer did right:
- Argued *for* and *against* using the **same underlying mechanism** from
  two directions, not two disconnected facts — the "for" case and the
  "against" case were in direct tension, not just two unrelated pros/cons.
- Stated plainly: "the wiki doesn't contain a [X] paper to test this
  head-to-head — this is a synthesis I've assembled, not a claim either
  paper makes about the other." Correct epistemic humility, not
  overclaimed confidence.

**Q3 — "What method in my wiki, if any, is closest to [known method], but
for [different domain]?"**

What the frontier-tier answer did right:
- Answered **"None"** and explained why on concrete axes, rather than
  straining to manufacture a connection that doesn't hold up. A system
  optimizing for "sound smart" forces an answer; a good one says "no" when
  the honest answer is no.
- The offered extension ("here's what a hypothetical version would look
  like") was explicitly flagged as "a proposal, not something currently in
  the vault" — never blurred with what's actually documented.

## What to look for at each tier

Use `[capable mode]` vs `[local mode]` schema variants matching whichever
you're testing (§8's mode-aware `CLAUDE.md`).

- **Frontier** (Claude Sonnet 4.5+, GPT-5, Gemini 2.5 Pro): should match
  the shape above — multi-page synthesis, section-level citations, correct
  `{{synthesis}}`/`{{unclear-in-source}}` hedging, willing to say "no" or
  "not in the vault" rather than force a connection.
- **Strong local** (Qwen3-32B, Llama 3.3-70B): expect noticeably shorter
  synthesis, possibly missing the "spot the gap across pages the sources
  don't cite each other on" move — but citations should still be accurate
  and hedging should still be present.
- **Medium local** (Qwen3-14B, Llama 3.1-8B, `mode: local` schema):
  expect solid single-page retrieval with a citation. Multi-page synthesis
  quality drops off — may need you to explicitly ask "should I also read
  [[X]]" per the local-mode `/ask` workflow rather than doing it
  unprompted. Watch for citations that don't actually match the quoted
  text — verify at least one against the raw source yourself.
- **Small local** (Llama 3.2-3B, Qwen3-4B): retrieval only. Don't expect
  synthesis across pages — if it attempts one, verify it carefully; this
  tier is the most likely to blur `{{synthesis}}` into stated fact without
  meaning to.

## If your local-model results are noticeably worse than this

That's expected, not a bug report — see the tier table above and in
`docs/quickstart-local.md`. If a *frontier* model's results look
noticeably worse than the reference shape above, that's worth actually
investigating: check whether `CLAUDE.md`'s `mode:` line matches what you
intended, and whether the model is actually reading raw sources before
quoting them (§8's provenance discipline) rather than paraphrasing from a
research page.
