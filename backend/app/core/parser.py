"""
Genetic file parser.

Reads raw consumer-genetics files and returns the user's genotype at each
SNP in the curated catalog. Supports:

* 23andMe v3 / v4 / v5 (tab-separated; columns rsid, chromosome, position, genotype)
* AncestryDNA v1 / v2 (tab-separated; columns rsid, chromosome, position, allele1, allele2)
* PDF reports (e.g. third-party pharmacogenomic results) — text is
  extracted with pypdf and rsid + genotype pairs are mined out with a
  permissive regex.
* "Generic" raw format (rsid <tab> genotype) for synthetic test fixtures.

The parser tolerates:

* Header comment blocks (`# ...`)
* Quote characters around alleles (Ancestry encloses each allele in `"`)
* No-call values: "--", "00", "NN" — represented as `None` in the result
* Indel notations like "I/D" or "DD" — preserved as-is
* Mitochondrial chromosome reported as "M", "MT", or "mt"
* Both Unix and Windows line endings

Allele orientation: 23andMe and AncestryDNA both report on the positive
(forward) strand, so we do not flip alleles. Star-allele callers in
`phenotype.py` assume positive-strand input.
"""

from __future__ import annotations

import gzip
import io
import re
import zipfile
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from . import snp_catalog


class FileFormat(str, Enum):
    TWENTY_THREE_AND_ME = "23andme"
    ANCESTRY = "ancestry"
    GENERIC = "generic"
    PDF = "pdf"
    UNKNOWN = "unknown"


class ParseError(ValueError):
    """Raised when a file is recognized but no usable genetic data is found."""


NO_CALL_TOKENS = frozenset({"--", "00", "0", "NN", "N", ""})


@dataclass(frozen=True)
class Genotype:
    rsid: str
    chromosome: str
    position: int
    alleles: tuple[str, ...]   # 1 element for haploid (mtDNA, male X), 2 otherwise

    @property
    def is_no_call(self) -> bool:
        return any(a is None or a in NO_CALL_TOKENS for a in self.alleles)

    @property
    def diplotype(self) -> str:
        """Sorted, joined string for stable equality (e.g. 'AC' not 'CA')."""
        return "".join(sorted(self.alleles))


@dataclass(frozen=True)
class ParseResult:
    """The output of a successful parse."""

    file_format: FileFormat
    total_variants: int
    matched_variants: int        # how many of TARGET_RSIDS we found
    no_calls: int
    genotypes: dict[str, Genotype]  # rsid → Genotype, only for TARGET_RSIDS

    @property
    def coverage_pct(self) -> float:
        if not snp_catalog.TARGET_RSIDS:
            return 0.0
        return 100.0 * self.matched_variants / len(snp_catalog.TARGET_RSIDS)


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def parse_file(path: str | Path) -> ParseResult:
    """Parse a raw genetic file from disk. Auto-detects gzip and zip."""
    p = Path(path)
    data = _read_bytes(p)
    return parse_bytes(data)


def parse_bytes(data: bytes) -> ParseResult:
    """Parse raw bytes (handy for HTTP uploads). Auto-detects gzip / zip / pdf."""
    if data[:5] == b"%PDF-":
        text = _extract_pdf_text(data)
        normalized = _normalize_loose_text(text)
        # `_normalize_loose_text` always emits 2 header lines; real markers add more.
        n_data_lines = max(0, len([ln for ln in normalized.splitlines()
                                   if ln and not ln.startswith("#")]))
        if n_data_lines == 0:
            raise ParseError(
                "Couldn't find any genetic markers in this PDF. "
                "Syntrx looks for rsID + genotype pairs (e.g. 'rs1801133 CT'). "
                "Most consumer-DNA reports include these on a 'health' or 'raw data' page."
            )
        result = parse_text(normalized)
        if result.matched_variants == 0:
            raise ParseError(
                f"Found {n_data_lines} rsID(s) in the PDF, but none of them "
                "are in Syntrx's clinically actionable catalog. Try uploading the "
                "raw data file from your testing provider rather than a results PDF."
            )
        # Tag the format so the UI shows the right pipeline label
        return ParseResult(
            file_format=FileFormat.PDF,
            total_variants=result.total_variants,
            matched_variants=result.matched_variants,
            no_calls=result.no_calls,
            genotypes=result.genotypes,
        )
    text = _maybe_decompress(data).decode("utf-8", errors="replace")
    return parse_text(text)


