"""Request and response models for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class InteractionRequest(BaseModel):
    drugs: list[str] = Field(..., min_length=1, max_length=20)
    report_id: str | None = None
    payload: bytes | None = None  # raw genetic file (base64-decoded by FastAPI)


class HealthResponse(BaseModel):
    status: str
    catalog: dict[str, int]
    llm_provider: str


class ReportSummary(BaseModel):
    id: str
    created_at: str
    matched_variants: int
    finding_count: int
    headline: str | None = None
