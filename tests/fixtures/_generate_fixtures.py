"""One-off generator for the tiny hand-crafted PDF fixtures used by
test_ingest.py. Run with `python tests/fixtures/_generate_fixtures.py` to
regenerate. Not collected by pytest (leading underscore) and not imported
at test time — the committed .pdf outputs are what tests actually use."""

from pathlib import Path

HERE = Path(__file__).parent


def _make_pdf(pages_text: list[str]) -> bytes:
    n_pages = len(pages_text)
    catalog_num = 1
    pages_num = 2
    page_nums = list(range(3, 3 + n_pages))
    content_nums = list(range(3 + n_pages, 3 + 2 * n_pages))
    font_num = 3 + 2 * n_pages

    objects: list[tuple[int, str]] = []
    kids = " ".join(f"{n} 0 R" for n in page_nums)
    objects.append((catalog_num, f"<< /Type /Catalog /Pages {pages_num} 0 R >>"))
    objects.append((pages_num, f"<< /Type /Pages /Kids [{kids}] /Count {n_pages} >>"))
    for i, pnum in enumerate(page_nums):
        cnum = content_nums[i]
        objects.append(
            (
                pnum,
                f"<< /Type /Page /Parent {pages_num} 0 R "
                f"/Resources << /Font << /F1 {font_num} 0 R >> >> "
                f"/MediaBox [0 0 612 792] /Contents {cnum} 0 R >>",
            )
        )
    for i, cnum in enumerate(content_nums):
        text = pages_text[i].replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream = f"BT /F1 18 Tf 72 700 Td ({text}) Tj ET"
        objects.append((cnum, f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream"))
    objects.append((font_num, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    objects.sort(key=lambda o: o[0])

    out = bytearray()
    out += b"%PDF-1.4\n"
    offsets: dict[int, int] = {}
    for num, body in objects:
        offsets[num] = len(out)
        out += f"{num} 0 obj\n{body}\nendobj\n".encode("latin-1")

    xref_offset = len(out)
    max_num = max(offsets)
    out += f"xref\n0 {max_num + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for num in range(1, max_num + 1):
        off = offsets.get(num, 0)
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {max_num + 1} /Root {catalog_num} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode()
    return bytes(out)


def main() -> None:
    (HERE / "toy-paper.pdf").write_bytes(
        _make_pdf(["Toy Paper Title", "Second page of the toy paper."])
    )
    (HERE / "toy-paper-arxiv.pdf").write_bytes(
        _make_pdf(["arXiv:2999.00001 Toy ArXiv Paper Title"])
    )
    (HERE / "toy-paper-2.pdf").write_bytes(
        _make_pdf(["A third distinct toy paper, for the --jobs parallelism test."])
    )
    (HERE / "malformed.pdf").write_bytes(b"this is not a real pdf, just garbage bytes\x00\x01\x02")
    print("Generated toy-paper.pdf, toy-paper-arxiv.pdf, toy-paper-2.pdf, malformed.pdf")


if __name__ == "__main__":
    main()
