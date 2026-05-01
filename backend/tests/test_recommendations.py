"""Recommendation engine — high-impact rules return correct findings."""

from app.core.parser import parse_file
from app.core.phenotype import call_phenotypes
from app.core.recommendations import generate_findings


def _findings_by_gene(file):
    parsed = parse_file(file)
    phenos = call_phenotypes(parsed.genotypes)
    return {f.gene: f for f in generate_findings(parsed.genotypes, phenos)}


def test_codeine_warning_for_pm(sample_files):
    f = _findings_by_gene(sample_files["cyp2d6_poor_metabolizer"])
    assert "CYP2D6" in f
    assert "codeine" in f["CYP2D6"].detail.lower()
    assert f["CYP2D6"].requires_physician
    assert f["CYP2D6"].confidence.value == "high"


def test_warfarin_storm_findings(sample_files):
    f = _findings_by_gene(sample_files["warfarin_sensitive_pgx_storm"])
    # warfarin sensitivity finding lives under CYP2C9
    assert "CYP2C9" in f
    assert "warfarin" in f["CYP2C9"].detail.lower()
    assert "SLCO1B1" in f
    assert "DPYD" in f


def test_caffeine_warning_when_slow(sample_files):
    f = _findings_by_gene(sample_files["ultrarapid_2c19_caffeine_slow"])
    assert "CYP1A2" in f
    assert "caffeine" in f["CYP1A2"].detail.lower()


def test_apoe_e4_carrier_finding(sample_files):
    f = _findings_by_gene(sample_files["apoe_e4_carrier_with_iron"])
    assert "APOE" in f
    assert "alzheimer" in f["APOE"].detail.lower()
    assert "HFE" in f


def test_alcohol_findings(sample_files):
    f = _findings_by_gene(sample_files["asian_alcohol_flush"])
    assert "ALDH2" in f
    assert "ADH1B" in f
    assert "acetaldehyde" in f["ALDH2"].detail.lower()


def test_average_european_minimal_alerts(sample_files):
    f = _findings_by_gene(sample_files["average_european"])
    # Should not raise warfarin sensitivity or DPYD warnings
    assert "CYP2C9" not in f or "warfarin" not in f["CYP2C9"].title.lower()
    assert "DPYD" not in f or "Poor" not in f["DPYD"].title
