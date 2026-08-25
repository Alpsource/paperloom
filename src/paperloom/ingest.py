"""Batch PDF ingestion: PDF -> MinerU -> sources/raw/<id>/. See §7 of
paperloom.md. Ingestion is deliberately separate from wiki writing — this
module only ever touches sources/raw/, never sources/research/."""

from __future__ import annotations

import errno
import hashlib
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pypdf import PdfReader
from rich.progress import Progress

from paperloom.supervisor import spawn
from paperloom.vault import append_log_line

ARXIV_RE = re.compile(r"\d{4}\.\d{4,5}")
DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+")

DEFAULT_MINERU_CMD = ["mineru"]


@dataclass
class ComputedId:
    id: str
    arxiv_id: str | None = None
    doi: str | None = None


@dataclass
class IngestResult:
    id: str
    pdf_path: Path
    status: str  # "success" | "skipped" | "failed"
    n_pages: int | None = None
    message: str | None = None


class IngestAborted(Exception):
    """Raised by ingest_folder when the batch is interrupted mid-run."""

    def __init__(self, completed: int, total: int):
        self.completed = completed
        self.total = total
        super().__init__(f"aborted after {completed}/{total} papers")


def _first_page_text(pdf_path: Path) -> str:
    try:
        reader = PdfReader(str(pdf_path))
        if not reader.pages:
            return ""
        return reader.pages[0].extract_text() or ""
    except Exception:
        return ""


def _slugify_doi(doi: str) -> str:
    return doi.replace("/", "_").replace(":", "_")


def compute_id(pdf_path: Path) -> ComputedId:
    """Derive a stable ID for a PDF: arXiv ID > DOI > sha256[:12]. See §7 step 2."""
    name = pdf_path.name
    m = ARXIV_RE.search(name)
    if m:
        return ComputedId(id=m.group(0), arxiv_id=m.group(0))

    text = _first_page_text(pdf_path)
    m = ARXIV_RE.search(text)
    if m:
        return ComputedId(id=m.group(0), arxiv_id=m.group(0))

    m = DOI_RE.search(name) or DOI_RE.search(text)
    if m:
        doi = m.group(0)
        return ComputedId(id=_slugify_doi(doi), doi=doi)

    return ComputedId(id=hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:12])


def _enrich_via_semantic_scholar(arxiv_id: str | None, doi: str | None) -> dict:
    """Best-effort metadata enrichment. Any failure (network, 404, rate
    limit) is silently ignored — no key required, low volume only. See §7
    step 6."""
    if not (arxiv_id or doi):
        return {}
    ident = f"ARXIV:{arxiv_id}" if arxiv_id else f"DOI:{doi}"
    try:
        r = httpx.get(
            f"https://api.semanticscholar.org/graph/v1/paper/{ident}",
            params={"fields": "title,authors,year,venue,referenceCount"},
            timeout=5.0,
        )
        r.raise_for_status()
        data = r.json()
        return {
            "title": data.get("title"),
            "authors": [a.get("name") for a in data.get("authors", [])] or None,
            "year": data.get("year"),
            "venue": data.get("venue"),
            "n_refs": data.get("referenceCount"),
        }
    except Exception:
        return {}


def _append_log(vault_root: Path, line: str) -> None:
    today = datetime.now().date().isoformat()
    append_log_line(Path(vault_root) / "logs" / f"{today}.md", line)


