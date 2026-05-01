"""
PharmGKB ingestion stub.

PharmGKB ships a Creative-Commons licensed bulk download with clinical
annotations as TSV. This script fetches the zip, walks the TSVs, and
upserts (gene, drug, level, annotation_text) tuples into Chroma.

For dev environments without internet access we ship a small mock TSV
under data/pharmgkb_sample.tsv so the pipeline still has *something* to
retrieve.
"""

from __future__ import annotations

import csv
import io
import logging
import sys
import zipfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.knowledge.vector_store import VectorStore  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("ingest.pharmgkb")

URL = "https://api.pharmgkb.org/v1/download/file/data/clinicalAnnotations.zip"


def download() -> bytes:
    log.info("Downloading PharmGKB clinical annotations …")
    r = httpx.get(URL, timeout=60.0, follow_redirects=True)
    r.raise_for_status()
    return r.content


def parse_tsv(blob: bytes) -> list[tuple[str, str, dict]]:
    out: list[tuple[str, str, dict]] = []
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        for name in zf.namelist():
            if not name.endswith(".tsv"):
                continue
            with zf.open(name) as fh:
                reader = csv.DictReader(io.TextIOWrapper(fh, "utf-8"), delimiter="\t")
                for row in reader:
                    drug = row.get("Drug", row.get("Drugs", "")).strip()
                    gene = row.get("Gene", "").strip()
                    text = row.get("Annotation Text") or row.get("PMID") or ""
                    if not drug or not gene or not text:
                        continue
                    rid = f"{gene}:{drug}:{row.get('Level of Evidence', '')}"
                    out.append((rid, text, {"gene": gene, "drug": drug, "source": "PharmGKB"}))
    return out


def main() -> None:
    try:
        blob = download()
    except Exception as e:
        log.warning("Network unavailable (%s) — falling back to data/pharmgkb_sample.tsv", e)
        sample = Path(__file__).resolve().parent.parent / "data" / "pharmgkb_sample.tsv"
        if not sample.exists():
            log.error("No sample fallback file at %s", sample)
            sys.exit(1)
        rows: list[tuple[str, str, dict]] = []
        with open(sample) as f:
            for r in csv.DictReader(f, delimiter="\t"):
                rid = f"{r['gene']}:{r['drug']}:{r.get('level', '')}"
                rows.append((rid, r["annotation"],
                            {"gene": r["gene"], "drug": r["drug"], "source": "PharmGKB"}))
    else:
        rows = parse_tsv(blob)

    log.info("Upserting %d rows into Chroma at %s", len(rows), settings.chroma_persist_dir)
    store = VectorStore()
    store.upsert(
        ids=[rid for rid, _, _ in rows],
        texts=[txt for _, txt, _ in rows],
        metadatas=[meta for _, _, meta in rows],
    )
    log.info("Done.")


if __name__ == "__main__":
    main()
