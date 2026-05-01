"""
Curated catalog of clinically actionable SNPs.

Every entry traces back to a CPIC guideline, FDA pharmacogenomic label,
or peer-reviewed publication and is annotated with the *risk allele*
(when defined), gene, category, and a short rationale. Phenotype
assignment for star-allele genes lives in `phenotype.py`; this module is
the single source of truth for *which variants we look at* and *what
they mean in isolation*.

Allele orientation: 23andMe and AncestryDNA report all genotypes on the
positive (forward / "plus") strand. References below follow the same
convention; if a SNP needs strand-flipping, that is documented inline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Domain(str, Enum):
    DRUG = "drug_metabolism"
    NUTRIENT = "nutrient"
    DIET = "diet_fitness"
    RISK = "risk_awareness"


class Confidence(str, Enum):
    HIGH = "high"          # CPIC level A or FDA label
    MODERATE = "moderate"  # multiple peer-reviewed studies
    EMERGING = "emerging"  # single study or preliminary data


@dataclass(frozen=True)
class SNPDefinition:
    """A single clinically-actionable variant we extract from the user's file."""

    rsid: str
    gene: str
    domain: Domain
    chromosome: str
    star_allele: str | None = None          # e.g. "*4" for CYP2D6 rs3892097
    risk_allele: str | None = None          # the allele associated with the phenotype
    description: str = ""
    confidence: Confidence = Confidence.MODERATE
    sources: tuple[str, ...] = field(default_factory=tuple)
    # If True, the gene's interpretation depends on multiple SNPs and must
    # be resolved by the diplotype caller in `phenotype.py`.
    composite: bool = False


# ---------------------------------------------------------------------------
# 1. Pharmacogenomics (drug metabolism)
# ---------------------------------------------------------------------------

