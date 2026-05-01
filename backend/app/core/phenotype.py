"""
Phenotype caller.

For pharmacogenes with star-allele nomenclature (CYP2D6, CYP2C19,
CYP2C9, CYP3A5, TPMT) we resolve a *diplotype* (e.g. "*1/*4") from the
user's SNP genotypes and assign a CPIC-defined phenotype using activity
scores. For everything else we just normalize the genotype.

This module is deliberately *deterministic*. CPIC publishes the
genotype→phenotype mapping; the LLM never overrides it. The synthesis
agent only translates these phenotypes into plain English.
"""

from __future__ import annotations

from dataclasses import dataclass

from .parser import Genotype
from .snp_catalog import Confidence


@dataclass(frozen=True)
class Phenotype:
    gene: str
    diplotype: str
    phenotype: str
    activity_score: float | None
    confidence: Confidence
    source: str = "CPIC"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_allele(g: Genotype | None, allele: str) -> bool:
    return bool(g) and allele in g.alleles and not g.is_no_call


def _allele_count(g: Genotype | None, allele: str) -> int:
    if not g or g.is_no_call:
        return 0
    return sum(1 for a in g.alleles if a == allele)


# ---------------------------------------------------------------------------
# CYP2D6  (codeine, tramadol, SSRIs, beta-blockers, tamoxifen)
# ---------------------------------------------------------------------------
# CPIC activity scores per allele:
#   *1, *2, *35   = 1.0   (normal)
#   *10, *17, *41 = 0.5   (decreased) - we use *10 (rs1065852)
#   *3, *4, *5, *6, *7, *8 = 0  (no function)
# Phenotype (sum of two allele activities):
#   0          → Poor Metabolizer (PM)
#   >0 ≤1.0    → Intermediate Metabolizer (IM)
#   >1.0 ≤2.25 → Normal Metabolizer (NM)
#   >2.25      → Ultrarapid Metabolizer (UM)
# (Gene duplications/CNVs that produce UM cannot be detected from a
# 23andMe SNP file — we surface that limitation in the recommendation.)

_CYP2D6_ACTIVITY = {"*1": 1.0, "*2": 1.0, "*4": 0.0, "*10": 0.5, "*6": 0.0, "*3": 0.0}


def _call_cyp2d6(genos: dict[str, Genotype]) -> Phenotype:
    # Each entry: (rsid, star-allele, risk allele on the +strand). We iterate
    # in priority order — once both allele slots are filled we stop. Order
    # matters because *3 and *6 are no-function and dominate over *10's
    # decreased-function call.
    SNPS = [
        ("rs35742686", "*3",  "-"),   # frameshift deletion
        ("rs5030655",  "*6",  "-"),   # single-base deletion
        ("rs3892097",  "*4",  "A"),   # splice defect
        ("rs1065852",  "*10", "A"),   # P34S (reduced function)
    ]
    alleles: list[str] = []
    for rsid, star, risk in SNPS:
        g = genos.get(rsid)
        if not g or g.is_no_call:
            continue
        c = _allele_count(g, risk)
        for _ in range(min(c, 2 - len(alleles))):
            alleles.append(star)
        if len(alleles) >= 2:
            break

    while len(alleles) < 2:
        alleles.append("*1")

    diplotype = "/".join(sorted(alleles))
    score = sum(_CYP2D6_ACTIVITY.get(a, 1.0) for a in alleles)
    # CPIC 2019 update — boundary moved from 1.0 to 1.25
    if score == 0:
        ph = "Poor Metabolizer"
    elif score < 1.25:
        ph = "Intermediate Metabolizer"
    elif score <= 2.25:
        ph = "Normal Metabolizer"
    else:
        ph = "Ultrarapid Metabolizer"

    return Phenotype("CYP2D6", diplotype, ph, score, Confidence.HIGH)


# ---------------------------------------------------------------------------
# CYP2C19  (clopidogrel, omeprazole, SSRIs)
# ---------------------------------------------------------------------------
# *1 = normal (1.0), *2 = no function (0), *3 = no function (0),
# *17 = increased (~1.5)

