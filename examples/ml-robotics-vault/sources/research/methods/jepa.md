---
type: method
canonical: Joint-Embedding Predictive Architecture (JEPA)
aliases: [JEPA]
kind: architecture
introduced_by: []
uses: []
applied_to: [concept:self-supervised-representation-learning]
---

A JEPA learns by predicting the latent representation of a target signal
from the latent representation of a context signal, rather than
reconstructing the target in its original data space. `{{synthesis:
[[raw:2309.16014]], [[raw:2403.11772]], [[raw:2409.19407]]}}` this is what
distinguishes it from both contrastive joint-embedding methods (which need
negative/positive sample pairs) and generative masked-autoencoder methods
(which reconstruct in pixel/data space and can overfit to
reconstruction-irrelevant detail).

**Not yet in this vault:** the originating papers — LeCun's 2022 position
paper and Assran et al.'s I-JEPA (arXiv:2301.08243) — haven't been ingested
here, so `introduced_by` above is empty rather than pointing at a
`[[paper:...]]` page that doesn't exist in `sources/research/`. `{{common-
knowledge}}` JEPA is generally attributed to those two works. Ingesting
I-JEPA would complete the provenance chain for this page.

## How it works

Three components, consistently described across every JEPA-family paper in
this vault: a context encoder, a target encoder (usually an EMA-updated
copy of the context encoder, not trained by gradient descent directly —
`{{synthesis: [[raw:2403.11772]]}}`), and a predictor that maps the context
encoding to a prediction of the target encoding. The training objective is
a distance between the predicted and actual target-encoder representations
— `{{synthesis: [[raw:2309.16014]], [[raw:2403.11772]]}}` — computed
entirely in embedding space, never in the original data space.

## Variants in this vault

| Paper | Domain | Key adaptation |
|---|---|---|
| [[paper:2309.16014]] Graph-JEPA | Graphs | Masked subgraph prediction; target coordinates on the unit hyperbola instead of raw embedding regression, to encode implicit graph hierarchy — [[raw:2309.16014#1-Introduction]] |
| [[paper:2403.11772]] S-JEPA | EEG / BCI | Domain-specific spatial block masking across EEG channels — [[raw:2403.11772#INTRODUCTION]] |
| [[paper:2409.19407]] Brain-JEPA | fMRI | Brain Gradient Positioning (a functional coordinate system replacing anatomical position encoding) + Spatiotemporal Masking tailored to fMRI's heterogeneous time-series patches — [[raw:2409.19407#1-Introduction]] |
| [[paper:2512.10942]] VL-JEPA | Vision-language | Predicts *text* embeddings from vision input instead of autoregressively generating tokens — [[raw:2512.10942#1-Introduction]] |

## Open questions

- What does the accuracy/efficiency trade-off actually look like when a
  JEPA's target modality is discrete (text, as in VL-JEPA) versus
  continuous (EEG/fMRI time series, images)? None of the four papers here
  directly compare against each other.
- Ingest I-JEPA (arXiv:2301.08243) to ground this page's core definition
  in the originating source rather than four downstream applications'
  restatements of it.
