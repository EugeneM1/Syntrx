"""Drug-interaction checker endpoint."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.parser import parse_bytes
from app.core.phenotype import call_phenotypes
from app.services.interactions import check, known_drugs
from app.services.report_store import ReportStore

router = APIRouter(tags=["interactions"])
_store = ReportStore.get_default()


@router.get("/interactions/drugs")
def known() -> list[str]:
    return known_drugs()


@router.post("/interactions/check")
async def check_drugs(
    drugs: str = Form(..., description="Comma-separated drug names"),
    report_id: str | None = Form(default=None),
    file: UploadFile | None = File(default=None),
) -> dict:
    drug_list = [d.strip() for d in drugs.split(",") if d.strip()]
    if not drug_list:
        raise HTTPException(400, "Provide at least one drug")

    if report_id:
        raw = _store.get_genotypes(report_id)
        if not raw:
            raise HTTPException(404, "Report not found")
        parsed = parse_bytes(raw)
    elif file:
        payload = await file.read()
        parsed = parse_bytes(payload)
    else:
        raise HTTPException(400, "Provide either report_id or file")

    phenos = call_phenotypes(parsed.genotypes)
    interactions = check(drug_list, phenos)
    return {
        "drugs": drug_list,
        "interactions": [asdict(i) for i in interactions],
        "summary": {
            "avoid": sum(1 for i in interactions if i.severity == "avoid"),
            "warning": sum(1 for i in interactions if i.severity == "warning"),
            "caution": sum(1 for i in interactions if i.severity == "caution"),
            "info": sum(1 for i in interactions if i.severity == "info"),
        },
    }