def parse_text(text: str) -> ParseResult:
    """Parse the textual contents of a raw genetic file."""
    lines = text.splitlines()
    fmt = detect_format(lines)
    target = snp_catalog.TARGET_RSIDS

    matched: dict[str, Genotype] = {}
    total = 0
    no_calls = 0

    for row in _iter_rows(lines, fmt):
        total += 1
        if row.rsid not in target:
            continue
        if row.is_no_call:
            no_calls += 1
        matched[row.rsid] = row

    return ParseResult(
        file_format=fmt,
        total_variants=total,
        matched_variants=len(matched),
        no_calls=no_calls,
        genotypes=matched,
    )


# ---------------------------------------------------------------------------
# Format detection
# ---------------------------------------------------------------------------

def detect_format(lines: Iterable[str]) -> FileFormat:
    """Sniff the file format from comment headers + first data line."""
    header_text = ""
    first_data: list[str] | None = None

    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            header_text += s.lower() + "\n"
            continue
        first_data = s.split("\t")
        break

    if "23andme" in header_text:
        return FileFormat.TWENTY_THREE_AND_ME
    if "ancestry" in header_text or "ancestrydna" in header_text:
        return FileFormat.ANCESTRY

    if first_data is None:
        return FileFormat.UNKNOWN
    n = len(first_data)
    if n == 4:
        return FileFormat.TWENTY_THREE_AND_ME
    if n == 5:
        return FileFormat.ANCESTRY
    if n == 2:
        return FileFormat.GENERIC
    return FileFormat.UNKNOWN


# ---------------------------------------------------------------------------
# Row iteration
# ---------------------------------------------------------------------------

def _iter_rows(lines: Iterable[str], fmt: FileFormat) -> Iterator[Genotype]:
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#") or s.startswith("rsid"):
            continue
        # Strip quotes around fields (AncestryDNA quirk)
        s = s.replace('"', "")

        cols = s.split("\t")
        try:
            if fmt == FileFormat.TWENTY_THREE_AND_ME and len(cols) >= 4:
                rsid, chrom, pos, gt = cols[0], cols[1], cols[2], cols[3]
                alleles = _split_genotype(gt, chrom)
            elif fmt == FileFormat.ANCESTRY and len(cols) >= 5:
                rsid, chrom, pos, a1, a2 = cols[0], cols[1], cols[2], cols[3], cols[4]
                alleles = _split_genotype(a1 + a2, chrom)
            elif fmt == FileFormat.GENERIC and len(cols) >= 2:
                rsid, gt = cols[0], cols[-1]
                chrom, pos = "?", "0"
                alleles = _split_genotype(gt, chrom)
            else:
                # Unknown row width — best-effort: assume 23andMe.
                if len(cols) < 4:
                    continue
                rsid, chrom, pos, gt = cols[0], cols[1], cols[2], cols[3]
                alleles = _split_genotype(gt, chrom)
        except ValueError:
            continue

        if not rsid.startswith("rs") and not rsid.startswith("i"):
            # Skip ancestry-internal IDs unless we've curated them
            if rsid not in snp_catalog.TARGET_RSIDS:
                continue
        try:
            position = int(pos)
        except (TypeError, ValueError):
            position = 0

        yield Genotype(
            rsid=rsid,
            chromosome=_normalize_chromosome(chrom),
            position=position,
            alleles=alleles,
        )


def _split_genotype(gt: str, chromosome: str) -> tuple[str, ...]:
    """Split a 23andMe-style 'AG' / 'AA' / '--' string into per-allele tuple.

    For mitochondrial DNA and male X/Y, only one allele is meaningful.
    """
    gt = (gt or "").strip().upper()
    chrom = (chromosome or "").upper()

    if gt in NO_CALL_TOKENS:
        return (gt or "--",)

    # Indel calls (some 23andMe rows): 'I', 'D', 'II', 'DD', 'ID'
    if gt in {"I", "D"}:
        return (gt,)
    if gt in {"II", "DD", "ID", "DI"}:
        return tuple(gt)

    # Haploid chromosomes
    if chrom in {"M", "MT", "Y"}:
        return (gt[0],) if len(gt) >= 1 else ("--",)

    if len(gt) == 1:
        return (gt,)
    if len(gt) == 2:
        return (gt[0], gt[1])
    # Longer allele strings (rare, usually multi-base indels) — return whole
    return (gt,)


def _normalize_chromosome(c: str) -> str:
    c = (c or "").strip().upper()
    if c in {"MT", "M"}:
        return "MT"
    if c.startswith("CHR"):
        c = c[3:]
    return c or "?"


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _read_bytes(p: Path) -> bytes:
    return p.read_bytes()


