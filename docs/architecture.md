# Syntrx architecture notes

These are the design decisions that actually mattered. Each section
links to the file where the decision lives, so you can read the code
alongside it.

## 1. Deterministic-first pharmacogenomics

The core engine ([`app/core/phenotype.py`](../backend/app/core/phenotype.py),
[`app/core/recommendations.py`](../backend/app/core/recommendations.py))
is closed-form Python. Given a genotype map, it returns a fixed set of
findings — no LLM, no randomness. The LLM is only allowed to add a
narrator paragraph next to each finding, and the Safety Agent regex-strips
anything that drifts into diagnostic language.

This is the difference between a system that *can* match CPIC guidelines
and one that *will*. The CPIC concordance script in
[`scripts/evaluate.py`](../backend/scripts/evaluate.py) currently reports
13/13 = 100% on the synthetic profiles.

## 2. Curated catalog as the source of truth

[`app/core/snp_catalog.py`](../backend/app/core/snp_catalog.py) is the
one place that lists *which SNPs we care about and what they mean*. The
parser only retains catalog SNPs; the recommendation engine only acts
on catalog SNPs. Adding a new SNP is a one-file change.

Each `SNPDefinition` carries `gene`, `domain`, `risk_allele`,
`confidence`, `sources`, and a `composite` flag that signals "this SNP
is one piece of a star-allele diplotype, don't act on it in isolation".

## 3. Star-allele callers, not naive genotype lookups

Pharmacogenes (CYP2D6, CYP2C19, CYP2C9, TPMT, UGT1A1, …) follow CPIC's
star-allele system: each SNP defines a star allele, two stars combine
into a diplotype, and the diplotype maps to a phenotype via an *activity
score*. The callers in `phenotype.py` implement that calculation
explicitly. They don't try to be clever about CNVs or rare alleles —
those would require a real bioinformatics call set, not a 23andMe file.

## 4. Provider-agnostic LLM with deterministic fallback

[`app/services/llm.py`](../backend/app/services/llm.py) wraps Anthropic,
OpenAI, and a deterministic mock behind one `Protocol`. Tests use the
mock; production switches with one env var. The mock is *not* a stub
that returns "OK" — it composes a deterministic paraphrase of the input
prompt, so synthesis-agent tests can assert that "codeine" appears in
the narrator output for a CYP2D6 PM finding.

## 5. Vector store that degrades gracefully

[`app/knowledge/vector_store.py`](../backend/app/knowledge/vector_store.py)
returns `is_available() = False` when ChromaDB isn't installed or the
persist dir is empty. The Lookup Agent handles that by falling back to
the catalog's hard-coded `sources` field, so the pipeline produces
useful evidence chunks even before you've ingested PharmGKB.

## 6. Every recommendation cites its evidence

The `Finding` dataclass carries an `evidence: list[str]` field, and the
JSON serialization of every report includes those citations verbatim.
The frontend renders them inline so users can see exactly which CPIC
guideline or PubMed ID a recommendation came from.

## 7. Safety Agent applies hard rules, not heuristics

[`app/agents/safety_agent.py`](../backend/app/agents/safety_agent.py)
runs *after* the recommendation engine and the LLM. It:

1. Strips LLM narration that matches a small regex of diagnostic
   phrasing ("you have", "I diagnose", "take \d mg", etc).
2. Appends the standard "discuss with prescriber" disclaimer to any
   finding whose `requires_physician=True`.
3. Attaches the global Syntrx disclaimer to the report header.

It cannot invent or modify findings — its inputs and outputs are typed
so this is enforced at the boundary.

## 8. The frontend trusts the backend's structure

The React app's `Finding` type is identical to the backend's
`Finding.to_dict()` shape. The `DomainSection` component just renders
whatever the backend grouped under each `Domain`. There is no
client-side phenotype logic — the backend is the only place that
*decides* anything.
