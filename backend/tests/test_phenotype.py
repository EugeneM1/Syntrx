"""Star-allele callers — checked against expected CPIC phenotypes."""

import pytest

from app.core.parser import parse_file
from app.core.phenotype import call_phenotypes


@pytest.mark.parametrize("profile,gene,expect_substr", [
    ("cyp2d6_poor_metabolizer", "CYP2D6", "Poor"),
    ("warfarin_sensitive_pgx_storm", "CYP2C9", "Poor"),
    ("warfarin_sensitive_pgx_storm", "VKORC1", "High"),
    ("warfarin_sensitive_pgx_storm", "SLCO1B1", "Poor"),
    ("warfarin_sensitive_pgx_storm", "CYP2C19", "Poor"),
    ("warfarin_sensitive_pgx_storm", "DPYD", "Intermediate"),
    ("ultrarapid_2c19_caffeine_slow", "CYP2C19", "Ultrarapid"),
    ("ultrarapid_2c19_caffeine_slow", "CYP1A2", "Slow"),
    ("apoe_e4_carrier_with_iron", "APOE", "ε4"),
    ("apoe_e4_carrier_with_iron", "HFE", "C282Y/H63D"),
    ("average_european", "CYP2D6", "Normal"),
    ("average_european", "CYP2C19", "Normal"),
])
def test_phenotype_matches(sample_files, profile, gene, expect_substr):
    parsed = parse_file(sample_files[profile])
    phenos = call_phenotypes(parsed.genotypes)
    assert gene in phenos, f"{gene} not called in {profile}"
    assert expect_substr.lower() in phenos[gene].phenotype.lower(), \
        f"{profile}/{gene}: got {phenos[gene].phenotype!r}, expected substring {expect_substr!r}"


def test_no_call_returns_no_phenotype(sample_files):
    # Force the *4 SNP to a no-call by editing the parsed dict
    parsed = parse_file(sample_files["average_european"])
    parsed.genotypes.pop("rs3892097", None)
    parsed.genotypes.pop("rs1065852", None)
    phenos = call_phenotypes(parsed.genotypes)
    # Without any LoF SNPs we still default to *1/*1 NM
    assert phenos["CYP2D6"].diplotype == "*1/*1"
