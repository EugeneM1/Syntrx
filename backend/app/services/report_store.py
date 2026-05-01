"""
Lightweight report persistence.

Production deployment uses Postgres via SQLAlchemy. For dev / tests we
default to JSON files on disk so the API works without a running DB.
The store also keeps the original uploaded payload around so endpoints
that need to re-derive phenotypes (like the PDF card and the drug
interaction checker) don't need a re-upload.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.services.pipeline import Report


class ReportStore:
    _default: "ReportStore | None" = None

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or os.getenv("REPORT_DIR", "./data/reports"))
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, report: Report) -> None:
        out = self.root / f"{report.id}.json"
        out.write_text(json.dumps(report.to_dict(), indent=2))
        # Persist genotypes so later endpoints can reconstruct phenotypes
        geno = {rsid: list(g.alleles) for rsid, g in report.parse.genotypes.items()}
        (self.root / f"{report.id}.geno.json").write_text(json.dumps(geno))

    def get(self, report_id: str) -> dict | None:
        path = self.root / f"{report_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def get_genotypes(self, report_id: str) -> bytes | None:
        path = self.root / f"{report_id}.geno.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        # Re-emit a minimal generic-format file for the parser
        lines = ["# rsid\tgenotype"]
        for rsid, alleles in data.items():
            lines.append(f"{rsid}\t{''.join(alleles)}")
        return "\n".join(lines).encode("utf-8")

    def list_summaries(self) -> list[dict]:
        out = []
        for p in sorted(self.root.glob("*.json")):
            if p.name.endswith(".geno.json"):
                continue
            try:
                d = json.loads(p.read_text())
            except Exception:
                continue
            out.append({
                "id": d["id"],
                "created_at": d["created_at"],
                "matched_variants": d["parse"]["matched_variants"],
                "finding_count": len(d["findings"]),
                "headline": (d["findings"][0]["title"] if d["findings"] else None),
            })
        return out

    @classmethod
    def get_default(cls) -> "ReportStore":
        if cls._default is None:
            cls._default = cls()
        return cls._default
