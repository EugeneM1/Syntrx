"""
Command-line interface.

    python -m app.cli analyze data/sample/sample_23andme.txt
    python -m app.cli analyze data/sample/sample_23andme.txt --json
    python -m app.cli interactions --report <id> --drugs codeine,clopidogrel
    python -m app.cli evaluate
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.core.phenotype import call_phenotypes
from app.services.interactions import check
from app.services.pipeline import run_pipeline
from app.services.report_store import ReportStore

app = typer.Typer(help="Syntrx CLI — run the pipeline locally.")
console = Console()
store = ReportStore.get_default()


@app.command()
def analyze(
    path: Path = typer.Argument(..., exists=True, readable=True),
    json_output: bool = typer.Option(False, "--json", help="Print full JSON report."),
    use_llm: bool = typer.Option(True, "--llm/--no-llm", help="Run the LLM narrator."),
) -> None:
    """Run the four-stage pipeline against a raw genetic file."""
    payload = path.read_bytes()
    report = run_pipeline(payload, filename=path.name, use_llm=use_llm)
    store.save(report)

    if json_output:
        print(json.dumps(report.to_dict(), indent=2))
        return

    console.print(Panel.fit(
        f"[bold]Syntrx report[/bold] {report.id[:8]}\n"
        f"Format: {report.parse.file_format.value}\n"
        f"Matched {report.parse.matched_variants}/{len(report.parse.genotypes) or '—'} catalog SNPs "
        f"({report.parse.coverage_pct:.0f}%)",
        title="Pipeline complete",
    ))

    for stage in report.trace:
        console.print(f"  [dim]{stage.duration_ms:>4} ms[/dim]  {stage.name:<10} {stage.summary}")

    table = Table(title="Findings", show_lines=True)
    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Gene", style="magenta")
    table.add_column("Title")
    table.add_column("Confidence", justify="center")
    for f in report.findings:
        table.add_row(f.domain.value, f.gene, f.title, f.confidence.value)
    console.print(table)


@app.command()
def interactions(
    report: str = typer.Option(..., "--report", help="Report ID from a prior `analyze` run."),
    drugs: str = typer.Option(..., "--drugs", help="Comma-separated drug names."),
) -> None:
    raw = store.get_genotypes(report)
    if not raw:
        raise typer.BadParameter(f"Report {report} not found in {store.root}")
    from app.core.parser import parse_bytes
    parsed = parse_bytes(raw)
    phenos = call_phenotypes(parsed.genotypes)
    rows = check([d.strip() for d in drugs.split(",") if d.strip()], phenos)

    table = Table(title=f"Interactions for {report[:8]}")
    table.add_column("Drug")
    table.add_column("Gene")
    table.add_column("Phenotype")
    table.add_column("Severity")
    table.add_column("Note")
    for i in rows:
        sev_color = {"avoid": "red", "warning": "red", "caution": "yellow", "info": "green"}[i.severity]
        table.add_row(i.drug, i.gene, i.phenotype, f"[{sev_color}]{i.severity}[/]", i.summary)
    console.print(table)


@app.command()
def evaluate() -> None:
    """Run the CPIC concordance suite (delegates to scripts/evaluate.py)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("eval", Path(__file__).resolve().parent.parent / "scripts" / "evaluate.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)  # type: ignore
    mod.main()


if __name__ == "__main__":
    app()