def ingest_one(
    pdf_path: Path,
    vault_root: Path,
    mineru_cmd: list[str] | None = None,
    skip_existing: bool = True,
    id_override: str | None = None,
) -> IngestResult:
    """Ingest a single PDF: §7 steps 2-7. Never raises on a MinerU failure —
    writes PARSE_FAILED.txt and returns a "failed" result instead, so a
    batch keeps going past one bad PDF.

    `id_override` (used by the MCP `ingest_pdf` tool's `id_hint`): when
    given, skips compute_id()'s auto-detection and uses this ID directly."""
    mineru_cmd = mineru_cmd or DEFAULT_MINERU_CMD
    pdf_path = Path(pdf_path)
    if id_override:
        computed = ComputedId(id=id_override)
    else:
        computed = compute_id(pdf_path)
    paper_id = computed.id

    dest = Path(vault_root) / "sources" / "raw" / paper_id
    paper_md = dest / "paper.md"

    if skip_existing and paper_md.exists():
        return IngestResult(id=paper_id, pdf_path=pdf_path, status="skipped")

    dest.mkdir(parents=True, exist_ok=True)
    dest_pdf = dest / "paper.pdf"
    shutil.copy2(pdf_path, dest_pdf)  # copy, never move — user keeps the original

    mineru_out = dest / "mineru-out"
    basename = dest_pdf.stem  # always "paper"
    proc = spawn(
        [
            *mineru_cmd,
            "-p",
            str(dest_pdf),
            "-o",
            str(mineru_out),
            "-f",
            "true",
            "-t",
            "true",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    output_bytes, _ = proc.communicate()
    # MinerU's output subdirectory name depends on which backend produced it
    # (e.g. "auto" for pipeline, "hybrid_auto" for hybrid-engine — the
    # current default) — search for the markdown by basename instead of
    # assuming one fixed layout, so this isn't tied to one backend/version.
    candidates = sorted(mineru_out.glob(f"**/{basename}.md"))
    parsed_md = candidates[0] if candidates else None

    if proc.returncode != 0 or parsed_md is None:
        (dest / "PARSE_FAILED.txt").write_text(
            f"mineru exited with code {proc.returncode}\n\n"
            + output_bytes.decode("utf-8", errors="replace")
        )
        shutil.rmtree(mineru_out, ignore_errors=True)
        message = f"mineru exit code {proc.returncode}"
        _append_log(vault_root, f"- INGEST FAILED {paper_id} ({pdf_path.name}) — {message}")
        return IngestResult(id=paper_id, pdf_path=pdf_path, status="failed", message=message)

    # The markdown references extracted figures via a relative "images/"
    # link sitting alongside it — move that folder too, or every image in
    # the immutable raw record ends up a dangling link.
    parsed_images_dir = parsed_md.parent / "images"
    if parsed_images_dir.is_dir():
        parsed_images_dir.replace(dest / "images")

    parsed_md.replace(paper_md)
    shutil.rmtree(mineru_out, ignore_errors=True)

    sha256 = hashlib.sha256(dest_pdf.read_bytes()).hexdigest()
    try:
        reader = PdfReader(str(dest_pdf))
        n_pages = len(reader.pages)
        pdf_title = (reader.metadata.title if reader.metadata else None) or None
    except Exception:
        n_pages = None
        pdf_title = None

    enrichment = _enrich_via_semantic_scholar(computed.arxiv_id, computed.doi)
    title = enrichment.get("title") or pdf_title or pdf_path.stem

    meta = {
        "id": paper_id,
        "title": title,
        "authors": enrichment.get("authors"),
        "year": enrichment.get("year"),
        "venue": enrichment.get("venue"),
        "doi": computed.doi,
        "arxiv_id": computed.arxiv_id,
        "sha256": sha256,
        "ingested_at": datetime.now(UTC).isoformat(),
        "n_pages": n_pages,
        "n_refs": enrichment.get("n_refs"),
    }
    (dest / "meta.json").write_text(json.dumps(meta, indent=2))

    _append_log(vault_root, f"- INGEST {paper_id} ({title}) — {n_pages} pages parsed")
    return IngestResult(id=paper_id, pdf_path=pdf_path, status="success", n_pages=n_pages)


def ingest_folder(
    folder: Path,
    vault_root: Path,
    pattern: str = "*.pdf",
    jobs: int = 1,
    skip_existing: bool = True,
    mineru_cmd: list[str] | None = None,
    show_progress: bool = True,
) -> list[IngestResult]:
    """Batch-ingest every PDF in `folder` matching `pattern`. See §7 /
    §5's `paperloom ingest` and §13's parallelism/failure-mode tests."""
    pdfs = sorted(Path(folder).glob(f"**/{pattern}"))
    results: list[IngestResult] = []

    def _run_one(pdf: Path) -> IngestResult:
        return ingest_one(pdf, vault_root, mineru_cmd=mineru_cmd, skip_existing=skip_existing)

    with Progress(disable=not show_progress) as bar:
        task = bar.add_task("Ingesting", total=len(pdfs))
        try:
            if jobs <= 1:
                for pdf in pdfs:
                    results.append(_run_one(pdf))
                    bar.update(task, advance=1)
            else:
                with ThreadPoolExecutor(max_workers=jobs) as pool:
                    futures = {pool.submit(_run_one, pdf): pdf for pdf in pdfs}
                    for future in as_completed(futures):
                        results.append(future.result())
                        bar.update(task, advance=1)
        except (KeyboardInterrupt, SystemExit) as e:
            # supervisor's own SIGINT/SIGTERM handler has already killed any
            # in-flight MinerU processes by the time this is caught — see §6.
            raise IngestAborted(len(results), len(pdfs)) from e
        except OSError as e:
            if getattr(e, "errno", None) == errno.ENOSPC or "No space left" in str(e):
                raise RuntimeError(f"Disk full after {len(results)}/{len(pdfs)} papers: {e}") from e
            raise

    return results
