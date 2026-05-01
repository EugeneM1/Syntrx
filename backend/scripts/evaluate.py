"""
CPIC concordance evaluation.

For each synthetic profile we know the *expected* pharmacogenomic
phenotype. We run the pipeline against each and report the match rate.
This becomes the talking point in the resume / interview narrative
("X% concordance against CPIC across Y drug-gene pairs").
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

# Allow running as `python scripts/evaluate.py` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.parser import parse_file
from app.core.phenotype import call_phenotypes


# Expected gene → phenotype substring per profile
EXPECTED = {
    "average_european": {
        "CYP2D6": "Normal", "CYP2C19": "Normal", "CYP2C9": "Normal",
        "VKORC1": "Standard", "DPYD": "Normal",
    },
    "cyp2d6_poor_metabolizer": {
        "CYP2D6": "Poor",
    },
    "warfarin_sensitive_pgx_storm": {
        "CYP2C9": "Poor",
        "VKORC1": "High",
        "SLCO1B1": "Poor",
        "DPYD": "Intermediate",
        "CYP2C19": "Poor",
    },
    "ultrarapid_2c19_caffeine_slow": {
        "CYP2C19": "Ultrarapid",
        "CYP1A2": "Slow",
    },
    "apoe_e4_carrier_with_iron": {
        "APOE": "ε4",
        "HFE": "C282Y/H63D",
    },
    "asian_alcohol_flush": {
        # ALDH2/ADH1B are not in `phenotype.py` callers — handled at finding-level
    },
}


def main() -> None:
    console = Console()
    sample_dir = Path(__file__).resolve().parent.parent / "data" / "sample"
    if not list(sample_dir.glob("sample_*.txt")):
        console.print("[yellow]No sample files found — run generate_sample_data.py first.[/]")
        return

    table = Table(title="CPIC Concordance")
    table.add_column("Profile")
    table.add_column("Gene")
    table.add_column("Expected")
    table.add_column("Got")
    table.add_column("Match", justify="center")

    total = 0
    correct = 0
    for path in sorted(sample_dir.glob("sample_*.txt")):
        if path.stem == "sample_23andme":
            continue
        profile = path.stem.replace("sample_", "")
        expected = EXPECTED.get(profile, {})
        if not expected:
            continue
        parsed = parse_file(path)
        phenos = call_phenotypes(parsed.genotypes)
        for gene, want in expected.items():
            got = phenos.get(gene)
            label = got.phenotype if got else "(no call)"
            ok = bool(got and want.lower() in label.lower())
            total += 1
            correct += int(ok)
            table.add_row(profile, gene, want, label, "[green]✓[/]" if ok else "[red]✗[/]")

    console.print(table)
    if total:
        pct = 100.0 * correct / total
        color = "green" if pct >= 95 else "yellow" if pct >= 85 else "red"
        console.print(f"\n[{color}]Concordance: {correct}/{total} = {pct:.1f}%[/]")


if __name__ == "__main__":
    main()
