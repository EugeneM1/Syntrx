"""
Stage 3 — Synthesis Agent.

Wraps the deterministic recommendation engine and (optionally) calls the
LLM to add a 1–2 sentence personalized "narrator" voice on top of each
finding. The LLM never overrides the deterministic output: it only adds
a `narrative` string that gets shown next to the actions.

Confidence tiering and citations are unchanged from the deterministic engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core import recommendations
from app.core.parser import Genotype
from app.core.phenotype import Phenotype
from app.services.llm import LLMProvider, get_llm

from .base import Agent
from .lookup_agent import LookupOutput


@dataclass
class SynthesisInput:
    genotypes: dict[str, Genotype]
    phenotypes: dict[str, Phenotype]
    lookup: LookupOutput


@dataclass
class SynthesisOutput:
    findings: list[recommendations.Finding] = field(default_factory=list)
    narratives: dict[str, str] = field(default_factory=dict)   # finding.id → text


SYS_PROMPT = (
    "You are Syntrx's plain-language narrator. You will be given a clinical "
    "finding from a deterministic pharmacogenomics engine and a few research "
    "snippets. Write 1–2 friendly sentences that put the finding into the "
    "user's everyday life. Do not change any clinical claim. Do not add new "
    "advice. Do not invent dosages. Do not promise outcomes. Keep it concrete."
)


class SynthesisAgent(Agent[SynthesisInput, SynthesisOutput]):
    name = "synthesis"

    def __init__(self, llm: LLMProvider | None = None, *, use_llm: bool = True):
        self.llm = llm or get_llm()
        self.use_llm = use_llm

    def run(self, input_data: SynthesisInput) -> SynthesisOutput:
        findings = recommendations.generate_findings(input_data.genotypes, input_data.phenotypes)
        out = SynthesisOutput(findings=findings)

        if not self.use_llm:
            return out

        for f in findings:
            user = (
                f"Finding: {f.title}\n"
                f"Headline: {f.summary}\n"
                f"Detail: {f.detail}\n"
                f"Actions:\n- " + "\n- ".join(f.actions) + "\n"
                f"Confidence: {f.confidence.value}\n"
                f"Sources: {', '.join(f.evidence)}\n"
            )
            try:
                txt = self.llm.complete(SYS_PROMPT, user, max_tokens=160, temperature=0.3)
                out.narratives[f.id] = txt.strip()
            except Exception as e:  # network failure, missing key, etc.
                out.narratives[f.id] = ""
                # Re-raise only if the user explicitly chose a real provider
                if self.llm.name not in {"mock"}:
                    out.narratives[f.id] = f"[narration unavailable: {type(e).__name__}]"
        return out

    def describe(self, output: SynthesisOutput) -> str:
        return f"{len(output.findings)} findings, narrator={self.llm.name}"

    def metadata(self, output: SynthesisOutput) -> dict:
        return {"findings": len(output.findings), "llm": self.llm.name}
