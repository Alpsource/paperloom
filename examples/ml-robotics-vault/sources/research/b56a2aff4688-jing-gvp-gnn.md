---
type: paper
id: b56a2aff4688
title: "Learning from Protein Structure with Geometric Vector Perceptrons"
authors: [Jing, Eismann, Suriana, Townshend, Dror]
year: null
venue: null
tags: [gnn, protein-structure, geometric-deep-learning]
raw: sources/raw/b56a2aff4688/paper.md
---

`{{unclear-in-source}}` no arXiv ID or DOI was detectable on this PDF's
first page during ingestion, so its vault ID is a content hash rather than
an arXiv number, and `year`/`venue` weren't captured by the ingestion
pipeline's metadata enrichment — not reported rather than guessed.

## TLDR

Introduces the Geometric Vector Perceptron (GVP), a drop-in replacement
for MLP layers in GNNs that operates on both scalar and Euclidean-vector
features, letting a single GNN reason about both the geometric (3D
positions/orientations) and relational (sequence, residue-residue
interaction) aspects of macromolecule structure at once — where prior
architectures leaned on one aspect or the other, not both
[[raw:b56a2aff4688#ABSTRACT]].

## Contributions

- [[method:geometric-vector-perceptron]]: extends standard dense layers to
  operate on collections of Euclidean vectors, not just scalars
  [[raw:b56a2aff4688#ABSTRACT]].
- Demonstrates GVP-GNN outperforms prior state-of-the-art CNN and GNN
  architectures on two protein-structure problems: model quality
  assessment (MQA) and computational protein design (CPD)
  [[raw:b56a2aff4688#ABSTRACT]].
- Frames the geometric/relational split explicitly: geometric methods
  (CNNs, operating directly on 3D geometry) versus relational methods
  (GNNs, expressive on sequence/interaction structure) as the two
  previously-separate leading approaches this work unifies
  [[raw:b56a2aff4688#1-INTRODUCTION]].

## Method summary

A GVP is a drop-in replacement for the MLPs used in a GNN's aggregation
and feed-forward layers. It operates directly on scalar features and on
geometric features — features that transform as a vector under rotation of
the spatial coordinate frame — so geometric information at nodes and edges
can be embedded without first reducing it to scalars, which would discard
information a scalar-only representation can't fully capture
[[raw:b56a2aff4688#1-INTRODUCTION]]. The resulting GVP-GNN applies to any
problem where the input is the structure of a single macromolecule, or of
molecules bound to one another [[raw:b56a2aff4688#1-INTRODUCTION]].

## Datasets & metrics

`{{unclear-in-source}}` specific dataset names and metric values for the
MQA/CPD evaluations are in tables further into the raw parse than reviewed
for this page — not reported here rather than guessed. See
[[raw:b56a2aff4688]] directly (code released at
github.com/drorlab/gvp, per the paper's own abstract
[[raw:b56a2aff4688#ABSTRACT]]).

## Related work in this vault

- None yet — this is the vault's only structural-biology / geometric-GNN
  paper. The other four are all [[method:jepa]] applications
  ([[concept:self-supervised-representation-learning]]); GVP-GNN doesn't
  belong to that family (it's a supervised architecture, not a
  self-supervised pretraining method), so no [[method:jepa]] cross-link
  applies here.

## Open questions

- This paper predates the JEPA-family papers in this vault (GVP layers
  are from 2020-2021-era work based on citation patterns in the raw text,
  while every other paper here is 2023+). Whether a JEPA-style
  self-supervised pretraining objective could be combined with GVP-style
  geometric layers is a natural question this vault doesn't yet have an
  answer to — no paper here addresses it.
