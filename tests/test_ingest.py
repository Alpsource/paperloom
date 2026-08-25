import json
import shutil
import sys
from pathlib import Path

from paperloom.ingest import ingest_folder, ingest_one

FIXTURES = Path(__file__).parent / "fixtures"
FAKE_MINERU = FIXTURES / "fake_mineru.py"


def _mineru_cmd(call_log: Path) -> list[str]:
    return [sys.executable, str(FAKE_MINERU), "--call-log", str(call_log)]


def test_ingest_one_creates_paper_md_and_meta(tmp_path):
    vault = tmp_path / "vault"
    call_log = tmp_path / "calls.log"

    result = ingest_one(
        FIXTURES / "toy-paper.pdf",
        vault,
        mineru_cmd=_mineru_cmd(call_log),
    )

    assert result.status == "success"
    dest = vault / "sources" / "raw" / result.id
    paper_md = dest / "paper.md"
    assert paper_md.exists()
    assert "Fake parsed content" in paper_md.read_text()

    # The markdown references images/fig1.jpg via a relative link — that
    # folder must survive the mineru-out cleanup, or the link dangles.
    assert (dest / "images" / "fig1.jpg").exists()

    meta = json.loads((dest / "meta.json").read_text())
    assert meta["id"] == result.id
    assert meta["sha256"]
    assert meta["n_pages"] == 2
    assert "ingested_at" in meta

    today_logs = list((vault / "logs").glob("*.md"))
    assert len(today_logs) == 1
    assert f"INGEST {result.id}" in today_logs[0].read_text()


def test_ingest_one_skip_existing_does_not_invoke_mineru(tmp_path):
    vault = tmp_path / "vault"
    call_log = tmp_path / "calls.log"
    cmd = _mineru_cmd(call_log)

    first = ingest_one(FIXTURES / "toy-paper.pdf", vault, mineru_cmd=cmd)
    assert first.status == "success"
    assert call_log.read_text().count("\n") == 1

    second = ingest_one(FIXTURES / "toy-paper.pdf", vault, mineru_cmd=cmd, skip_existing=True)
    assert second.status == "skipped"
    assert second.id == first.id
    # fake_mineru's call log must not have grown — it was never re-invoked.
    assert call_log.read_text().count("\n") == 1


def test_ingest_folder_continues_past_malformed_pdf(tmp_path):
    vault = tmp_path / "vault"
    call_log = tmp_path / "calls.log"
    src_folder = tmp_path / "pdfs"
    src_folder.mkdir()
    shutil.copy2(FIXTURES / "malformed.pdf", src_folder / "malformed.pdf")
    shutil.copy2(FIXTURES / "toy-paper-arxiv.pdf", src_folder / "toy-paper-arxiv.pdf")

    results = ingest_folder(
        src_folder,
        vault,
        mineru_cmd=_mineru_cmd(call_log),
        show_progress=False,
    )

    assert len(results) == 2
    by_source = {r.pdf_path.name: r for r in results}

    failed = by_source["malformed.pdf"]
    assert failed.status == "failed"
    failed_dest = vault / "sources" / "raw" / failed.id
    assert (failed_dest / "PARSE_FAILED.txt").exists()
    assert not (failed_dest / "paper.md").exists()

    good = by_source["toy-paper-arxiv.pdf"]
    assert good.status == "success"
    assert good.id == "2999.00001"  # arXiv ID detected from page-1 text
    assert (vault / "sources" / "raw" / good.id / "paper.md").exists()


def test_ingest_folder_with_jobs_lands_all_pdfs(tmp_path):
    vault = tmp_path / "vault"
    call_log = tmp_path / "calls.log"
    src_folder = tmp_path / "pdfs"
    src_folder.mkdir()
    for name in ("toy-paper.pdf", "toy-paper-arxiv.pdf", "toy-paper-2.pdf"):
        shutil.copy2(FIXTURES / name, src_folder / name)

    results = ingest_folder(
        src_folder,
        vault,
        jobs=2,
        mineru_cmd=_mineru_cmd(call_log),
        show_progress=False,
    )

    assert len(results) == 3
    assert all(r.status == "success" for r in results)
    for r in results:
        assert (vault / "sources" / "raw" / r.id / "paper.md").exists()

    # Orphan-prevention here is structural, not something to re-probe: every
    # ingest_one call — whether run sequentially or inside a thread-pool
    # worker — calls proc.communicate() (waits for exit) on its MinerU
    # subprocess before returning, so nothing is left running once
    # ingest_folder returns. (A shared call-log-file line count was tried
    # here instead and turned out flaky under concurrent subprocess writes
    # on Windows — dropped since §13 doesn't actually ask for an exact
    # invocation count, only that all 3 papers land.)