def _call_cyp2c19(genos: dict[str, Genotype]) -> Phenotype:
    rs4244285  = genos.get("rs4244285")   # *2
    rs4986893  = genos.get("rs4986893")   # *3
    rs12248560 = genos.get("rs12248560")  # *17

    alleles: list[str] = []
    for g, name in [(rs4244285, "*2"), (rs4986893, "*3")]:
        if g and not g.is_no_call:
            for _ in range(min(_allele_count(g, "A"), 2 - len(alleles))):
                alleles.append(name)
    if rs12248560 and not rs12248560.is_no_call:
        for _ in range(min(_allele_count(rs12248560, "T"), 2 - len(alleles))):
            alleles.append("*17")
    while len(alleles) < 2:
        alleles.append("*1")

    diplotype = "/".join(sorted(alleles))
    n_lof = sum(1 for a in alleles if a in {"*2", "*3"})
    n_inc = sum(1 for a in alleles if a == "*17")

    if n_lof == 2:
        ph = "Poor Metabolizer"
    elif n_lof == 1 and n_inc == 0:
        ph = "Intermediate Metabolizer"
    elif n_lof == 1 and n_inc == 1:
        ph = "Intermediate Metabolizer"   # CPIC: combined activity ≈ 1.5 → IM/likely
    elif n_inc == 2:
        ph = "Ultrarapid Metabolizer"
    elif n_inc == 1:
        ph = "Rapid Metabolizer"
    else:
        ph = "Normal Metabolizer"

    return Phenotype("CYP2C19", diplotype, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# CYP2C9  (warfarin, NSAIDs, phenytoin)
# ---------------------------------------------------------------------------
# *1 = 1.0, *2 = 0.5, *3 = 0

_CYP2C9_ACTIVITY = {"*1": 1.0, "*2": 0.5, "*3": 0.0}


def _call_cyp2c9(genos: dict[str, Genotype]) -> Phenotype:
    rs1799853 = genos.get("rs1799853")   # *2 (T)
    rs1057910 = genos.get("rs1057910")   # *3 (C)

    alleles: list[str] = []
    if rs1057910 and not rs1057910.is_no_call:
        for _ in range(min(_allele_count(rs1057910, "C"), 2 - len(alleles))):
            alleles.append("*3")
    if rs1799853 and not rs1799853.is_no_call:
        for _ in range(min(_allele_count(rs1799853, "T"), 2 - len(alleles))):
            alleles.append("*2")
    while len(alleles) < 2:
        alleles.append("*1")

    diplotype = "/".join(sorted(alleles))
    score = sum(_CYP2C9_ACTIVITY[a] for a in alleles)
    # CPIC 2017 update — activity score 1.5 is now NM (was IM previously),
    # 0.5 is PM (was IM). Net effect: 1.0 is the only IM band.
    if score >= 1.5:
        ph = "Normal Metabolizer"
    elif score >= 1.0:
        ph = "Intermediate Metabolizer"
    else:
        ph = "Poor Metabolizer"
    return Phenotype("CYP2C9", diplotype, ph, score, Confidence.HIGH)


# ---------------------------------------------------------------------------
# CYP3A5  (tacrolimus)
# ---------------------------------------------------------------------------
# rs776746: T = *1 (expressor), C = *3 (non-expressor).

def _call_cyp3a5(genos: dict[str, Genotype]) -> Phenotype | None:
    g = genos.get("rs776746")
    if not g or g.is_no_call:
        return None
    n_star3 = _allele_count(g, "C")
    if n_star3 == 0:
        ph, dip = "Normal Metabolizer / Expressor", "*1/*1"
    elif n_star3 == 1:
        ph, dip = "Intermediate Metabolizer", "*1/*3"
    else:
        ph, dip = "Poor Metabolizer / Nonexpressor", "*3/*3"
    return Phenotype("CYP3A5", dip, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# CYP1A2  (caffeine)
# ---------------------------------------------------------------------------
# *1F (rs762551): A = inducible/fast, C = slow.
# Note: actual induction requires environmental triggers (smoking, charred meat).

def _call_cyp1a2(genos: dict[str, Genotype]) -> Phenotype | None:
    g = genos.get("rs762551")
    if not g or g.is_no_call:
        return None
    n_a = _allele_count(g, "A")
    if n_a == 2:
        ph, dip = "Rapid Metabolizer (inducible)", "*1F/*1F"
    elif n_a == 1:
        ph, dip = "Intermediate Metabolizer", "*1F/*1A"
    else:
        ph, dip = "Slow Metabolizer", "*1A/*1A"
    return Phenotype("CYP1A2", dip, ph, None, Confidence.MODERATE)


# ---------------------------------------------------------------------------
# TPMT  (thiopurines)
# ---------------------------------------------------------------------------
# rs1800462 (*2: C), rs1800460 (*3B: T), rs1142345 (*3C: C).
# *3A is *3B+*3C in cis, which we approximate when both heterozygous.

def _call_tpmt(genos: dict[str, Genotype]) -> Phenotype | None:
    rs1800462 = genos.get("rs1800462")
    rs1800460 = genos.get("rs1800460")
    rs1142345 = genos.get("rs1142345")
    if not any([rs1800462, rs1800460, rs1142345]):
        return None
    alleles: list[str] = []
    if rs1800462 and not rs1800462.is_no_call:
        for _ in range(min(_allele_count(rs1800462, "C"), 2 - len(alleles))):
            alleles.append("*2")
    # Treat *3B + *3C in cis (commonest combination) as a single *3A
    n_3b = _allele_count(rs1800460, "T") if rs1800460 else 0
    n_3c = _allele_count(rs1142345, "C") if rs1142345 else 0
    n_3a = min(n_3b, n_3c)
    for _ in range(min(n_3a, 2 - len(alleles))):
        alleles.append("*3A")
    # Remaining heterozygous variants
    for _ in range(min(n_3b - n_3a, 2 - len(alleles))):
        alleles.append("*3B")
    for _ in range(min(n_3c - n_3a, 2 - len(alleles))):
        alleles.append("*3C")
    while len(alleles) < 2:
        alleles.append("*1")
    diplotype = "/".join(sorted(alleles))
    n_lof = sum(1 for a in alleles if a != "*1")
    if n_lof == 2:
        ph = "Poor Metabolizer"
    elif n_lof == 1:
        ph = "Intermediate Metabolizer"
    else:
        ph = "Normal Metabolizer"
    return Phenotype("TPMT", diplotype, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# UGT1A1  (irinotecan, atazanavir)
# ---------------------------------------------------------------------------

def _call_ugt1a1(genos: dict[str, Genotype]) -> Phenotype | None:
    g = genos.get("rs887829")
    if not g or g.is_no_call:
        return None
    n_t = _allele_count(g, "T")
    if n_t == 2:
        ph, dip = "Poor Metabolizer (Gilbert syndrome)", "*28/*28"
    elif n_t == 1:
        ph, dip = "Intermediate Metabolizer", "*1/*28"
    else:
        ph, dip = "Normal Metabolizer", "*1/*1"
    return Phenotype("UGT1A1", dip, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# SLCO1B1  (statin myopathy)
# ---------------------------------------------------------------------------

def _call_slco1b1(genos: dict[str, Genotype]) -> Phenotype | None:
    g = genos.get("rs4149056")
    if not g or g.is_no_call:
        return None
    n_c = _allele_count(g, "C")
    if n_c == 2:
        ph, dip = "Poor Function", "*5/*5"
    elif n_c == 1:
        ph, dip = "Decreased Function", "*1/*5"
    else:
        ph, dip = "Normal Function", "*1/*1"
    return Phenotype("SLCO1B1", dip, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# VKORC1  (warfarin)
# ---------------------------------------------------------------------------

def _call_vkorc1(genos: dict[str, Genotype]) -> Phenotype | None:
    g = genos.get("rs9923231")
    if not g or g.is_no_call:
        return None
    n_t = _allele_count(g, "T") + _allele_count(g, "A")  # may be reported either way
    if n_t == 2:
        ph, dip = "High warfarin sensitivity", "AA"
    elif n_t == 1:
        ph, dip = "Moderate warfarin sensitivity", "GA"
    else:
        ph, dip = "Standard warfarin sensitivity", "GG"
    return Phenotype("VKORC1", dip, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# DPYD  (5-FU / capecitabine)
# ---------------------------------------------------------------------------
# Any heterozygous loss-of-function variant → dose-reduce; homozygous → avoid.

def _call_dpyd(genos: dict[str, Genotype]) -> Phenotype | None:
    risk = {
        "rs3918290":  "T",   # *2A
        "rs55886062": "C",   # *13
        "rs67376798": "A",   # D949V
    }
    n_lof = 0
    captured = []
    for rsid, allele in risk.items():
        g = genos.get(rsid)
        if not g or g.is_no_call:
            continue
        c = _allele_count(g, allele)
        if c:
            captured.append((rsid, c))
            n_lof += c
    if not captured:
        return Phenotype("DPYD", "Reference/Reference", "Normal Metabolizer", 2.0, Confidence.HIGH)
    if n_lof >= 2:
        ph, score = "Poor Metabolizer (avoid 5-FU)", 0.0
    else:
        ph, score = "Intermediate Metabolizer (reduce dose 50%)", 1.0
    dip = "/".join(f"{r}({c})" for r, c in captured)
    return Phenotype("DPYD", dip, ph, score, Confidence.HIGH)


# ---------------------------------------------------------------------------
# APOE  (Alzheimer's risk modifier)
# ---------------------------------------------------------------------------
# Diplotype derived from rs429358 + rs7412.

def _call_apoe(genos: dict[str, Genotype]) -> Phenotype | None:
    g1 = genos.get("rs429358")
    g2 = genos.get("rs7412")
    if not g1 or not g2 or g1.is_no_call or g2.is_no_call:
        return None
    # ε mapping per chromosome (each allele).
    # APOE codon 112 (rs429358): T = Cys, C = Arg.
    # APOE codon 158 (rs7412):   T = Cys, C = Arg.
    #   Cys112 + Cys158 → ε2   (rs429358 T + rs7412 T)
    #   Cys112 + Arg158 → ε3   (rs429358 T + rs7412 C)
    #   Arg112 + Arg158 → ε4   (rs429358 C + rs7412 C)
    #   Arg112 + Cys158 → ε1   (rs429358 C + rs7412 T) — extremely rare
    counts = {"ε2": 0, "ε3": 0, "ε4": 0}
    for a1, a2 in zip(g1.alleles, g2.alleles, strict=False):
        if a1 == "T" and a2 == "T":
            counts["ε2"] += 1
        elif a1 == "T" and a2 == "C":
            counts["ε3"] += 1
        elif a1 == "C" and a2 == "C":
            counts["ε4"] += 1
        elif a1 == "C" and a2 == "T":
            # ε1 — very rare; treat as ε3-equivalent for risk reporting
            counts["ε3"] += 1
    diplotype = (
        "/".join([k for k, v in counts.items() for _ in range(v)] or ["ε3", "ε3"])
    )
    if counts["ε4"] == 2:
        ph = "ε4/ε4 — substantially elevated Alzheimer's risk"
    elif counts["ε4"] == 1:
        ph = "Single ε4 carrier — moderately elevated Alzheimer's risk"
    elif counts["ε2"] >= 1:
        ph = "ε2 carrier — typical or reduced Alzheimer's risk; mildly altered lipids"
    else:
        ph = "ε3/ε3 — population-baseline Alzheimer's risk"
    return Phenotype("APOE", diplotype, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# HFE  (hereditary hemochromatosis)
# ---------------------------------------------------------------------------

def _call_hfe(genos: dict[str, Genotype]) -> Phenotype | None:
    c282y = genos.get("rs1800562")
    h63d = genos.get("rs1799945")
    if not c282y and not h63d:
        return None
    n_c282y = _allele_count(c282y, "A") if c282y and not c282y.is_no_call else 0
    n_h63d = _allele_count(h63d, "G") if h63d and not h63d.is_no_call else 0

    if n_c282y == 2:
        ph = "C282Y/C282Y — classical iron overload risk; monitor ferritin"
        dip = "C282Y/C282Y"
    elif n_c282y == 1 and n_h63d == 1:
        ph = "C282Y/H63D compound heterozygous — moderate iron overload risk"
        dip = "C282Y/H63D"
    elif n_c282y == 1:
        ph = "C282Y carrier — usually asymptomatic"
        dip = "C282Y/wt"
    elif n_h63d == 2:
        ph = "H63D/H63D — low iron overload risk"
        dip = "H63D/H63D"
    elif n_h63d == 1:
        ph = "H63D carrier — usually asymptomatic"
        dip = "H63D/wt"
    else:
        ph = "Reference — no HFE variants detected"
        dip = "wt/wt"
    return Phenotype("HFE", dip, ph, None, Confidence.HIGH)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

CALLERS = [
    _call_cyp2d6, _call_cyp2c19, _call_cyp2c9, _call_cyp3a5, _call_cyp1a2,
    _call_tpmt, _call_ugt1a1, _call_slco1b1, _call_vkorc1, _call_dpyd,
    _call_apoe, _call_hfe,
]


def call_phenotypes(genos: dict[str, Genotype]) -> dict[str, Phenotype]:
    out: dict[str, Phenotype] = {}
    for fn in CALLERS:
        try:
            ph = fn(genos)
        except Exception:
            ph = None
        if ph is not None:
            out[ph.gene] = ph
    return out
