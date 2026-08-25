# ML/Robotics Example Vault

A small, fully real, worked example of a paperloom vault — shipped
alongside the [paperloom repo](https://github.com/Alpsource/paperloom) so
you can see what a populated vault actually looks like instead of just
reading about the schema.

Five real papers, actually ingested via `paperloom ingest` (real MinerU
parses in `sources/raw/`, not stand-in text), with hand-written wiki pages
in `sources/research/` demonstrating all five page shapes from
`CLAUDE.md`: paper, method, dataset-adjacent concept, and synthesis pages,
cross-linked with `[[wikilinks]]` and grounded with `[[raw:...]]`
citations back to the actual parsed PDFs.

**Note:** each `sources/raw/<id>/` here has `paper.md`, `meta.json`, and
`images/` — but not `paper.pdf`. A real vault's `sources/raw/` keeps the
original PDF too; it's omitted here specifically to avoid redistributing
third-party arXiv PDFs in this public repo.

Start at [`index.md`](index.md) or [`context.md`](context.md).

## What's here

- 4 papers extending the [[method:jepa]] framework to a new modality each
  (graphs, EEG, fMRI, vision-language).
- 1 paper (GVP-GNN) on a geometric GNN architecture for protein structure
  — deliberately unrelated to the JEPA cluster, showing that a vault
  doesn't need every paper to be thematically connected.
- A synthesis page comparing how the four JEPA papers each adapt masking
  for their modality.
- Real gaps, documented rather than hidden: the JEPA method page notes
  its originating papers aren't ingested here, and several paper pages
  flag `{{unclear-in-source}}` where the raw MinerU parse was too messy
  to cite precisely (VL-JEPA's raw text in particular has heavy OCR
  corruption — a real example of what `paperloom ingest` output quality
  can look like on a difficult source PDF).

This vault isn't meant to be comprehensive — it's meant to be honest about
what a small, real, incrementally-built vault actually contains: solid
pages next to open questions and known gaps, exactly as `CLAUDE.md`'s own
provenance discipline expects.
