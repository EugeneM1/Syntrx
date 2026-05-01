import { Sparkles, Stethoscope, ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";
import type { Finding } from "../lib/api";
import { rankFindings } from "../lib/api";

interface Props {
  findings: Finding[];
  reportId: string;
  max?: number;
}

/**
 * The "above the fold" panel — surfaces the 3 most clinically important
 * findings so the user sees them before scrolling.
 */
export default function Headlines({ findings, reportId, max = 3 }: Props) {
  const top = rankFindings(findings)
    .filter((f) => f.requires_physician || f.confidence === "high")
    .slice(0, max);

  if (top.length === 0) {
    return (
      <div className="card flex items-center gap-3 p-5">
        <Sparkles className="h-5 w-5 text-emerald-600" />
        <p className="text-sm text-ink-900">
          No high-priority pharmacogenomic alerts in your profile. Standard prescribing guidance applies.
        </p>
      </div>
    );
  }

  return (
    <section className="card overflow-hidden">
      <div className="flex items-center gap-2 border-b border-slate-100 bg-gradient-to-r from-accent-50 to-white px-5 py-3">
        <Sparkles className="h-4 w-4 text-accent-600" />
        <h2 className="text-sm font-semibold uppercase tracking-wider text-accent-700">
          Top {top.length} for you
        </h2>
      </div>
      <ol className="divide-y divide-slate-100">
        {top.map((f, i) => (
          <li key={f.id} className="flex gap-4 px-5 py-4">
            <div className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-full bg-accent-100 text-xs font-bold text-accent-700">
              {i + 1}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs text-ink-600">{f.gene}</span>
                {f.diplotype && (
                  <span className="pill bg-slate-100 font-mono text-ink-600">{f.diplotype}</span>
                )}
                {f.requires_physician && (
                  <span className="pill bg-rose-50 text-rose-700 ring-1 ring-rose-200">
                    <Stethoscope className="mr-1 h-3 w-3" /> Discuss with prescriber
                  </span>
                )}
              </div>
              <p className="mt-1 font-semibold text-ink-900">{f.title}</p>
              <p className="text-sm text-ink-600">{f.summary}</p>
              {f.actions[0] && (
                <p className="mt-2 text-sm text-ink-900">
                  <span className="font-medium text-ink-900">Next step:</span> {f.actions[0]}
                </p>
              )}
            </div>
          </li>
        ))}
      </ol>
      <Link
        to={`/interactions/${reportId}`}
        className="flex items-center justify-between border-t border-slate-100 bg-slate-50 px-5 py-3 text-sm font-medium text-accent-700 hover:bg-slate-100"
      >
        Run a drug-interaction check on these genes
        <ArrowRight className="h-4 w-4" />
      </Link>
    </section>
  );
}
