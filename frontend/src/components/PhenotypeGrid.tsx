import { useState } from "react";
import clsx from "clsx";
import { ChevronDown, FlaskConical } from "lucide-react";
import type { Phenotype } from "../lib/api";

// Categorical phenotype → color hint. Keys match the CPIC vocabulary.
function tone(phenotype: string): "ok" | "watch" | "warn" {
  const p = phenotype.toLowerCase();
  if (p.includes("poor") || p.includes("ultrarapid") || p.includes("high")
      || p.includes("deficient") || p.includes("compound")) return "warn";
  if (p.includes("intermediate") || p.includes("rapid") || p.includes("decreased")
      || p.includes("slow") || p.includes("moderate") || p.includes("ε4")
      || p.includes("carrier")) return "watch";
  return "ok";
}

const TONE_STYLES = {
  ok: "border-emerald-200 bg-emerald-50/50",
  watch: "border-amber-200 bg-amber-50/50",
  warn: "border-rose-200 bg-rose-50/50",
} as const;

const TONE_DOT = {
  ok: "bg-emerald-500",
  watch: "bg-amber-500",
  warn: "bg-rose-500",
} as const;

interface Props {
  phenotypes?: Record<string, Phenotype>;
}

export default function PhenotypeGrid({ phenotypes }: Props) {
  const [open, setOpen] = useState(true);
  const list = Object.values(phenotypes ?? {});
  if (list.length === 0) return null;

  // Order pharmacogenes first (most clinically actionable), then risk genes
  const PRIORITY = [
    "CYP2D6", "CYP2C19", "CYP2C9", "VKORC1", "SLCO1B1", "DPYD",
    "TPMT", "UGT1A1", "CYP3A5", "CYP1A2", "APOE", "HFE",
  ];
  list.sort((a, b) => PRIORITY.indexOf(a.gene) - PRIORITY.indexOf(b.gene));

  return (
    <section className="card overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left hover:bg-slate-50"
      >
        <div className="flex items-center gap-2">
          <FlaskConical className="h-4 w-4 text-accent-600" />
          <h2 className="text-base font-semibold">Phenotype summary</h2>
          <span className="pill bg-slate-100 text-ink-600">{list.length} genes called</span>
        </div>
        <ChevronDown className={clsx("h-5 w-5 text-ink-600 transition", open && "rotate-180")} />
      </button>
      {open && (
        <div className="grid gap-2 border-t border-slate-100 bg-slate-50/40 p-4 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((p) => {
            const t = tone(p.phenotype);
            return (
              <div key={p.gene}
                   className={clsx("rounded-xl border p-3 text-sm bg-white", TONE_STYLES[t])}>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-ink-900">{p.gene}</span>
                  <span className="flex items-center gap-1 text-xs text-ink-600">
                    <span className={clsx("h-1.5 w-1.5 rounded-full", TONE_DOT[t])} />
                    {p.diplotype}
                  </span>
                </div>
                <p className="mt-1 leading-snug text-ink-900">{p.phenotype}</p>
                {p.activity_score !== null && (
                  <p className="mt-1 text-[11px] text-ink-600">
                    Activity score {p.activity_score.toFixed(2)}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
