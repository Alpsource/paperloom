---
type: method
canonical: Geometric Vector Perceptron (GVP)
aliases: [GVP, GVP-GNN]
kind: architecture
introduced_by: [paper:b56a2aff4688]
uses: []
applied_to: [concept:self-supervised-representation-learning]
---

A drop-in replacement for standard MLP layers in a GNN's aggregation and
feed-forward steps, extended to operate on collections of Euclidean
vectors rather than only scalars
[[raw:b56a2aff4688#ABSTRACT]].

## How it works

Protein structure has both a geometric aspect (3D positions/orientations
of residues) and a relational aspect (sequence and residue-residue
interactions); prior work leaned on one or the other — CNNs for geometry,
GNNs for relations — but not both at once
[[raw:b56a2aff4688#1-INTRODUCTION]]. GVPs operate directly on both scalar
and vector-valued (geometric) features, where the vector features
transform correctly under rotation of spatial coordinates, so a GNN built
from GVP layers can reason over macromolecule structure without collapsing
geometric information down to scalars first
[[raw:b56a2aff4688#1-INTRODUCTION]].

## Variants in this vault

| Paper | Domain | Notes |
|---|---|---|
| [[paper:b56a2aff4688]] GVP-GNN | Protein structure | Evaluated on model quality assessment and computational protein design, outperforming prior CNN and GNN baselines on both — [[raw:b56a2aff4688#ABSTRACT]] |

## Open questions

- This vault has no other structural-biology papers yet to compare GVP-GNN
  against more recent geometric GNN variants — a gap, not a finding.
