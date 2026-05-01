"""Drug-interaction checker."""

from app.core.parser import parse_file
from app.core.phenotype import call_phenotypes
from app.services import interactions


def test_codeine_avoid_for_pm(sample_files):
    parsed = parse_file(sample_files["cyp2d6_poor_metabolizer"])
    phenos = call_phenotypes(parsed.genotypes)
    rows = interactions.check(["codeine"], phenos)
    assert any(r.severity == "avoid" and r.drug == "codeine" for r in rows)


def test_clopidogrel_warning_for_2c19_pm(sample_files):
    parsed = parse_file(sample_files["warfarin_sensitive_pgx_storm"])
    phenos = call_phenotypes(parsed.genotypes)
    rows = interactions.check(["plavix"], phenos)
    sev = next(r.severity for r in rows if r.drug == "clopidogrel")
    assert sev == "avoid"


def test_unknown_drug_returns_info(sample_files):
    parsed = parse_file(sample_files["average_european"])
    phenos = call_phenotypes(parsed.genotypes)
    rows = interactions.check(["levitatesirin"], phenos)
    assert rows[0].severity == "info"
    assert "not in Syntrx" in rows[0].summary


def test_known_drugs_listing():
    drugs = interactions.known_drugs()
    assert "codeine" in drugs and "clopidogrel" in drugs
    assert len(drugs) > 20