PGX_SNPS: list[SNPDefinition] = [
    # ---- CYP2D6 (codeine, tramadol, SSRIs, beta-blockers, tamoxifen) ----
    SNPDefinition("rs3892097",  "CYP2D6", Domain.DRUG, "22", "*4",  "A",
        "Splice defect causing CYP2D6 *4 (no enzyme activity).",
        Confidence.HIGH, ("CPIC: codeine/tramadol guideline", "PharmGKB: rs3892097"), composite=True),
    SNPDefinition("rs1065852",  "CYP2D6", Domain.DRUG, "22", "*10", "A",
        "Reduced-function CYP2D6 *10 (P34S).", Confidence.HIGH,
        ("CPIC", "PharmGKB: rs1065852"), composite=True),
    SNPDefinition("rs5030655",  "CYP2D6", Domain.DRUG, "22", "*6",  "-",
        "CYP2D6 *6 single-base deletion → no function.", Confidence.HIGH,
        ("CPIC", "PharmGKB: rs5030655"), composite=True),
    SNPDefinition("rs35742686", "CYP2D6", Domain.DRUG, "22", "*3",  "-",
        "CYP2D6 *3 frameshift → no function.", Confidence.HIGH,
        ("CPIC", "PharmGKB: rs35742686"), composite=True),
    SNPDefinition("rs1135840",  "CYP2D6", Domain.DRUG, "22", None,  "C",
        "S486T tag SNP used in star-allele calling.", Confidence.MODERATE,
        ("PharmGKB: rs1135840",), composite=True),

    # ---- CYP2C19 (clopidogrel, PPIs, SSRIs) ----
    SNPDefinition("rs4244285",  "CYP2C19", Domain.DRUG, "10", "*2",  "A",
        "Splice defect → CYP2C19 *2 (no function).", Confidence.HIGH,
        ("CPIC: clopidogrel guideline", "PharmGKB: rs4244285"), composite=True),
    SNPDefinition("rs4986893",  "CYP2C19", Domain.DRUG, "10", "*3",  "A",
        "Premature stop → CYP2C19 *3 (no function).", Confidence.HIGH,
        ("CPIC", "PharmGKB: rs4986893"), composite=True),
    SNPDefinition("rs12248560", "CYP2C19", Domain.DRUG, "10", "*17", "T",
        "Promoter variant → CYP2C19 *17 (increased function).",
        Confidence.HIGH, ("CPIC", "PharmGKB: rs12248560"), composite=True),

    # ---- CYP2C9 (warfarin, NSAIDs, phenytoin) ----
    SNPDefinition("rs1799853",  "CYP2C9", Domain.DRUG, "10", "*2",  "T",
        "R144C → CYP2C9 *2 (decreased function).", Confidence.HIGH,
        ("CPIC: warfarin guideline", "PharmGKB: rs1799853"), composite=True),
    SNPDefinition("rs1057910",  "CYP2C9", Domain.DRUG, "10", "*3",  "C",
        "I359L → CYP2C9 *3 (decreased function).", Confidence.HIGH,
        ("CPIC: warfarin guideline", "PharmGKB: rs1057910"), composite=True),

    # ---- VKORC1 (warfarin) ----
    SNPDefinition("rs9923231",  "VKORC1", Domain.DRUG, "16", None, "T",
        "−1639 G>A promoter variant: T allele → warfarin sensitivity.",
        Confidence.HIGH, ("CPIC: warfarin guideline", "PharmGKB: rs9923231")),

    # ---- CYP3A5 (tacrolimus) ----
    SNPDefinition("rs776746",   "CYP3A5", Domain.DRUG, "7",  "*3",  "C",
        "CYP3A5 *3 splice defect; C allele = no expression.",
        Confidence.HIGH, ("CPIC: tacrolimus guideline", "PharmGKB: rs776746"), composite=True),

    # ---- CYP1A2 (caffeine) ----
    SNPDefinition("rs762551",   "CYP1A2", Domain.DRUG, "15", "*1F", "A",
        "*1F: A allele = inducible/fast metabolism, C allele = slow.",
        Confidence.MODERATE, ("PharmGKB: rs762551",)),

    # ---- DPYD (5-FU / capecitabine) ----
    SNPDefinition("rs3918290",  "DPYD",  Domain.DRUG, "1",  "*2A", "T",
        "DPYD *2A splice variant — fluoropyrimidine toxicity risk.",
        Confidence.HIGH, ("CPIC: fluoropyrimidine guideline", "PharmGKB: rs3918290")),
    SNPDefinition("rs55886062", "DPYD",  Domain.DRUG, "1",  "*13", "C",
        "DPYD *13 (I560S) — fluoropyrimidine toxicity risk.",
        Confidence.HIGH, ("CPIC", "PharmGKB: rs55886062")),
    SNPDefinition("rs67376798", "DPYD",  Domain.DRUG, "1",  None,  "A",
        "D949V — fluoropyrimidine toxicity risk.",
        Confidence.HIGH, ("CPIC", "PharmGKB: rs67376798")),

    # ---- TPMT (thiopurines: azathioprine, mercaptopurine) ----
    SNPDefinition("rs1800462",  "TPMT",  Domain.DRUG, "6",  "*2",   "C",
        "TPMT *2 → no enzyme activity.", Confidence.HIGH,
        ("CPIC: thiopurine guideline", "PharmGKB: rs1800462"), composite=True),
    SNPDefinition("rs1800460",  "TPMT",  Domain.DRUG, "6",  "*3B",  "T",
        "TPMT *3B (A154T) — reduced activity.", Confidence.HIGH,
        ("CPIC", "PharmGKB: rs1800460"), composite=True),
    SNPDefinition("rs1142345",  "TPMT",  Domain.DRUG, "6",  "*3C",  "C",
        "TPMT *3C (Y240C) — reduced activity.", Confidence.HIGH,
        ("CPIC", "PharmGKB: rs1142345"), composite=True),

    # ---- UGT1A1 (irinotecan, atazanavir) ----
    SNPDefinition("rs887829",   "UGT1A1", Domain.DRUG, "2", "*28-tag", "T",
        "Tag SNP for UGT1A1 *28 (Gilbert's syndrome / irinotecan toxicity).",
        Confidence.HIGH, ("CPIC: atazanavir guideline", "PharmGKB: rs887829")),

    # ---- SLCO1B1 (statin myopathy) ----
    SNPDefinition("rs4149056",  "SLCO1B1", Domain.DRUG, "12", "*5", "C",
        "V174A — decreased statin uptake → muscle toxicity risk.",
        Confidence.HIGH, ("CPIC: simvastatin guideline", "PharmGKB: rs4149056")),

    # ---- IFNL3 (HCV interferon response) ----
    SNPDefinition("rs12979860", "IFNL3", Domain.DRUG, "19", None, "T",
        "C allele predicts higher response to peginterferon for HCV.",
        Confidence.HIGH, ("CPIC: peginterferon guideline", "PharmGKB: rs12979860")),

    # ---- G6PD (drug-induced hemolysis) ----
    SNPDefinition("rs1050829",  "G6PD", Domain.DRUG, "X", None, "C",
        "G6PD A− variant → hemolysis risk with rasburicase, dapsone, primaquine.",
        Confidence.HIGH, ("FDA label: rasburicase", "PharmGKB: rs1050829")),
]


