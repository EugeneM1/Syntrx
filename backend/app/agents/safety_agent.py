"""
Stage 4 — Safety Agent.

Applies hard rules to the assembled report:

1. Any finding with `requires_physician=True` gets a standard disclaimer
   appended to its `actions`.
2. Strip any LLM narration that contains diagnostic language ("you have
   X disease", "you will develop", "prescribe X mg") — these slip past
   the synthesis prompt occasionally.
3. Add the global Syntrx disclaimer to the report header.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.recommendations import Finding

from .base import Agent
from .synthesis_agent import SynthesisOutput

DIAGNOSTIC_PATTERNS = [
    r"\byou (have|will (develop|get))\b",
    r"\bI diagnose\b",
    r"\btake \d+\s?mg\b",
    r"\bprescribe(s|d)? you\b",
    r"\bstart taking\b",
]
_DIAG_RE = re.compile("|".join(DIAGNOSTIC_PATTERNS), re.IGNORECASE)

PHYSICIAN_DISCLAIMER = (
    "Bring this finding to your prescriber before changing or starting any medication. "
    "Syntrx is a literacy tool, not a clinical decision-maker."
)

GLOBAL_DISCLAIMER = (
    "Syntrx is a genetic literacy and wellness tool. It does not diagnose disease, "
    "prescribe medication, or replace medical advice. All findings cite peer-reviewed "
    "research and CPIC guidelines; consult a clinician before acting on them."
)


@dataclass
class SafetyOutput:
    findings: list[Finding]
    narratives: dict[str, str]
    global_disclaimer: str = GLOBAL_DISCLAIMER
    flags: list[str] = field(default_factory=list)


class SafetyAgent(Agent[SynthesisOutput, SafetyOutput]):
    name = "safety"

    def run(self, input_data: SynthesisOutput) -> SafetyOutput:
        cleaned: dict[str, str] = {}
        flags: list[str] = []

        for fid, narration in input_data.narratives.items():
            if narration and _DIAG_RE.search(narration):
                flags.append(f"diagnostic_phrasing:{fid}")
                cleaned[fid] = ""
            else:
                cleaned[fid] = narration

        for f in input_data.findings:
            if f.requires_physician and not any("Syntrx is a literacy tool" in a for a in f.actions):
                f.actions.append(PHYSICIAN_DISCLAIMER)

        return SafetyOutput(
            findings=input_data.findings,
            narratives=cleaned,
            flags=flags,
        )

    def describe(self, output: SafetyOutput) -> str:
        return f"{len(output.findings)} findings cleared, flags={len(output.flags)}"

    def metadata(self, output: SafetyOutput) -> dict:
        return {"flags": output.flags}
