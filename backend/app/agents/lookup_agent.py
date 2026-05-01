"""
Stage 2 — Lookup Agent.

Given the user's genotypes, retrieve the relevant evidence chunks for
each clinically-significant SNP. We try the live ChromaDB vector store
first, falling back to the in-process catalog citations so that the
pipeline is fully functional without ingesting the full PharmGKB dump.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core import snp_catalog
from app.core.parser import Genotype
from app.knowledge.vector_store import VectorStore

from .base import Agent


@dataclass
class LookupOutput:
    chunks_per_snp: dict[str, list[dict]] = field(default_factory=dict)
    fallback: bool = True   # True if we used the catalog defaults instead of Chroma


class LookupAgent(Agent[dict[str, Genotype], LookupOutput]):
    name = "lookup"

    def __init__(self, store: VectorStore | None = None) -> None:
        self.store = store or VectorStore.get_default()

    def run(self, input_data: dict[str, Genotype]) -> LookupOutput:
        out = LookupOutput(fallback=not self.store.is_available())
        for rsid in input_data:
            defn = snp_catalog.get(rsid)
            if not defn:
                continue
            if not out.fallback:
                hits = self.store.query(rsid, defn.gene, top_k=5)
                if hits:
                    out.chunks_per_snp[rsid] = hits
                    continue
            # Fallback: surface the curated description + hard-coded sources
            out.chunks_per_snp[rsid] = [
                {"source": s, "text": defn.description, "score": 1.0}
                for s in (defn.sources or ("Syntrx curated catalog",))
            ]
        return out

    def describe(self, output: LookupOutput) -> str:
        return f"chunks for {len(output.chunks_per_snp)} SNPs ({'rag' if not output.fallback else 'catalog'})"

    def metadata(self, output: LookupOutput) -> dict:
        return {"snps_with_evidence": len(output.chunks_per_snp), "rag_used": not output.fallback}