def _maybe_decompress(data: bytes) -> bytes:
    """Transparently handle .gz and .zip uploads (very common from 23andMe)."""
    if data[:2] == b"\x1f\x8b":  # gzip magic
        return gzip.decompress(data)
    if data[:2] == b"PK":  # zip magic
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            # Take the first non-directory member — usually the only one
            for name in zf.namelist():
                if not name.endswith("/"):
                    return zf.read(name)
    return data


# ---------------------------------------------------------------------------
# PDF support
# ---------------------------------------------------------------------------

# Two patterns: locate each rsID, then look ahead on the same line for a
# genotype-shaped token. This is more robust than a single mega-regex because
# real PDF tables interleave chromosome/position columns between the rsID and
# the genotype.
_RSID_RE = re.compile(r"\b(rs\d{2,12})\b", re.IGNORECASE)
# No `\b` anchors — they don't fire on punctuation like `--`. We use
# `fullmatch` against an already-tokenized chunk so the regex itself
# only validates *shape*.
_GENOTYPE_TOKEN_RE = re.compile(
    r"([ACGT]{2}|[ACGT]|--|00|II|DD|ID|DI|NN)",
    re.IGNORECASE,
)
# Used to skip purely numeric tokens like chromosome position columns
_NUMERIC_TOKEN_RE = re.compile(r"^\d+$")

# Some PDFs report star alleles directly (e.g. "CYP2D6: *1/*4"). We expose
# that information so the API can return a useful error message even when
# raw rsIDs are absent.
_STAR_ALLELE_RE = re.compile(r"\b(CYP\w+|TPMT|UGT1A1|SLCO1B1|VKORC1|DPYD)\s*[:=]?\s*(\*\d+(?:/\*\d+)?)")


def _extract_pdf_text(data: bytes) -> str:
    """Pull text out of every page of a PDF. Returns empty string on failure."""
    try:
        from pypdf import PdfReader  # imported lazily so non-PDF runs don't pay the cost
    except ImportError as e:
        raise ParseError(
            "PDF support is not installed. Run `pip install pypdf>=5.0.0` "
            "(or `pip install -r requirements.txt`) and try again."
        ) from e

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                raise ParseError(
                    "This PDF is password-protected. Decrypt it (e.g. via Preview "
                    "→ Export) and re-upload."
                )
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text() or "")
            except Exception:
                # Skip pages with unsupported content streams instead of failing
                continue
        return "\n".join(pages)
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Could not read PDF: {type(e).__name__}: {e}") from e


def _normalize_loose_text(text: str) -> str:
    """Mine rsID + genotype pairs out of arbitrary text.

    For each rsID we look at the text up to the next rsID (or 80 chars,
    whichever comes first), and pull the first genotype-shaped token,
    skipping purely numeric tokens (chromosome / position columns).
    First occurrence of each rsID wins.

    Returns a synthetic 23andMe-format stream that the existing parser
    consumes.
    """
    matches = list(_RSID_RE.finditer(text))
    seen: dict[str, str] = {}
    for i, m in enumerate(matches):
        rsid = m.group(1).lower()
        if rsid in seen:
            continue
        # Window: between this rsID and the next (or 80 chars cap)
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        end = min(m.end() + 80, next_start)
        tail = text[m.end():end].split("\n", 1)[0]
        gt = _first_genotype_token(tail)
        if gt:
            seen[rsid] = gt

    out_lines = ["# extracted from pdf", "# rsid\tchromosome\tposition\tgenotype"]
    for rsid, gt in seen.items():
        out_lines.append(f"{rsid}\t?\t0\t{gt}")
    return "\n".join(out_lines) + "\n"


def _first_genotype_token(text: str) -> str | None:
    """Return the first genotype-shaped token in `text`, ignoring numerics.

    Genotype-shaped means: 2 nucleotides (CT, AA), a no-call (--, 00, NN),
    or an indel marker (II, DD, ID). Numeric tokens like '11856378' (a
    chromosomal position) are skipped explicitly. We split on whitespace
    rather than using `\\b` word boundaries because `--` has no word
    boundary on either side.
    """
    for tok in re.split(r"[\s,;|()]+", text):
        s = tok.strip(":.>=")
        if not s:
            continue
        # Check genotype shape FIRST — '00' (no-call) looks numeric but is
        # a valid genotype token, so it must take precedence.
        if _GENOTYPE_TOKEN_RE.fullmatch(s):
            return s.upper()
        if _NUMERIC_TOKEN_RE.match(s):
            continue
    return None


def detected_star_alleles(text: str) -> dict[str, str]:
    """Parse 'CYP2D6 *1/*4' style snippets out of free text."""
    return {m.group(1).upper(): m.group(2) for m in _STAR_ALLELE_RE.finditer(text)}
