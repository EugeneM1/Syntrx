import { useState } from "react";
import { ChevronDown, AlertTriangle, Stethoscope, Pill, Quote, BookOpen } from "lucide-react";
import clsx from "clsx";
import type { Finding } from "../lib/api";
import ConfidenceBadge from "./ConfidenceBadge";

interface Props {
  finding: Finding;
  narration?: string;
}

export default function FindingCard({ finding, narration }: Props) {
  const [open, setOpen] = useState(false);
  const requirePhys = finding.requires_physician;

  return (
    <div
      className={clsx(
        "card overflow-hidden transition",
        requirePhys && "ring-1 ring-rose-100",
      )}
    >
      <button
        className="grid w-full grid-cols-[1fr_auto] items-start gap-4 px-5 py-4 text-left hover:bg-slate-50"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs font-semibold text-ink-900">{finding.gene}</span>
            {finding.diplotype && (
              <span className="pill bg-slate-100 text-ink-600 font-mono">{finding.diplotype}</span>
            )}
            <ConfidenceBadge value={finding.confidence} />
            {requirePhys && (
              <span className="pill bg-rose-50 text-rose-700 ring-1 ring-rose-200">
                <Stethoscope className="mr-1 h-3 w-3" /> Discuss with prescriber
              </span>
            )}
          </div>
          <h3 className="mt-1.5 text-base font-semibold leading-snug text-ink-900">
            {finding.title}
          </h3>
          <p className="mt-0.5 text-sm leading-relaxed text-ink-600">{finding.summary}</p>
        </div>
        <ChevronDown
          className={clsx("mt-1 h-5 w-5 shrink-0 text-ink-600 transition", open && "rotate-180")}
        />
      </button>

      {open && (
        <div className="space-y-5 border-t border-slate-100 bg-slate-50/50 px-5 py-5 text-sm">
          {/* What it means */}
          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-ink-600">
              What this means
            </h4>
            <p className="leading-relaxed text-ink-900">{finding.detail}</p>
          </div>

          {/* LLM narration block, if any */}
          {narration && (
            <div className="flex gap-3 rounded-xl border border-accent-100 bg-accent-50 px-4 py-3 text-accent-900">
              <Quote className="mt-0.5 h-4 w-4 shrink-0 text-accent-600" />
              <p className="leading-relaxed">{narration}</p>
            </div>
          )}

          {/* Action items */}
          <div>
            <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ink-600">
              <AlertTriangle className="h-3 w-3" /> What to do
            </h4>
            <ul className="space-y-2 text-ink-900">
              {finding.actions.map((a, i) => (
                <li key={i} className="flex gap-2.5 leading-relaxed">
                  <span
                    aria-hidden
                    className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-accent-600"
                  />
                  <span>{a}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Related drugs / nutrients */}
          {(finding.related_drugs.length > 0 || finding.related_nutrients.length > 0) && (
            <div>
              <h4 className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ink-600">
                <Pill className="h-3 w-3" /> Affects
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {finding.related_drugs.map((d) => (
                  <span
                    key={d}
                    className="pill bg-white text-ink-900 ring-1 ring-slate-200 font-mono"
                  >
                    {d}
                  </span>
                ))}
                {finding.related_nutrients.map((n) => (
                  <span
                    key={n}
                    className="pill bg-white text-ink-900 ring-1 ring-slate-200"
                  >
                    {n}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Citations */}
          <div className="border-t border-slate-200 pt-3">
            <h4 className="mb-1 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-ink-600">
              <BookOpen className="h-3 w-3" /> Sources
            </h4>
            <p className="text-xs leading-relaxed text-ink-600">{finding.evidence.join(" · ")}</p>
          </div>
        </div>
      )}
    </div>
  );
}
