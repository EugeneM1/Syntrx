"""Upload + report endpoints."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse, Response

from app.core.parser import ParseError, parse_bytes
from app.core.phenotype import call_phenotypes
from app.services.pdf import render_card
from app.services.pipeline import Report, run_pipeline
from app.services.report_store import ReportStore

router = APIRouter(tags=["reports"])
_store = ReportStore.get_default()


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    use_llm: bool = Query(default=True, description="Disable to skip the LLM narration step."),
) -> JSONResponse:
    if not file.filename:
        raise HTTPException(400, "No filename")
    payload = await file.read()
    if not payload:
        raise HTTPException(400, "Empty upload")
    if len(payload) > 50 * 1024 * 1024:
        raise HTTPException(413, "File too large (50 MB max)")
    try:
        report = run_pipeline(payload, filename=file.filename, use_llm=use_llm)
    except ParseError as e:
        # PDF / format issues — surface as a friendly 400, not 500
        raise HTTPException(400, str(e)) from e
    _store.save(report)
    return JSONResponse(report.to_dict())


@router.get("/reports/{report_id}")
def get_report(report_id: str) -> dict:
    rep = _store.get(report_id)
    if not rep:
        raise HTTPException(404, "Report not found")
    return rep


@router.get("/reports")
def list_reports() -> list[dict]:
    return _store.list_summaries()


@router.get("/reports/{report_id}/card.pdf")
def pharmacogenomic_card(report_id: str) -> Response:
    """Return the printable PDF card for a saved report."""
    raw = _store.get_genotypes(report_id)
    rep_dict = _store.get(report_id)
    if not raw or not rep_dict:
        raise HTTPException(404, "Report not found")
    parsed = parse_bytes(raw)
    phenos = call_phenotypes(parsed.genotypes)
    findings = []
    for f in rep_dict["findings"]:
        # Reconstruct minimal Finding-like obj for the renderer
        findings.append(_FindingShim(**f))
    pdf = render_card(phenos, findings)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="syntrx_card_{report_id[:8]}.pdf"'},
    )


@router.post("/preview")
async def preview(file: UploadFile = File(...)) -> dict:
    """Run the deterministic engine only — fast, no LLM call. Useful for tests."""
    payload = await file.read()
    if not payload:
        raise HTTPException(400, "Empty upload")
    rep: Report = run_pipeline(payload, filename=file.filename or "upload.txt", use_llm=False)
    return rep.to_dict()


# --- Shim so the PDF renderer can stay typed ----------------------------------

class _FindingShim:
    def __init__(self, **kw):
        self.id = kw.get("id", "")
        self.gene = kw.get("gene", "")
        self.title = kw.get("title", "")
        self.summary = kw.get("summary", "")
        self.detail = kw.get("detail", "")
        self.actions = kw.get("actions", [])
        self.evidence = kw.get("evidence", [])
        self.related_drugs = kw.get("related_drugs", [])
        self.related_nutrients = kw.get("related_nutrients", [])
        self.diplotype = kw.get("diplotype")
        self.activity_score = kw.get("activity_score")
        self.requires_physician = kw.get("requires_physician", False)

        class _Conf:
            def __init__(self, v): self.value = v
        self.confidence = _Conf(kw.get("confidence", "moderate"))

        class _Dom:
            def __init__(self, v): self.value = v
        self.domain = _Dom(kw.get("domain", "drug_metabolism"))
