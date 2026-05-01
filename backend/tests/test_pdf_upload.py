"""PDF upload — text extraction + loose rsID matching."""

import io

import pytest

from app.core import parser

reportlab = pytest.importorskip("reportlab")
pypdf = pytest.importorskip("pypdf")


def _make_pdf(lines: list[str]) -> bytes:
    """Build a tiny PDF in memory."""
    from reportlab.lib.pagesizes import LETTER
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=LETTER)
    y = 750
    for line in lines:
        c.drawString(72, y, line)
        y -= 14
        if y < 72:
            c.showPage()
            y = 750
    c.save()
    return buf.getvalue()


def test_pdf_with_rsid_genotype_pairs_parses():
    blob = _make_pdf([
        "Pharmacogenomic Test Report — Patient 12345",
        "",
        "rs1801133  CT     (MTHFR C677T)",
        "rs9923231  GA     (VKORC1)",
        "rs4244285  AA     (CYP2C19 *2)",
        "rs1815739  TT     (ACTN3 R577X)",
    ])
    res = parser.parse_bytes(blob)
    assert res.file_format == parser.FileFormat.PDF
    assert "rs1801133" in res.genotypes
    assert res.genotypes["rs1801133"].diplotype == "CT"
    assert res.genotypes["rs4244285"].diplotype == "AA"
    assert res.matched_variants == 4


def test_pdf_with_no_genetic_data_raises_friendly_error():
    blob = _make_pdf([
        "Welcome to Acme Genomics",
        "Your test results are attached.",
        "Please contact your physician for interpretation.",
    ])
    with pytest.raises(parser.ParseError) as ei:
        parser.parse_bytes(blob)
    assert "rsID" in str(ei.value) or "genetic markers" in str(ei.value)


def test_pdf_loose_match_handles_alt_separators():
    blob = _make_pdf([
        "rs1801133: CT",
        "rs9923231 -> GA",
        "rs601338 = AA",
    ])
    res = parser.parse_bytes(blob)
    assert "rs1801133" in res.genotypes
    assert "rs9923231" in res.genotypes
    assert "rs601338" in res.genotypes


def test_loose_normalize_dedupes_repeated_rsids():
    text = "rs1801133 CT noise noise rs1801133 TT"
    out = parser._normalize_loose_text(text)
    # First occurrence wins
    assert out.count("rs1801133") == 1
    assert "rs1801133\t?\t0\tCT" in out
