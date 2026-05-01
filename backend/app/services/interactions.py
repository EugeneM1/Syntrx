"""
Drug-interaction checker.

Cross-references a user's medication list against their pharmacogenomic
phenotypes and returns flagged interactions. Knowledge of which drugs
each gene metabolizes lives here so that the catalog stays focused on
SNPs and the recommendations layer stays focused on phenotypes.

Drug names are normalized via a small alias table — clopidogrel /
Plavix / clopidogrel bisulfate all map to the same canonical entry.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.phenotype import Phenotype


@dataclass(frozen=True)
class DrugProfile:
    name: str
    canonical: str
    metabolized_by: tuple[str, ...]
    activated_by: tuple[str, ...] = ()
    note: str = ""


_DRUGS: dict[str, DrugProfile] = {}
def _add(name: str, canonical: str, metabolized_by: tuple[str, ...],
         activated_by: tuple[str, ...] = (), note: str = "") -> None:
    p = DrugProfile(canonical, canonical, metabolized_by, activated_by, note)
    _DRUGS[name.lower()] = p
    _DRUGS[canonical.lower()] = p


# Common opioids / analgesics
_add("codeine",     "codeine",      ("CYP2D6",), activated_by=("CYP2D6",),
     note="Codeine is a prodrug — needs CYP2D6 to become morphine.")
_add("tramadol",    "tramadol",     ("CYP2D6", "CYP3A4"), activated_by=("CYP2D6",))
_add("hydrocodone", "hydrocodone",  ("CYP2D6",), activated_by=("CYP2D6",))
_add("oxycodone",   "oxycodone",    ("CYP2D6", "CYP3A4"))
_add("methadone",   "methadone",    ("CYP2B6", "CYP3A4"))

# Antiplatelets
_add("clopidogrel", "clopidogrel",  ("CYP2C19",), activated_by=("CYP2C19",),
     note="Clopidogrel is a prodrug — CYP2C19 PMs/IMs may not benefit.")
_add("plavix",      "clopidogrel",  ("CYP2C19",), activated_by=("CYP2C19",))
_add("prasugrel",   "prasugrel",    ("CYP3A4", "CYP2B6"))
_add("ticagrelor",  "ticagrelor",   ("CYP3A4",))

# PPIs
_add("omeprazole",  "omeprazole",   ("CYP2C19",))
_add("prilosec",    "omeprazole",   ("CYP2C19",))
_add("esomeprazole","esomeprazole", ("CYP2C19",))
_add("pantoprazole","pantoprazole", ("CYP2C19",))
_add("lansoprazole","lansoprazole", ("CYP2C19",))

# SSRIs / SNRIs
_add("sertraline",  "sertraline",   ("CYP2C19", "CYP2D6"))
_add("zoloft",      "sertraline",   ("CYP2C19", "CYP2D6"))
_add("escitalopram","escitalopram", ("CYP2C19",))
_add("citalopram",  "citalopram",   ("CYP2C19",))
_add("lexapro",     "escitalopram", ("CYP2C19",))
_add("fluoxetine",  "fluoxetine",   ("CYP2D6",))
_add("paroxetine",  "paroxetine",   ("CYP2D6",))
_add("venlafaxine", "venlafaxine",  ("CYP2D6", "CYP3A4"))

# Statins — SLCO1B1 (the OATP1B1 transporter) drives muscle-toxicity risk
_add("simvastatin",   "simvastatin",  ("CYP3A4", "SLCO1B1"),
     note="Statin uptake into the liver is SLCO1B1-mediated; reduced transporter function leaves more drug in muscle.")
_add("atorvastatin",  "atorvastatin", ("CYP3A4", "SLCO1B1"))
_add("rosuvastatin",  "rosuvastatin", ("SLCO1B1",))
_add("pravastatin",   "pravastatin",  ("SLCO1B1",))

# Anticoagulants
_add("warfarin",    "warfarin",     ("CYP2C9", "VKORC1"))
_add("coumadin",    "warfarin",     ("CYP2C9", "VKORC1"))

# Beta-blockers
_add("metoprolol",  "metoprolol",   ("CYP2D6",))
_add("propranolol", "propranolol",  ("CYP2D6",))

# Oncology
_add("tamoxifen",   "tamoxifen",    ("CYP2D6",), activated_by=("CYP2D6",))
_add("fluorouracil","fluorouracil", ("DPYD",))
_add("5-fu",        "fluorouracil", ("DPYD",))
_add("capecitabine","capecitabine", ("DPYD",))
_add("irinotecan",  "irinotecan",   ("UGT1A1",))
_add("azathioprine","azathioprine", ("TPMT",))
_add("mercaptopurine","mercaptopurine", ("TPMT",))

# Immunosuppressants
_add("tacrolimus",  "tacrolimus",   ("CYP3A5", "CYP3A4"))

# Stimulants / common
_add("caffeine",    "caffeine",     ("CYP1A2",))


@dataclass
class Interaction:
    drug: str
    gene: str
    phenotype: str
    severity: str             # info | caution | warning | avoid
    summary: str
    note: str = ""


# Severity matrix — gene + phenotype + drug-role → severity
def _severity(gene: str, phenotype: str, *, is_prodrug: bool) -> tuple[str, str]:
    """Return (severity, headline)."""
    p = phenotype.lower()
    if "ultrarapid" in p:
        if is_prodrug:
            return "warning", "Prodrug activated too quickly — risk of toxicity."
        return "caution", "Drug cleared faster than average — may be sub-therapeutic."
    if "rapid" in p:
        return "caution", "Faster-than-average clearance; may need higher dose."
    if "poor" in p:
        if is_prodrug:
            return "avoid", "Prodrug will not activate — likely ineffective."
        return "warning", "Drug clears very slowly — high risk of accumulation/toxicity."
    if any(k in p for k in ("intermediate", "decreased", "sensitivity",
                            "deficient", "slow")):
        return "caution", "Reduced clearance/activation — consider dose adjustment."
    return "info", "Standard metabolism expected."


def check(drugs: list[str], phenotypes: dict[str, Phenotype]) -> list[Interaction]:
    out: list[Interaction] = []
    for raw in drugs:
        key = (raw or "").strip().lower()
        profile = _DRUGS.get(key)
        if not profile:
            out.append(Interaction(
                drug=raw, gene="—", phenotype="unknown", severity="info",
                summary="Drug not in Syntrx pharmacogenomic catalog — no specific gene-drug flag.",
            ))
            continue

        flagged: list[Interaction] = []
        considered_genes: list[str] = []
        for gene in profile.metabolized_by:
            ph = phenotypes.get(gene)
            if not ph:
                continue
            considered_genes.append(gene)
            sev, headline = _severity(gene, ph.phenotype,
                                      is_prodrug=gene in profile.activated_by)
            if sev != "info":
                flagged.append(Interaction(
                    drug=profile.canonical, gene=gene, phenotype=ph.phenotype,
                    severity=sev, summary=headline, note=profile.note,
                ))

        if flagged:
            out.extend(flagged)
        else:
            # Single reassuring line — don't duplicate per gene
            out.append(Interaction(
                drug=profile.canonical,
                gene=", ".join(considered_genes) or ", ".join(profile.metabolized_by),
                phenotype="not flagged", severity="info",
                summary="No actionable pharmacogenomic flags for your genotype.",
                note=profile.note,
            ))
    return out


def known_drugs() -> list[str]:
    return sorted({p.canonical for p in _DRUGS.values()})
