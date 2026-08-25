"""Stub CLI mimicking MinerU's interface, for test_ingest.py. Never touches
the real `mineru` package/model weights. Usage matches the subset of
MinerU's CLI that ingest.py invokes:

    fake_mineru.py -p <pdf> -o <outdir> -f true -t true

Writes <outdir>/<basename>/auto/<basename>.md and exits 0, UNLESS the input
file doesn't start with the %PDF magic bytes (simulating a MinerU crash on
a malformed PDF — checked by content, not filename, since ingest.py always
copies the source PDF to a fixed "paper.pdf" name before invoking this).
In that case it exits nonzero without writing anything. Every
invocation appends a line to --call-log (each test should point this at its
own tmp_path file for isolation) so tests can assert how many times it
actually ran.
"""

import argparse
import sys
import tempfile
from pathlib import Path

# Deliberately NOT under tests/fixtures/ (a tracked source directory) — a
# caller that forgets --call-log would otherwise leak local absolute paths
# (every invocation's -p argument) into a file git could pick up. System
# temp is the safe default for something meant to be throwaway.
DEFAULT_CALL_LOG = Path(tempfile.gettempdir()) / "paperloom_fake_mineru_calls.log"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", dest="pdf", required=True)
    ap.add_argument("-o", dest="outdir", required=True)
    ap.add_argument("-f", dest="formula", default="true")
    ap.add_argument("-t", dest="table", default="true")
    ap.add_argument("--call-log", dest="call_log", default=str(DEFAULT_CALL_LOG))
    args = ap.parse_args()

    with Path(args.call_log).open("a", encoding="utf-8") as f:
        f.write(args.pdf + "\n")

    pdf_path = Path(args.pdf)
    if pdf_path.read_bytes()[:4] != b"%PDF":
        print("fake_mineru: simulated crash on malformed input", file=sys.stderr)
        return 1

    basename = pdf_path.stem
    out_md_dir = Path(args.outdir) / basename / "auto"
    out_md_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_md_dir / "images"
    images_dir.mkdir(exist_ok=True)
    (images_dir / "fig1.jpg").write_bytes(b"\xff\xd8\xff\xd9")  # minimal fake jpeg bytes
    (out_md_dir / f"{basename}.md").write_text(
        f"# Fake parsed content\n\nParsed from {pdf_path.name} by fake_mineru.\n\n"
        f"![](images/fig1.jpg)\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
