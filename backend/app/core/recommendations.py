"""
Deterministic recommendation engine.

Turns parsed genotypes + called phenotypes into a list of `Finding`
objects that a user can act on. This is the *ground-truth* layer: the
LLM Synthesis Agent only paraphrases or expands findings, it cannot
invent or contradict them. That separation is what lets us validate
Syntrx against CPIC guidelines.

Each rule below is annotated with its evidence source. Anything that
suggests a prescription change is tagged `requires_physician=True` so
the Safety Agent will surface a disclaimer.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .parser import Genotype
from .phenotype import Phenotype
from .snp_catalog import Confidence, Domain


@dataclass
class Finding:
    id: str
    domain: Domain
    gene: str
    title: str
    summary: str                       # one-line headline for cards
    detail: str                        # 2–4 sentence plain-English explanation
    actions: list[str]                 # bullet-style recommendations
    confidence: Confidence
    evidence: list[str]
    related_drugs: list[str] = field(default_factory=list)
    related_nutrients: list[str] = field(default_factory=list)
    diplotype: str | None = None
    activity_score: float | None = None
    requires_physician: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "domain": self.domain.value,
            "gene": self.gene,
            "title": self.title,
            "summary": self.summary,
            "detail": self.detail,
            "actions": self.actions,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "related_drugs": self.related_drugs,
            "related_nutrients": self.related_nutrients,
            "diplotype": self.diplotype,
            "activity_score": self.activity_score,
            "requires_physician": self.requires_physician,
        }


# ---------------------------------------------------------------------------
# Pharmacogenomic rules — phenotype-driven
# ---------------------------------------------------------------------------

def _cyp2d6_findings(p: Phenotype) -> list[Finding]:
    base = {"gene": "CYP2D6", "diplotype": p.diplotype, "activity_score": p.activity_score,
            "confidence": p.confidence, "domain": Domain.DRUG}
    drugs = ["codeine", "tramadol", "hydrocodone", "oxycodone",
             "fluoxetine", "paroxetine", "venlafaxine", "metoprolol",
             "tamoxifen", "atomoxetine"]
    sources = ["CPIC: codeine/tramadol", "CPIC: SSRIs", "PharmGKB: CYP2D6"]

    if p.phenotype == "Poor Metabolizer":
        return [Finding(
            id="cyp2d6_pm", title="CYP2D6 Poor Metabolizer",
            summary="You activate codeine and similar opioids very slowly — they may give little pain relief.",
            detail=("Codeine, tramadol, and hydrocodone need CYP2D6 to convert into their active forms. "
                    "Your two non-functional copies mean these drugs will provide minimal analgesia. "
                    "On the other hand, drugs that CYP2D6 *clears* (e.g. metoprolol, paroxetine, atomoxetine) "
                    "will accumulate at standard doses and may cause side effects."),
            actions=[
                "If a doctor prescribes codeine or tramadol for pain, ask for an alternative such as acetaminophen, ibuprofen, or morphine.",
                "Use the lowest effective dose of metoprolol; watch for fatigue, bradycardia, dizziness.",
                "Mention this status before any oncology consult — tamoxifen activation is also reduced.",
            ],
            evidence=sources, related_drugs=drugs, requires_physician=True, **base)]
    if p.phenotype == "Intermediate Metabolizer":
        return [Finding(
            id="cyp2d6_im", title="CYP2D6 Intermediate Metabolizer",
            summary="You metabolize codeine-class opioids and several antidepressants more slowly than average.",
            detail=("Activation of codeine and tramadol is reduced, so analgesia may be partial. "
                    "Standard doses of paroxetine, fluoxetine, or metoprolol tend to run higher in your blood than average."),
            actions=[
                "Discuss starting at the lower end of the dose range for CYP2D6 substrates.",
                "Track side effects within the first 1–2 weeks of any new CYP2D6 substrate.",
            ],
            evidence=sources, related_drugs=drugs, requires_physician=True, **base)]
    if p.phenotype == "Ultrarapid Metabolizer":
        return [Finding(
            id="cyp2d6_um", title="CYP2D6 Ultrarapid Metabolizer",
            summary="Codeine converts to morphine very quickly — risk of opioid toxicity at standard doses.",
            detail=("Ultrarapid metabolism converts codeine to morphine faster than average, which has been "
                    "linked to fatal respiratory depression — especially in children and breastfeeding mothers. "
                    "Conversely, drugs cleared by CYP2D6 may be sub-therapeutic at standard doses."),
            actions=[
                "Avoid codeine and tramadol entirely; use a non-CYP2D6 analgesic.",
                "If prescribed an SSRI like paroxetine, blood levels may be too low for therapeutic effect.",
                "Bring this finding to any prescribing visit; the FDA codeine label flags UMs.",
            ],
            evidence=sources, related_drugs=drugs, requires_physician=True, **base)]
    return [Finding(
        id="cyp2d6_nm", title="CYP2D6 Normal Metabolizer",
        summary="You metabolize CYP2D6 drugs at the population-average rate.",
        detail="Standard dosing of codeine, tramadol, SSRIs, and beta-blockers is appropriate for your genotype.",
        actions=["No CYP2D6-specific changes needed; follow standard prescribing guidance."],
        evidence=sources, related_drugs=drugs, **base)]


def _cyp2c19_findings(p: Phenotype) -> list[Finding]:
    base = {"gene": "CYP2C19", "diplotype": p.diplotype, "confidence": p.confidence, "domain": Domain.DRUG}
    drugs = ["clopidogrel", "omeprazole", "esomeprazole", "lansoprazole",
             "sertraline", "citalopram", "escitalopram", "voriconazole"]
    src = ["CPIC: clopidogrel", "CPIC: SSRIs", "CPIC: PPIs", "PharmGKB: CYP2C19"]

    if p.phenotype == "Poor Metabolizer":
        return [Finding(
            id="cyp2c19_pm", title="CYP2C19 Poor Metabolizer",
            summary="Clopidogrel will not activate well — alternative antiplatelet therapy is preferred after stent or stroke.",
            detail=("Clopidogrel is a prodrug requiring CYP2C19 for activation. As a poor metabolizer "
                    "you will form much less active drug, which raises cardiovascular event risk if you "
                    "are placed on clopidogrel after PCI/stenting or stroke. PPIs will also clear slowly, "
                    "so they may have stronger acid suppression than expected."),
            actions=[
                "If antiplatelet therapy is needed, ask about prasugrel or ticagrelor instead of clopidogrel.",
                "Lower-than-standard PPI doses may be effective for reflux.",
                "Bring this to any psychiatric consult — sertraline / citalopram may run higher than average.",
            ],
            evidence=src, related_drugs=drugs, requires_physician=True, **base)]
    if p.phenotype == "Intermediate Metabolizer":
        return [Finding(
            id="cyp2c19_im", title="CYP2C19 Intermediate Metabolizer",
            summary="Reduced clopidogrel activation; consider alternatives if a stent is placed.",
            detail="One non-functional CYP2C19 copy lowers conversion of clopidogrel to its active form by ~30–50%. "
                    "PPIs and several SSRIs also accumulate somewhat more than average.",
            actions=[
                "Discuss prasugrel or ticagrelor as alternatives to clopidogrel after PCI.",
                "Standard PPI starting doses are usually fine; watch for over-suppression on long-term use.",
            ],
            evidence=src, related_drugs=drugs, requires_physician=True, **base)]
    if p.phenotype in {"Rapid Metabolizer", "Ultrarapid Metabolizer"}:
        return [Finding(
            id="cyp2c19_rmum", title=f"CYP2C19 {p.phenotype}",
            summary="PPIs and certain SSRIs may clear too quickly for full effect at standard doses.",
            detail=("CYP2C19 *17 boosts enzyme activity. Omeprazole, esomeprazole, and lansoprazole may not "
                    "control acid as effectively at standard doses; SSRIs like escitalopram may be sub-therapeutic. "
                    "Conversely, clopidogrel activates very efficiently."),
            actions=[
                "Consider higher-end of the dose range for PPIs (with physician guidance).",
                "If an SSRI underperforms at a standard dose, this genotype is one possible explanation.",
                "Clopidogrel works as expected — no change needed.",
            ],
            evidence=src, related_drugs=drugs, requires_physician=True, **base)]
    return [Finding(
        id="cyp2c19_nm", title="CYP2C19 Normal Metabolizer",
        summary="Standard dosing of clopidogrel, PPIs, and CYP2C19-cleared SSRIs.",
        detail="Population-average activity. No CYP2C19-specific dose adjustments needed.",
        actions=["No CYP2C19-specific changes required."],
        evidence=src, related_drugs=drugs, **base)]


def _cyp2c9_vkorc1_findings(c9: Phenotype, vk: Phenotype | None) -> list[Finding]:
    pieces = [f"CYP2C9 activity score {c9.activity_score:.1f}/2.0"]
    sensitive = (c9.activity_score or 2.0) < 2.0
    if vk:
        pieces.append(f"VKORC1 {vk.diplotype}")
        if "AA" in vk.diplotype or "GA" in vk.diplotype:
            sensitive = True
    text = "; ".join(pieces)
    base = {"gene": "CYP2C9", "diplotype": c9.diplotype, "activity_score": c9.activity_score,
            "domain": Domain.DRUG}
    if sensitive:
        return [Finding(
            id="warfarin_sensitive", title="Warfarin sensitivity",
            summary="Your combined CYP2C9 + VKORC1 genotype calls for a lower-than-standard warfarin starting dose.",
            detail=(f"{text}. CPIC's pharmacogenetic warfarin algorithm predicts a lower stable maintenance dose "
                    "than the typical 5 mg/day. If you are ever started on warfarin, share this with your prescriber — "
                    "starting at the standard dose risks early over-anticoagulation and bleeding."),
            actions=[
                "Bring this finding to any cardiology / anticoagulation visit.",
                "If starting warfarin, ask about a CPIC-guided starting dose and INR check at day 3–5.",
            ],
            evidence=["CPIC: warfarin guideline", "PharmGKB: warfarin"],
            confidence=Confidence.HIGH, related_drugs=["warfarin"],
            requires_physician=True, **base)]
    return []


def _cyp3a5_findings(p: Phenotype) -> list[Finding]:
    if p.phenotype.startswith("Normal"):
        return [Finding(
            id="cyp3a5_expressor", gene="CYP3A5", title="CYP3A5 Expressor",
            summary="If transplanted, you will need a higher tacrolimus dose than non-expressors.",
            detail=("You express functional CYP3A5, which clears tacrolimus rapidly. Standard 'one-size-fits-all' "
                    "starting doses are usually too low for expressors and lead to sub-therapeutic levels."),
            actions=["If you ever undergo solid-organ transplant, share this with the transplant team — CPIC publishes a tacrolimus dosing guideline."],
            evidence=["CPIC: tacrolimus", "PharmGKB: CYP3A5"], confidence=Confidence.HIGH,
            related_drugs=["tacrolimus"], domain=Domain.DRUG, diplotype=p.diplotype,
            requires_physician=True)]
    return []


def _cyp1a2_findings(p: Phenotype) -> list[Finding]:
    if "Slow" in p.phenotype:
        return [Finding(
            id="cyp1a2_slow", gene="CYP1A2", title="CYP1A2 Slow Caffeine Metabolizer",
            summary="More than ~2 cups of coffee a day appears to raise your cardiovascular risk above baseline.",
            detail=("CYP1A2 clears caffeine. Slow metabolizers (CC at rs762551) keep caffeine in circulation "
                    "longer; epidemiologic data link >2 cups/day in slow metabolizers to higher rates of "
                    "hypertension and non-fatal MI."),
            actions=[
                "Cap caffeine intake at ~200 mg/day (≈ 2 small cups of coffee).",
                "Switch to half-caf, decaf, or tea after lunch — caffeine half-life can be 6–10 hours.",
                "Watch sleep latency: more sensitivity to evening caffeine than the average person.",
            ],
            evidence=["PharmGKB: CYP1A2", "PMID: 16522833"], confidence=Confidence.MODERATE,
            related_drugs=["caffeine"], domain=Domain.DRUG, diplotype=p.diplotype)]
    return []


def _slco1b1_findings(p: Phenotype) -> list[Finding]:
    if "Decreased" in p.phenotype or "Poor" in p.phenotype:
        sev = "marked" if "Poor" in p.phenotype else "elevated"
        return [Finding(
            id="slco1b1_lowfn", gene="SLCO1B1", title="Statin Myopathy Risk (SLCO1B1)",
            summary=f"You have a {sev} genetic risk of muscle pain on simvastatin.",
            detail=("SLCO1B1 transports statins into the liver. Reduced transport leaves more statin in circulation "
                    "to reach muscle. Risk is greatest with simvastatin (especially 80 mg)."),
            actions=[
                "If a statin is needed, ask about rosuvastatin, pravastatin, or fluvastatin — they are less SLCO1B1-dependent.",
                "Avoid simvastatin 80 mg outright.",
                "Report unexplained muscle pain or dark urine immediately.",
            ],
            evidence=["CPIC: simvastatin", "PharmGKB: SLCO1B1"], confidence=Confidence.HIGH,
            related_drugs=["simvastatin", "atorvastatin"], domain=Domain.DRUG,
            diplotype=p.diplotype, requires_physician=True)]
    return []


def _dpyd_findings(p: Phenotype) -> list[Finding]:
    if "Poor" in p.phenotype:
        return [Finding(
            id="dpyd_pm", gene="DPYD", title="DPYD Deficiency — Avoid 5-FU",
            summary="Standard fluoropyrimidine chemotherapy doses are likely toxic for you.",
            detail=("Two loss-of-function DPYD copies leave you unable to clear fluoropyrimidines (5-FU, capecitabine, tegafur). "
                    "Standard doses can cause life-threatening neutropenia, mucositis, and diarrhea."),
            actions=[
                "If cancer treatment is ever discussed, alert the oncology team to your DPYD status before any 5-FU or capecitabine dose is given.",
                "Alternative non-fluoropyrimidine regimens or strict dose reduction (≥50%) is required.",
            ],
            evidence=["CPIC: fluoropyrimidine guideline", "PharmGKB: DPYD"],
            confidence=Confidence.HIGH, related_drugs=["fluorouracil", "capecitabine"],
            domain=Domain.DRUG, diplotype=p.diplotype, requires_physician=True)]
    if "Intermediate" in p.phenotype:
        return [Finding(
            id="dpyd_im", gene="DPYD", title="Reduced DPYD Activity",
            summary="If you are ever prescribed 5-FU or capecitabine, dose reduction (~50%) is required.",
            detail="One loss-of-function DPYD allele reduces fluoropyrimidine clearance and raises severe-toxicity risk.",
            actions=["Flag this in any oncology setting; CPIC recommends a 50% starting-dose reduction."],
            evidence=["CPIC: fluoropyrimidine guideline"], confidence=Confidence.HIGH,
            related_drugs=["fluorouracil", "capecitabine"], domain=Domain.DRUG,
            diplotype=p.diplotype, requires_physician=True)]
    return []


def _tpmt_findings(p: Phenotype) -> list[Finding]:
    if "Poor" in p.phenotype:
        return [Finding(
            id="tpmt_pm", gene="TPMT", title="TPMT Deficient — Thiopurine Toxicity Risk",
            summary="Standard azathioprine / mercaptopurine doses can cause severe bone-marrow suppression.",
            detail=("TPMT inactivates thiopurines. Two non-functional copies cause toxic accumulation."),
            actions=[
                "If autoimmune disease, IBD, or leukemia therapy is considered, alert the prescribing clinician.",
                "CPIC recommends ~10× dose reduction or alternative therapy.",
            ],
            evidence=["CPIC: thiopurine guideline"], confidence=Confidence.HIGH,
            related_drugs=["azathioprine", "mercaptopurine"], domain=Domain.DRUG,
            diplotype=p.diplotype, requires_physician=True)]
    if "Intermediate" in p.phenotype:
        return [Finding(
            id="tpmt_im", gene="TPMT", title="Reduced TPMT Activity",
            summary="Lower-than-standard thiopurine starting dose recommended.",
            detail="One non-functional TPMT allele increases thiopurine accumulation; CPIC suggests 30–80% of standard dose.",
            actions=["Flag for any rheumatology, gastroenterology, or hematology team prescribing thiopurines."],
            evidence=["CPIC: thiopurine guideline"], confidence=Confidence.HIGH,
            related_drugs=["azathioprine", "mercaptopurine"], domain=Domain.DRUG,
            diplotype=p.diplotype, requires_physician=True)]
    return []


def _ugt1a1_findings(p: Phenotype) -> list[Finding]:
    if "Gilbert" in p.phenotype or p.diplotype == "*28/*28":
        return [Finding(
            id="ugt1a1_28", gene="UGT1A1", title="UGT1A1 *28/*28 (Gilbert syndrome)",
            summary="Mild benign jaundice expected during illness/fasting; major risk only with irinotecan.",
            detail=("Two copies of UGT1A1 *28 reduce bilirubin glucuronidation, causing transient unconjugated "
                    "hyperbilirubinemia. Clinically benign on its own, but severe neutropenia and diarrhea occur "
                    "with standard-dose irinotecan."),
            actions=[
                "Mild jaundice during illness, fasting, or heavy exercise is expected — usually no workup needed.",
                "If oncology ever proposes irinotecan, dose reduction is required.",
                "Atazanavir-related jaundice is more likely; ask about alternatives if HIV therapy is needed.",
            ],
            evidence=["CPIC: atazanavir guideline", "FDA label: irinotecan"],
            confidence=Confidence.HIGH, related_drugs=["irinotecan", "atazanavir"],
            domain=Domain.DRUG, diplotype=p.diplotype)]
    return []


def _ifnl3_findings(g: Genotype) -> list[Finding]:
    if g.is_no_call:
        return []
    n_t = sum(1 for a in g.alleles if a == "T")
    if n_t == 0:
        ph, msg = "CC", "favorable interferon response"
    elif n_t == 1:
        ph, msg = "CT", "intermediate interferon response"
    else:
        ph, msg = "TT", "less favorable interferon response"
    return [Finding(
        id="ifnl3", gene="IFNL3", title=f"IFNL3 {ph} — {msg}",
        summary="Predicts response to peginterferon-based hepatitis C therapy.",
        detail="If hepatitis C therapy with peginterferon-alfa is ever prescribed, this genotype "
               "predicts treatment response. Modern direct-acting antivirals (DAAs) are usually preferred regardless.",
        actions=["Mention this if hepatitis C is diagnosed and interferon-based therapy is considered."],
        evidence=["CPIC: peginterferon", "PharmGKB: rs12979860"], confidence=Confidence.HIGH,
        related_drugs=["peginterferon-alfa"], domain=Domain.DRUG, diplotype=ph,
        requires_physician=True)]


# ---------------------------------------------------------------------------
# Nutrient rules — genotype-driven (no star-allele logic needed)
# ---------------------------------------------------------------------------

def _mthfr_finding(c677t: Genotype | None, a1298c: Genotype | None) -> list[Finding]:
    if not c677t and not a1298c:
        return []
    n_677 = sum(1 for a in (c677t.alleles if c677t and not c677t.is_no_call else ()) if a == "T")
    n_1298 = sum(1 for a in (a1298c.alleles if a1298c and not a1298c.is_no_call else ()) if a == "C")
    severity = n_677 + 0.5 * n_1298
    if severity == 0:
        return []
    if n_677 == 2:
        title, sev_word = "MTHFR C677T Homozygous", "substantially"
    elif n_677 == 1:
        title, sev_word = "MTHFR C677T Heterozygous", "modestly"
    else:
        title, sev_word = "MTHFR A1298C Variant", "mildly"
    return [Finding(
        id="mthfr", gene="MTHFR", title=title,
        summary=f"Folic acid → methylfolate conversion is {sev_word} reduced.",
        detail=(f"You carry {n_677} copy/copies of C677T and {n_1298} of A1298C. The MTHFR enzyme converts "
                "folic acid (the form in fortified flour and most multivitamins) into 5-MTHF, the active form "
                "your cells use. Reduced activity can lead to higher homocysteine and lower active-folate availability."),
        actions=[
            "Switch your multivitamin to one containing 5-MTHF (L-methylfolate), 400–800 mcg.",
            "Avoid synthetic folic acid supplements above 400 mcg/day.",
            "Pair with B12 (methylcobalamin) and B6 to fully clear homocysteine.",
        ],
        evidence=["PMID: 18950845", "ClinVar: MTHFR"], confidence=Confidence.HIGH,
        related_nutrients=["folate", "vitamin B12", "vitamin B6"], domain=Domain.NUTRIENT)]


def _vdr_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n = sum(1 for a in g.alleles if a == "T")
    if n == 0:
        return []
    return [Finding(
        id="vdr_fok1", gene="VDR", title="VDR FokI variant — vitamin D receptor sensitivity",
        summary="You may need higher serum vitamin D to get the same cellular effect.",
        detail="The FokI 'f' (T) allele yields a slightly less transcriptionally active vitamin D receptor. "
               "People with one or two T alleles often need higher 25(OH)D levels to feel the same benefit.",
        actions=[
            "Target 50–70 ng/mL 25(OH)D rather than the population minimum of 30 ng/mL.",
            "Supplement vitamin D3 2000–4000 IU/day with vitamin K2 (MK-7).",
            "Re-check 25(OH)D twice per year — adjust dose to the target.",
        ],
        evidence=["PMID: 17138664"], confidence=Confidence.MODERATE,
        related_nutrients=["vitamin D", "vitamin K2"], domain=Domain.NUTRIENT,
        requires_physician=False)]


def _fut2_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n = sum(1 for a in g.alleles if a == "A")
    if n < 2:
        return []
    return [Finding(
        id="fut2", gene="FUT2", title="FUT2 Non-secretor — reduced gut B12 absorption",
        summary="Your gut produces less of the surface sugars B12-binding bacteria use.",
        detail="Non-secretors (AA at rs601338) absorb less vitamin B12 from food regardless of dietary intake.",
        actions=[
            "Supplement sublingual methylcobalamin (1000 mcg) several times per week.",
            "Have B12 (or holotranscobalamin) checked annually.",
            "Vegetarians and vegans should be especially diligent.",
        ],
        evidence=["PMID: 18776911"], confidence=Confidence.HIGH,
        related_nutrients=["vitamin B12"], domain=Domain.NUTRIENT)]


def _bco1_finding(g7501: Genotype | None, g12934: Genotype | None) -> list[Finding]:
    score = 0
    for g, allele in [(g7501, "T"), (g12934, "T")]:
        if g and not g.is_no_call:
            score += sum(1 for a in g.alleles if a == allele)
    if score < 2:
        return []
    return [Finding(
        id="bco1", gene="BCO1", title="BCO1 Reduced β-carotene Conversion",
        summary="Plant-based vitamin A (β-carotene) converts inefficiently to active retinol for you.",
        detail="Combined BCO1 variants reduce β-carotene → retinol conversion by ~30–50%.",
        actions=[
            "Prioritize preformed vitamin A: eggs, dairy, liver, oily fish.",
            "If supplementing, choose retinyl palmitate or cod liver oil — not β-carotene.",
            "Carrots and sweet potatoes are still healthy, just inefficient as a sole vitamin-A source.",
        ],
        evidence=["PMID: 19103647"], confidence=Confidence.MODERATE,
        related_nutrients=["vitamin A"], domain=Domain.NUTRIENT)]


# ---------------------------------------------------------------------------
# Diet / fitness
# ---------------------------------------------------------------------------

def _apoa2_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n = sum(1 for a in g.alleles if a == "C")
    if n < 2:
        return []
    return [Finding(
        id="apoa2", gene="APOA2", title="APOA2 Saturated-Fat Sensitive",
        summary="Saturated fat raises your BMI and lipid markers more than the average person.",
        detail=("CC at APOA2 −265 has been replicated across multiple cohorts as conferring a stronger "
                "BMI response to saturated fat (>22 g/day vs <22 g/day)."),
        actions=[
            "Cap saturated fat at <7% of daily calories (~15 g for a 2,000-kcal diet).",
            "Swap butter and coconut oil for olive oil, avocado, and nuts.",
            "Lean meats over fatty cuts; this is a genetic, not just a willpower, sensitivity.",
        ],
        evidence=["PMID: 19158204"], confidence=Confidence.MODERATE,
        related_nutrients=["saturated fat"], domain=Domain.DIET)]


def _lct_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n_t = sum(1 for a in g.alleles if a == "T")
    if n_t >= 1:
        return [Finding(
            id="lct_persistent", gene="MCM6/LCT", title="Lactase Persistent",
            summary="You retain the ability to digest lactose into adulthood.",
            detail="The T allele upstream of LCT keeps lactase expression on past childhood — dairy is fine.",
            actions=["No restriction needed for genetic reasons."],
            evidence=["PMID: 14745526"], confidence=Confidence.HIGH,
            related_nutrients=["lactose"], domain=Domain.DIET)]
    return [Finding(
        id="lct_intolerant", gene="MCM6/LCT", title="Genetic Lactose Intolerance",
        summary="Lactase production drops in adulthood — dairy will likely cause GI symptoms.",
        detail=("CC at rs4988235 means lactase expression typically declines after childhood. "
                "Most people in this group develop bloating, gas, or diarrhea with lactose-containing dairy."),
        actions=[
            "Switch to lactose-free milk, hard cheeses (naturally low lactose), or plant-based alternatives.",
            "Lactase enzyme tablets (e.g. Lactaid) help when consuming dairy occasionally.",
            "Symptoms typically worsen with age.",
        ],
        evidence=["PMID: 14745526"], confidence=Confidence.HIGH,
        related_nutrients=["lactose"], domain=Domain.DIET)]


def _actn3_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n_t = sum(1 for a in g.alleles if a == "T")
    if n_t == 2:
        return [Finding(
            id="actn3_xx", gene="ACTN3", title="ACTN3 XX — Endurance-Biased Muscle",
            summary="Your fast-twitch fibers lack α-actinin-3 — endurance training is your sweet spot.",
            detail=("XX (TT) genotype eliminates α-actinin-3 in fast-twitch fibers. "
                    "Studied across elite athletes: rare among power/sprint specialists, common among endurance athletes."),
            actions=[
                "Lean into endurance/strength-endurance: running, cycling, swimming, rowing.",
                "Train pure power sparingly; warm up well to reduce injury risk.",
                "You can still build strength — recovery from heavy eccentric work just runs slower.",
            ],
            evidence=["PMID: 12879365"], confidence=Confidence.HIGH, domain=Domain.DIET)]
    if n_t == 1:
        return [Finding(
            id="actn3_rx", gene="ACTN3", title="ACTN3 RX — Mixed Muscle Type",
            summary="You retain partial α-actinin-3 expression — versatile across power and endurance.",
            detail="Heterozygous carriers fall between RR and XX athletes.",
            actions=["Mixed training (strength + cardio) likely yields the best response."],
            evidence=["PMID: 12879365"], confidence=Confidence.MODERATE, domain=Domain.DIET)]
    return [Finding(
        id="actn3_rr", gene="ACTN3", title="ACTN3 RR — Power-Biased Muscle",
        summary="Full α-actinin-3 expression in fast-twitch fibers — biased toward power output.",
        detail="RR genotype is over-represented in elite sprinters and Olympic lifters.",
        actions=["Sprint, jump, and lift programming will likely yield strong adaptations."],
        evidence=["PMID: 12879365"], confidence=Confidence.HIGH, domain=Domain.DIET)]


def _aldh2_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n_a = sum(1 for a in g.alleles if a == "A")
    if n_a == 0:
        return []
    sev = "homozygous" if n_a == 2 else "heterozygous"
    return [Finding(
        id="aldh2", gene="ALDH2", title=f"ALDH2*2 ({sev})",
        summary="Acetaldehyde, the carcinogen produced by alcohol, accumulates in your body.",
        detail=("ALDH2*2 inactivates aldehyde dehydrogenase. Acetaldehyde lingers, causing facial flushing, "
                "headache, nausea — and, with regular drinking, a sharply elevated risk of esophageal cancer "
                "(IARC group 1)."),
        actions=[
            "Limit alcohol intake — homozygous carriers should avoid it entirely if possible.",
            "If you do drink, prefer occasional, small servings; avoid daily intake.",
            "Tell anesthesiologists before any procedure — drug clearance can shift.",
        ],
        evidence=["PMID: 19414485", "WHO IARC monograph"],
        confidence=Confidence.HIGH, related_drugs=["alcohol"], domain=Domain.DIET)]


def _adh1b_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n_a = sum(1 for a in g.alleles if a == "A")
    if n_a == 0:
        return []
    return [Finding(
        id="adh1b", gene="ADH1B", title=f"ADH1B*2 carrier ({'homozygous' if n_a == 2 else 'heterozygous'})",
        summary="You convert ethanol → acetaldehyde ~40× faster than the reference allele.",
        detail="The *2 allele protects against alcohol use disorder (acetaldehyde build-up is unpleasant) "
               "but makes acetaldehyde damage more acute, especially when paired with ALDH2*2.",
        actions=["Most carriers naturally drink less; pair with ALDH2 result for full risk picture."],
        evidence=["PMID: 19414485"], confidence=Confidence.HIGH,
        related_drugs=["alcohol"], domain=Domain.DIET)]


def _fto_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n = sum(1 for a in g.alleles if a == "A")
    if n == 0:
        return []
    return [Finding(
        id="fto", gene="FTO", title=f"FTO risk allele ({n} cop{'ies' if n == 2 else 'y'})",
        summary="Higher baseline appetite drive and preference for calorie-dense foods.",
        detail=("Each FTO risk allele adds ~+1.5 kg/m² BMI in adults at population level — modest but real. "
                "It is *not* destiny: lifestyle blunts the effect substantially."),
        actions=[
            "Front-load protein at breakfast (≥30 g) — increases satiety in carriers.",
            "Plan meals; FTO carriers under-estimate calorie intake more on impromptu eating.",
            "Aerobic activity 150+ min/week reduces FTO's BMI effect to near-zero in studies.",
        ],
        evidence=["PMID: 17434869"], confidence=Confidence.HIGH, domain=Domain.DIET)]


def _tcf7l2_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n = sum(1 for a in g.alleles if a == "T")
    if n == 0:
        return []
    return [Finding(
        id="tcf7l2", gene="TCF7L2", title=f"TCF7L2 risk allele ({n} cop{'ies' if n == 2 else 'y'})",
        summary="Most-replicated common variant for type-2 diabetes risk — fully lifestyle-modifiable.",
        detail=("Carriers have ~40% increased T2D risk per allele (homozygous ~2×). "
                "Diabetes Prevention Program data show lifestyle intervention works *better* in carriers."),
        actions=[
            "Annual fasting glucose + HbA1c starting in your 30s.",
            "Maintain BMI <25; resistance training improves insulin sensitivity beyond cardio alone.",
            "Mediterranean / low-glycemic diet patterns out-perform low-fat for T2D risk in carriers.",
        ],
        evidence=["PMID: 16415884"], confidence=Confidence.HIGH, domain=Domain.RISK)]


# ---------------------------------------------------------------------------
# Risk-awareness rules
# ---------------------------------------------------------------------------

def _apoe_finding(p: Phenotype) -> list[Finding]:
    if "ε4/ε4" in p.diplotype or "ε4" in p.phenotype:
        title = "APOE ε4 carrier"
        if "ε4/ε4" in p.diplotype:
            title = "APOE ε4/ε4 — high-risk genotype"
            elev = "≈8–12×"
        else:
            elev = "≈3–4×"
        return [Finding(
            id="apoe_e4", gene="APOE", title=title,
            summary=f"Your lifetime Alzheimer's risk is {elev} the population baseline — but lifestyle blunts it.",
            detail=("APOE ε4 is the strongest common genetic risk factor for late-onset Alzheimer's. "
                    "It is NOT diagnostic — most carriers never develop dementia. The protective levers are "
                    "well-studied: aerobic exercise, omega-3 intake, sleep quality, blood-pressure control, and hearing care."),
            actions=[
                "Aerobic exercise 150+ min/week (consistently the strongest signal in cohort data).",
                "Mediterranean / MIND diet pattern; oily fish 2×/week or 1g EPA+DHA daily.",
                "Treat hypertension aggressively from midlife.",
                "Use hearing aids if you develop hearing loss — strongly linked to dementia risk.",
                "Prioritize sleep; aim for 7–9h with treatment of sleep apnea if present.",
            ],
            evidence=["PMID: 8346443", "Lancet Commission on Dementia Prevention 2024"],
            confidence=Confidence.HIGH, domain=Domain.RISK, diplotype=p.diplotype)]
    if "ε2" in p.diplotype:
        return [Finding(
            id="apoe_e2", gene="APOE", title="APOE ε2 carrier",
            summary="Slightly reduced Alzheimer's risk; mildly higher remnant lipoproteins.",
            detail="ε2 is associated with reduced AD risk and modest hyperlipidemia (type III).",
            actions=["Standard lipid screening; no specific neurological action needed."],
            evidence=["PMID: 8346443"], confidence=Confidence.HIGH, domain=Domain.RISK,
            diplotype=p.diplotype)]
    return []


def _hfe_finding(p: Phenotype) -> list[Finding]:
    if p.diplotype in {"C282Y/C282Y", "C282Y/H63D"}:
        sev = "elevated" if p.diplotype == "C282Y/H63D" else "high"
        return [Finding(
            id="hfe_risk", gene="HFE", title=f"Hereditary Hemochromatosis Risk ({p.diplotype})",
            summary=f"Your iron-overload risk is {sev} — monitor ferritin and consider blood donation.",
            detail=("Penetrance is incomplete (many carriers never develop overload), but this diplotype is the "
                    "classical high-risk pattern. Iron accumulates slowly over decades."),
            actions=[
                "Get serum ferritin and transferrin saturation tested annually.",
                "Donate blood regularly if eligible — therapeutic and preventive.",
                "Avoid iron supplements unless explicitly prescribed.",
                "Limit vitamin C with iron-rich meals (it boosts absorption).",
            ],
            evidence=["PMID: 8696333"], confidence=Confidence.HIGH, domain=Domain.RISK,
            diplotype=p.diplotype, requires_physician=True)]
    return []


def _f5_finding(g: Genotype | None) -> list[Finding]:
    if not g or g.is_no_call:
        return []
    n = sum(1 for a in g.alleles if a == "T")
    if n == 0:
        return []
    return [Finding(
        id="factor_v_leiden", gene="F5", title=f"Factor V Leiden ({n} cop{'ies' if n == 2 else 'y'})",
        summary="Increased risk of venous thromboembolism, especially with extra triggers.",
        detail=("FVL slows the breakdown of activated factor V → activated factor V lingers → clots form more easily. "
                "Heterozygous: ~5× lifetime VTE risk. Homozygous: ~50× lifetime risk."),
        actions=[
            "Stay well-hydrated and walk on long flights or drives (>4h).",
            "Discuss with your doctor before any estrogen-containing contraceptive or HRT.",
            "Tell surgeons before any procedure — prophylactic anticoagulation may be considered.",
            "Watch for unilateral leg swelling, calf pain, or sudden shortness of breath.",
        ],
        evidence=["PMID: 8164741"], confidence=Confidence.HIGH, domain=Domain.RISK,
        diplotype=("TT" if n == 2 else "CT"), requires_physician=True)]


# ---------------------------------------------------------------------------
# Top-level dispatcher
# ---------------------------------------------------------------------------

def generate_findings(
    genos: dict[str, Genotype],
    phenos: dict[str, Phenotype],
) -> list[Finding]:
    findings: list[Finding] = []

    # Pharmacogenomics
    if "CYP2D6" in phenos:
        findings += _cyp2d6_findings(phenos["CYP2D6"])
    if "CYP2C19" in phenos:
        findings += _cyp2c19_findings(phenos["CYP2C19"])
    if "CYP2C9" in phenos:
        findings += _cyp2c9_vkorc1_findings(phenos["CYP2C9"], phenos.get("VKORC1"))
    if "CYP3A5" in phenos:
        findings += _cyp3a5_findings(phenos["CYP3A5"])
    if "CYP1A2" in phenos:
        findings += _cyp1a2_findings(phenos["CYP1A2"])
    if "SLCO1B1" in phenos:
        findings += _slco1b1_findings(phenos["SLCO1B1"])
    if "DPYD" in phenos:
        findings += _dpyd_findings(phenos["DPYD"])
    if "TPMT" in phenos:
        findings += _tpmt_findings(phenos["TPMT"])
    if "UGT1A1" in phenos:
        findings += _ugt1a1_findings(phenos["UGT1A1"])
    if g := genos.get("rs12979860"):
        findings += _ifnl3_findings(g)

    # Nutrigenomics
    findings += _mthfr_finding(genos.get("rs1801133"), genos.get("rs1801131"))
    findings += _vdr_finding(genos.get("rs2228570"))
    findings += _fut2_finding(genos.get("rs601338"))
    findings += _bco1_finding(genos.get("rs7501331"), genos.get("rs12934922"))

    # Diet / fitness
    findings += _apoa2_finding(genos.get("rs5082"))
    findings += _lct_finding(genos.get("rs4988235"))
    findings += _actn3_finding(genos.get("rs1815739"))
    findings += _aldh2_finding(genos.get("rs671"))
    findings += _adh1b_finding(genos.get("rs1229984"))
    findings += _fto_finding(genos.get("rs9939609"))
    findings += _tcf7l2_finding(genos.get("rs7903146"))

    # Risk awareness
    if "APOE" in phenos:
        findings += _apoe_finding(phenos["APOE"])
    if "HFE" in phenos:
        findings += _hfe_finding(phenos["HFE"])
    findings += _f5_finding(genos.get("rs6025"))

    return findings


def group_by_domain(findings: list[Finding]) -> dict[str, list[Finding]]:
    out: dict[str, list[Finding]] = {d.value: [] for d in Domain}
    for f in findings:
        out[f.domain.value].append(f)
    return out
