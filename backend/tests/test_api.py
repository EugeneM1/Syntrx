"""End-to-end FastAPI route tests using TestClient."""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _upload_payload(sample_files, profile: str):
    payload = sample_files[profile].read_bytes()
    return ("file", ("genome.txt", io.BytesIO(payload), "text/plain"))


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["catalog"]["total"] > 0


def test_upload_returns_findings(sample_files):
    file = _upload_payload(sample_files, "cyp2d6_poor_metabolizer")
    r = client.post("/api/upload?use_llm=false", files=[file])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["findings"], "expected at least one finding"
    assert any(f["gene"] == "CYP2D6" for f in body["findings"])
    assert body["disclaimer"]


def test_upload_then_pdf_card(sample_files):
    file = _upload_payload(sample_files, "warfarin_sensitive_pgx_storm")
    up = client.post("/api/upload?use_llm=false", files=[file])
    rid = up.json()["id"]
    pdf = client.get(f"/api/reports/{rid}/card.pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"


def test_drug_interaction_endpoint(sample_files):
    file = _upload_payload(sample_files, "warfarin_sensitive_pgx_storm")
    rid = client.post("/api/upload?use_llm=false", files=[file]).json()["id"]
    r = client.post(
        "/api/interactions/check",
        data={"drugs": "codeine,plavix,simvastatin", "report_id": rid},
    )
    assert r.status_code == 200
    body = r.json()
    severities = {row["drug"]: row["severity"] for row in body["interactions"]}
    assert severities.get("clopidogrel") in {"warning", "avoid"}
    assert severities.get("simvastatin") in {"warning", "avoid"}


def test_upload_empty_file_rejected():
    r = client.post("/api/upload", files=[("file", ("empty.txt", b"", "text/plain"))])
    assert r.status_code == 400


def test_known_drugs_endpoint():
    r = client.get("/api/interactions/drugs")
    assert r.status_code == 200
    drugs = r.json()
    assert "codeine" in drugs and "clopidogrel" in drugs
