---
type: synthesis
date: 2026-08-25
---

## Question

What modalities has the [[method:jepa]] framework been extended to across
the papers in this vault, and what does each adaptation actually change
about the masking/context-target strategy — versus just swapping the
encoder backbone?

## Answer

Four papers in this vault apply JEPA to four different modalities, and in
every case the adaptation is more than a backbone swap — each identifies a
specific mismatch between image-style random/block masking and the target
modality's structure, and designs a masking or objective change to address
it.

**[[paper:2309.16014]] Graph-JEPA** (graphs) masks subgraphs rather than
image patches, predicting a target subgraph's representation from a
context subgraph's. It goes further than a direct port by changing the
*objective* itself: instead of regressing the target embedding directly,
it predicts the target's coordinates on the unit hyperbola in a 2D plane,
motivated by graph-level concepts having an implicit hierarchy that a flat
Euclidean regression target doesn't capture
[[raw:2309.16014#1-Introduction]].

**[[paper:2403.11772]] S-JEPA** (EEG) introduces spatial block masking —
masking across EEG *channels*, not just time — because EEG's useful
structure is spatial (which electrodes) as much as temporal. The paper's
own ablations found downstream performance was sensitive to
pretraining-example *length* but not mask *size*
[[raw:2403.11772#ABSTRACT]], suggesting the channel-masking dimension
matters more than how much of any single window gets masked.

**[[paper:2409.19407]] Brain-JEPA** (fMRI) goes furthest structurally: it
replaces positional encoding itself (Brain Gradient Positioning, a
functional rather than anatomical coordinate system for ROIs) *and*
introduces Spatiotemporal Masking that splits non-observed input into
three distinct regions (Cross-ROI, Cross-Time, Double-Cross) sampled
separately, rather than masking uniformly
[[raw:2409.19407#1-Introduction]]. The paper's stated reason: anatomically
nearby ROIs can have very different functional activation patterns, so
anatomical position (what the prior model BrainLM used) is the wrong
inductive bias for fMRI [[raw:2409.19407#1-Introduction]].

**[[paper:2512.10942]] VL-JEPA** (vision-language) is the outlier: it
doesn't change *masking* at all — the adaptation is changing what's being
predicted. Context is vision input, the "mask" is the query, and the
target is a *different modality entirely* (text), predicted as a
continuous embedding rather than generated as discrete tokens
[[raw:2512.10942#1-Introduction]]. This is a qualitatively different kind
of adaptation than the other three, which all stay within one modality and
change how *that modality* gets masked.

**Pattern:** the three single-modality adaptations (graph, EEG, fMRI) each
identify what "spatial structure" means for their domain and mask along
that structure specifically, rather than reusing image-patch masking
verbatim. The cross-modal case (VL-JEPA) doesn't need a masking innovation
at all, because context and target are already different modalities by
construction — the innovation there is entirely in what the objective
targets (embedding-space text prediction vs. token generation), not in how
input gets hidden from the model.

## Sources touched

- [[paper:2309.16014]] — [[raw:2309.16014]]
- [[paper:2403.11772]] — [[raw:2403.11772]]
- [[paper:2409.19407]] — [[raw:2409.19407]]
- [[paper:2512.10942]] — [[raw:2512.10942]]
- [[method:jepa]]
