---
type: concept
---

## Definition

Learning representations from unlabeled data by constructing a training
signal out of the input itself, rather than from human-provided labels —
e.g. by masking part of the input and training a model to recover or
predict something about the masked part.

## When it matters

Every paper in this vault reaches for self-supervision for the same
underlying reason: labeled data is expensive or scarce relative to the
raw data available. `{{synthesis: [[raw:2309.16014]], [[raw:2409.19407]]}}`
Graph-JEPA motivates this via the cost of manually labeling graph data
across bioinformatics/chemoinformatics/social-network domains
[[raw:2309.16014#1-Introduction]]; Brain-JEPA motivates it via the scale of
unlabeled fMRI data available relative to labeled clinical outcomes
[[raw:2409.19407#1-Introduction]].

## Papers that shaped current understanding (in this vault)

- [[paper:2309.16014]] Graph-JEPA — extends [[method:jepa]] to graph-level
  representations via masked subgraph prediction.
- [[paper:2403.11772]] S-JEPA — extends [[method:jepa]] to EEG signals for
  cross-dataset BCI transfer.
- [[paper:2409.19407]] Brain-JEPA — extends [[method:jepa]] to fMRI brain
  dynamics.
- [[paper:2512.10942]] VL-JEPA — extends [[method:jepa]] to vision-language,
  predicting text embeddings instead of tokens.
- [[paper:b56a2aff4688]] GVP-GNN — a different self-supervision-adjacent
  strategy: not a JEPA variant, but a [[method:geometric-vector-perceptron]]
  architecture change that makes the *supervised* protein-structure tasks
  it targets (model quality assessment, protein design) more
  sample-efficient by better matching the model's inductive bias to the
  structure of the input.

## Sibling concepts

- Contrastive learning (invariance-based self-supervision) — described as
  JEPA's alternative in every JEPA paper here, but no contrastive-learning
  paper is itself ingested in this vault yet. A gap, not a finding.
- Masked autoencoding (generative reconstruction-based self-supervision) —
  same situation: discussed as a contrast point by
  [[paper:2403.11772]] and [[paper:2409.19407]], but not itself
  represented by an ingested paper here.
