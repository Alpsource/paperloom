# Context

*Last built: 2026-08-25*

## Current focus

Five papers, ingested and written up: four extend the Joint-Embedding
Predictive Architecture ([[method:jepa]]) to a new modality, and one
(GVP-GNN) is unrelated to JEPA entirely — a geometric-GNN architecture for
protein structure. The vault currently demonstrates the full page-shape
set (paper, method, concept, synthesis) but is intentionally small; it's a
worked example, not a comprehensive literature review of any of these
subfields.

## Active topics

**JEPA across modalities.** [[paper:2309.16014]] (Graph-JEPA),
[[paper:2403.11772]] (S-JEPA), [[paper:2409.19407]] (Brain-JEPA), and
[[paper:2512.10942]] (VL-JEPA) each adapt [[method:jepa]] to a different
domain — graphs, EEG, fMRI, and vision-language respectively. The
[[synthesis:2026-08-25-jepa-modality-adaptations]] page works through what
each adaptation actually changes: the three single-modality papers
(graph/EEG/fMRI) each redesign *masking* to match their modality's real
structure rather than reusing image-patch masking; VL-JEPA instead changes
what's *predicted* (cross-modal text embeddings, not tokens), since its
context and target are different modalities by construction.

**Structural biology, separately.** [[paper:b56a2aff4688]] (GVP-GNN)
introduces [[method:geometric-vector-perceptron]] layers for protein
structure — a supervised architecture change, not a self-supervised
pretraining method, so it sits outside the JEPA cluster. It's in this
vault because the domain focus in `CLAUDE.md` includes drug-target
interaction and structural biology as adjacent interests, not because it
relates to the other four papers.

## Key decisions

- This example vault deliberately keeps `sources/raw/` limited to five
  small papers to stay lightweight as a shipped example — it isn't meant
  to demonstrate scale (see the build spec's own note that ripgrep search
  and this file layout are expected to hold up to hundreds of papers).
- The [[method:jepa]] page's `introduced_by` frontmatter field is
  deliberately empty, not pointing at a `[[paper:...]]` that doesn't exist
  in this vault. The originating papers (LeCun's 2022 position paper,
  Assran et al.'s I-JEPA) were never ingested here — every JEPA claim on
  that page is synthesized from what the four downstream papers say about
  the framework in their own introductions, not from the source paper
  itself. This is flagged directly on the page rather than papered over.

## Learnings

- Every JEPA-family paper here independently describes the same
  target-encoder pattern: an EMA (exponential moving average) copy of the
  context encoder, not trained by direct gradient descent. It shows up
  identically in Graph-JEPA, S-JEPA, and Brain-JEPA's method descriptions,
  which is a reasonably strong signal it's a load-bearing design choice
  for the whole JEPA family, not an incidental implementation detail of
  any one paper.
- Domain-specific masking design shows up as the central contribution in
  three of the four single-modality JEPA papers here (Graph-JEPA's
  subgraph masking + hyperbolic objective, S-JEPA's spatial channel
  masking, Brain-JEPA's Spatiotemporal Masking + Brain Gradient
  Positioning). None of them treat "port JEPA to a new modality" as a
  trivial backbone swap — masking strategy is where the actual research
  contribution lives in each case.

## Open questions

- None of the four JEPA papers here compare against each other directly
  (different modalities, different benchmarks) — there's no way to say
  from this vault alone whether, e.g., Brain-JEPA's more involved
  three-region masking is actually necessary versus S-JEPA-style simpler
  spatial masking would have worked for fMRI too.
- I-JEPA (arXiv:2301.08243) itself isn't ingested. Every method-page claim
  about "what JEPA is" in this vault is currently a synthesis across
  downstream applications rather than grounded in the original source.
- BrainLM, the prior fMRI foundation model Brain-JEPA compares against,
  also isn't ingested — no independent verification of Brain-JEPA's
  comparative claims is possible from this vault alone.

## Blockers

None currently — the gaps above are "papers worth ingesting next," not
blockers to using what's here.
