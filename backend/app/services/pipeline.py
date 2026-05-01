"""
Pipeline orchestrator.

Runs the four agents in order and returns a single `Report` object plus
a per-stage trace. The trace is exposed via the API so the frontend can
show a real "Parsing → Looking up → Synthesizing → Safety check" timeline.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

UTC = timezone.utc

from app.agents.base import AgentStep
from app.agents.lookup_agent import LookupAgent
from app.agents.parser_agent import ParserAgent, ParserInput
from app.agents.safety_agent import SafetyAgent
from app.agents.synthesis_agent import SynthesisAgent, SynthesisInput
from app.core.parser import ParseResult
from app.core.phenotype import Phenotype, call_phenotypes
from app.core.recommendations import Finding, group_by_domain
from app.core.snp_catalog import summary as catalog_summary


@dataclass
class Report:
    id: str
    created_at: str
    parse: ParseResult
    findings: list[Finding]
    narratives: dict[str, str]
    disclaimer: str
    phenotypes: dict[str, Phenotype] = field(default_factory=dict)
    trace: list[AgentStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "parse": {
                "file_format": self.parse.file_format.value,
                "total_variants": self.parse.total_variants,
                "matched_variants": self.parse.matched_variants,
                "no_calls": self.parse.no_calls,
                "coverage_pct": round(self.parse.coverage_pct, 1),
            },
            "catalog": catalog_summary(),
            "phenotypes": {
                gene: {
                    "gene": p.gene,
                    "diplotype": p.diplotype,
                    "phenotype": p.phenotype,
                    "activity_score": p.activity_score,
                    "confidence": p.confidence.value,
                    "source": p.source,
                }
                for gene, p in self.phenotypes.items()
            },
            "findings": [f.to_dict() for f in self.findings],
            "by_domain": {k: [f.to_dict() for f in v] for k, v in group_by_domain(self.findings).items()},
            "narratives": self.narratives,
            "disclaimer": self.disclaimer,
            "trace": [asdict(s) for s in self.trace],
        }


def run_pipeline(payload: bytes, *, filename: str = "upload.txt", use_llm: bool = True) -> Report:
    trace: list[AgentStep] = []

    parser = ParserAgent()
    parsed, step1 = parser(ParserInput(payload=payload, filename=filename))
    trace.append(step1)

    lookup = LookupAgent()
    lookup_out, step2 = lookup(parsed.genotypes)
    trace.append(step2)

    phenos = call_phenotypes(parsed.genotypes)
    synth = SynthesisAgent(use_llm=use_llm)
    synth_out, step3 = synth(SynthesisInput(parsed.genotypes, phenos, lookup_out))
    trace.append(step3)

    safety = SafetyAgent()
    safe_out, step4 = safety(synth_out)
    trace.append(step4)

    return Report(
        id=str(uuid.uuid4()),
        created_at=datetime.now(UTC).isoformat(),
        parse=parsed,
        findings=safe_out.findings,
        narratives=safe_out.narratives,
        disclaimer=safe_out.global_disclaimer,
        phenotypes=phenos,
        trace=trace,
    )
