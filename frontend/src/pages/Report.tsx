import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, Download, Pill, Beaker, FlaskConical, Sparkles, ShieldCheck } from "lucide-react";
import { getReport, type Report } from "../lib/api";
import DomainSection from "../components/DomainSection";
import SummaryStats from "../components/SummaryStats";
import PhenotypeGrid from "../components/PhenotypeGrid";
import Headlines from "../components/Headlines";

export default function ReportView() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReport(id).then(setReport).catch((e) => setError(e.message));
  }, [id]);

  if (error)
    return (
      <div className="card p-6">
        <p className="text-rose-600">{error}</p>
        <Link to="/" className="mt-3 inline-block text-sm text-accent-700 hover:underline">
          ← Back to upload
        </Link>
      </div>
    );

  if (!report)
    return (
      <div className="card p-6 text-ink-600">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-accent-600" />
          Loading report…
        </div>
      </div>
    );

  return (
    <div className="space-y-8">
      {/* Page header */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-wider text-ink-600">Personalized health report</p>
          <h1 className="font-mono text-lg text-ink-900">{report.id.slice(0, 8)}</h1>
          <p className="text-sm text-ink-600">
            Generated {new Date(report.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <a
            href={`/api/reports/${report.id}/card.pdf`}
            target="_blank" rel="noreferrer"
            className="btn-ghost"
          >
            <Download className="h-4 w-4" /> PGx card (PDF)
          </a>
          <Link to={`/interactions/${report.id}`} className="btn-primary">
            <Pill className="h-4 w-4" /> Drug interaction checker <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </header>

      {/* Summary + headlines */}
      <SummaryStats report={report} />
      <Headlines findings={report.findings ?? []} reportId={report.id} />

      {/* All called phenotypes at a glance */}
      <PhenotypeGrid phenotypes={report.phenotypes} />

      {/* Domain sections — empty arrays for older reports */}
      <DomainSection
        title="Drug metabolism"
        accent="bg-accent-600"
        icon={<Beaker className="h-4 w-4 text-accent-600" />}
        description="How your CYP enzymes shape prescription medication response."
        findings={report.by_domain?.drug_metabolism ?? []}
        narratives={report.narratives ?? {}}
      />
      <DomainSection
        title="Nutrient optimization"
        accent="bg-emerald-500"
        icon={<FlaskConical className="h-4 w-4 text-emerald-600" />}
        description="Genotype-specific vitamin and mineral guidance."
        findings={report.by_domain?.nutrient ?? []}
        narratives={report.narratives ?? {}}
      />
      <DomainSection
        title="Diet & fitness"
        accent="bg-amber-500"
        icon={<Sparkles className="h-4 w-4 text-amber-600" />}
        description="Macronutrient response, food sensitivities, exercise programming."
        findings={report.by_domain?.diet_fitness ?? []}
        narratives={report.narratives ?? {}}
      />
      <DomainSection
        title="Lifestyle-modifiable risk"
        accent="bg-rose-500"
        icon={<ShieldCheck className="h-4 w-4 text-rose-600" />}
        description="Risk-aware findings where action can change the trajectory."
        findings={report.by_domain?.risk_awareness ?? []}
        narratives={report.narratives ?? {}}
      />

      <p className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs leading-relaxed text-ink-600">
        {report.disclaimer}
      </p>
    </div>
  );
}