# ---------------------------------------------------------------------------
# 2. Nutrigenomics (vitamins, micronutrients)
# ---------------------------------------------------------------------------

NUTRIENT_SNPS: list[SNPDefinition] = [
    SNPDefinition("rs1801133",  "MTHFR", Domain.NUTRIENT, "1",  None, "T",
        "C677T — T allele reduces MTHFR activity ~30–60% per allele.",
        Confidence.HIGH, ("PMID: 18950845", "ClinVar: MTHFR")),
    SNPDefinition("rs1801131",  "MTHFR", Domain.NUTRIENT, "1",  None, "C",
        "A1298C — C allele mildly reduces MTHFR activity.",
        Confidence.MODERATE, ("PMID: 11528502",)),
    SNPDefinition("rs2228570",  "VDR",   Domain.NUTRIENT, "12", None, "T",
        "FokI — T ('f') allele yields a less transcriptionally active VDR; "
        "carriers may need higher serum 25(OH)D to reach the same cellular effect.",
        Confidence.MODERATE, ("PMID: 17138664",)),
    SNPDefinition("rs1544410",  "VDR",   Domain.NUTRIENT, "12", None, "A",
        "BsmI — A allele weakly associated with lower 25(OH)D status.",
        Confidence.EMERGING, ("PMID: 21317104",)),
    SNPDefinition("rs601338",   "FUT2",  Domain.NUTRIENT, "19", None, "A",
        "Non-secretor (AA) = reduced gut B12 absorption.",
        Confidence.HIGH, ("PMID: 18776911",)),
    SNPDefinition("rs7501331",  "BCO1",  Domain.NUTRIENT, "16", None, "T",
        "T allele reduces β-carotene → retinol conversion ~50%.",
        Confidence.MODERATE, ("PMID: 19103647",)),
    SNPDefinition("rs12934922", "BCO1",  Domain.NUTRIENT, "16", None, "T",
        "T allele further reduces β-carotene cleavage activity.",
        Confidence.MODERATE, ("PMID: 19103647",)),
    SNPDefinition("rs33972313", "SLC23A1", Domain.NUTRIENT, "5", None, "T",
        "Reduced SVCT1 vitamin-C transporter efficiency.",
        Confidence.EMERGING, ("PMID: 20008638",)),
    SNPDefinition("rs1801198",  "TCN2",  Domain.NUTRIENT, "22", None, "G",
        "P259R — G allele weakly reduces holotranscobalamin (active B12).",
        Confidence.EMERGING, ("PMID: 16091735",)),
    SNPDefinition("rs2282679",  "GC",    Domain.NUTRIENT, "4",  None, "C",
        "Vitamin D binding protein — C allele lowers 25(OH)D.",
        Confidence.HIGH, ("PMID: 20541252",)),
]


# ---------------------------------------------------------------------------
# 3. Diet, fitness, lifestyle
# ---------------------------------------------------------------------------

