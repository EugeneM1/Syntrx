"""Stage 1 — Parse raw genetic file into a structured genotype map."""

from __future__ import annotations

from dataclasses import dataclass

from app.core import parser

from .base import Agent


@dataclass
class ParserInput:
    payload: bytes
    filename: str = "upload.txt"


class ParserAgent(Agent[ParserInput, parser.ParseResult]):
    name = "parser"

    def run(self, input_data: ParserInput) -> parser.ParseResult:
        return parser.parse_bytes(input_data.payload)

    def describe(self, output: parser.ParseResult) -> str:
        return (f"format={output.file_format.value} variants={output.total_variants} "
                f"matched={output.matched_variants}/{len(output.genotypes) or '?'}")

    def metadata(self, output: parser.ParseResult) -> dict:
        return {
            "file_format": output.file_format.value,
            "total_variants": output.total_variants,
            "matched_variants": output.matched_variants,
            "no_calls": output.no_calls,
            "coverage_pct": round(output.coverage_pct, 1),
        }