DIET_SNPS: list[SNPDefinition] = [
    SNPDefinition("rs5082",     "APOA2", Domain.DIET, "1",  None, "C",
        "−265 T>C — CC genotype: saturated fat ↑ BMI more than non-CC.",
        Confidence.MODERATE, ("PMID: 19158204",)),
    SNPDefinition("rs4988235",  "MCM6",  Domain.DIET, "2",  None, "T",
        "Lactase persistence: T allele = retains lactase into adulthood.",
        Confidence.HIGH, ("PMID: 14745526",)),
    SNPDefinition("rs1815739",  "ACTN3", Domain.DIET, "11", None, "T",
        "R577X — T (X) allele truncates α-actinin-3 in fast-twitch fibers.",
        Confidence.HIGH, ("PMID: 12879365",)),
    SNPDefinition("rs1229984",  "ADH1B", Domain.DIET, "4",  None, "A",
        "His48Arg — A allele encodes ~40× faster ethanol → acetaldehyde.",
        Confidence.HIGH, ("PMID: 19414485",)),
    SNPDefinition("rs671",      "ALDH2", Domain.DIET, "12", None, "A",
        "ALDH2*2 — A allele = inactive aldehyde dehydrogenase (Asian flush).",
        Confidence.HIGH, ("PMID: 19414485", "WHO IARC monograph")),
    SNPDefinition("rs9939609",  "FTO",   Domain.DIET, "16", None, "A",
        "A allele associated with +1.5 kg/m² BMI per copy.",
        Confidence.HIGH, ("PMID: 17434869",)),
    SNPDefinition("rs7903146",  "TCF7L2", Domain.DIET, "10", None, "T",
        "Strongest common type-2 diabetes risk variant.",
        Confidence.HIGH, ("PMID: 16415884",)),
    SNPDefinition("rs1801282",  "PPARG", Domain.DIET, "3",  None, "C",
        "Pro12Ala — C (Pro) allele increases T2D risk; lifestyle modifiable.",
        Confidence.HIGH, ("PMID: 11118012",)),
    SNPDefinition("rs713598",   "TAS2R38", Domain.DIET, "7", None, "C",
        "PAV/AVI haplotype tag — C = 'taster' bitter perception.",
        Confidence.MODERATE, ("PMID: 12595690",)),
    SNPDefinition("rs8065080",  "TRPV1", Domain.DIET, "17", None, "T",
        "I585V — affects spicy/capsaicin sensitivity.",
        Confidence.EMERGING, ("PMID: 18550826",)),
]


# ---------------------------------------------------------------------------
# 4. Lifestyle-modifiable risk awareness
# ---------------------------------------------------------------------------

RISK_SNPS: list[SNPDefinition] = [
    SNPDefinition("rs429358",   "APOE",  Domain.RISK, "19", None, "C",
        "APOE codon 112 — C allele defines ε4 (Alzheimer's risk).",
        Confidence.HIGH, ("PMID: 8346443",), composite=True),
    SNPDefinition("rs7412",     "APOE",  Domain.RISK, "19", None, "T",
        "APOE codon 158 — T allele defines ε2 (lipid-lowering).",
        Confidence.HIGH, ("PMID: 8346443",), composite=True),
    SNPDefinition("rs1800562",  "HFE",   Domain.RISK, "6",  None, "A",
        "C282Y — homozygous = hereditary hemochromatosis risk.",
        Confidence.HIGH, ("PMID: 8696333",), composite=True),
    SNPDefinition("rs1799945",  "HFE",   Domain.RISK, "6",  None, "G",
        "H63D — compound het with C282Y modifies iron-overload risk.",
        Confidence.HIGH, ("PMID: 8696333",), composite=True),
    SNPDefinition("rs6025",     "F5",    Domain.RISK, "1",  None, "T",
        "Factor V Leiden — T allele increases VTE risk ~5–10×.",
        Confidence.HIGH, ("PMID: 8164741",)),
    SNPDefinition("rs1799963",  "F2",    Domain.RISK, "11", None, "A",
        "Prothrombin G20210A — increased VTE risk.",
        Confidence.HIGH, ("PMID: 8916933",)),
]


# ---------------------------------------------------------------------------
# Aggregate + lookups
# ---------------------------------------------------------------------------

ALL_SNPS: list[SNPDefinition] = PGX_SNPS + NUTRIENT_SNPS + DIET_SNPS + RISK_SNPS

BY_RSID: dict[str, SNPDefinition] = {s.rsid: s for s in ALL_SNPS}
BY_GENE: dict[str, list[SNPDefinition]] = {}
for _s in ALL_SNPS:
    BY_GENE.setdefault(_s.gene, []).append(_s)

TARGET_RSIDS: frozenset[str] = frozenset(BY_RSID.keys())


def get(rsid: str) -> SNPDefinition | None:
    return BY_RSID.get(rsid)


def for_gene(gene: str) -> list[SNPDefinition]:
    return BY_GENE.get(gene, [])


def summary() -> dict[str, int]:
    """Quick counts by domain — used in /api/health and the README banner."""
    out: dict[str, int] = {}
    for s in ALL_SNPS:
        out[s.domain.value] = out.get(s.domain.value, 0) + 1
    out["total"] = len(ALL_SNPS)
    return out
