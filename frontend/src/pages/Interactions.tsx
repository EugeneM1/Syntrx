import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Pill, AlertTriangle, ShieldOff, ShieldAlert, ShieldCheck, Info, ArrowLeft, Search,
} from "lucide-react";
import clsx from "clsx";
import { checkInteractions, knownDrugs } from "../lib/api";
import DrugInput from "../components/DrugInput";

const SEV_META = {
  avoid:   { ring: "ring-rose-200",   bg: "bg-rose-50",   text: "text-rose-800",   Icon: ShieldOff,   label: "Avoid" },
  warning: { ring: "ring-rose-200",   bg: "bg-rose-50",   text: "text-rose-800",   Icon: ShieldAlert, label: "Warning" },
  caution: { ring: "ring-amber-200",  bg: "bg-amber-50",  text: "text-amber-800",  Icon: AlertTriangle, label: "Caution" },
  info:    { ring: "ring-emerald-200", bg: "bg-emerald-50", text: "text-emerald-800", Icon: ShieldCheck, label: "OK" },
} as const;

const QUICK_PICKS = [
  ["Pain", ["codeine", "tramadol", "ibuprofen"]],
  ["Cardiac", ["clopidogrel", "warfarin", "metoprolol"]],
  ["GI", ["omeprazole", "esomeprazole"]],
  ["Mood", ["sertraline", "escitalopram", "fluoxetine"]],
  ["Lipids", ["simvastatin", "atorvastatin", "rosuvastatin"]],
] as const;

export default function Interactions() {
  const { id = "" } = useParams();
  const [drugs, setDrugs] = useState<string[]>([]);
  const [known, setKnown] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Awaited<ReturnType<typeof checkInteractions>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { knownDrugs().then(setKnown).catch(() => {}); }, []);

  async function run(list = drugs) {
    if (list.length === 0) {
      setError("Add at least one drug first.");
      return;
    }
    setBusy(true); setError(null);
    try {
      setResult(await checkInteractions(id, list));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  function quickAdd(items: readonly string[]) {
    const merged = Array.from(new Set([...drugs, ...items]));
    setDrugs(merged);
  }

  const summary = result?.summary ?? {};
  const ordered = useMemo(() => {
    if (!result) return [];
    const RANK = { avoid: 0, warning: 1, caution: 2, info: 3 } as const;
    return [...result.interactions].sort((a, b) => RANK[a.severity] - RANK[b.severity]);
  }, [result]);

  return (
    <div className="space-y-6">
      <header className="flex items-end justify-between gap-3">
        <div>
          <Link to={`/report/${id}`} className="inline-flex items-center gap-1 text-xs text-ink-600 hover:text-ink-900">
            <ArrowLeft className="h-3 w-3" /> Back to report
          </Link>
          <h1 className="mt-1 flex items-center gap-2 text-2xl font-semibold">
            <Pill className="h-5 w-5 text-accent-600" /> Drug interaction checker
          </h1>
          <p className="text-sm text-ink-600">
            Cross-reference your medications against your pharmacogenomic profile.
            Flags are guidance, not prescriptions.
          </p>
        </div>
      </header>

      <div className="card space-y-4 p-4">
        <DrugInput
          drugs={drugs}
          onChange={setDrugs}
          suggestions={known}
          placeholder="Type a drug — e.g. clopidogrel, plavix, codeine"
        />

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-wider text-ink-600">Quick picks</span>
          {QUICK_PICKS.map(([label, items]) => (
            <button
              key={label}
              onClick={() => quickAdd(items)}
              className="pill bg-slate-100 text-ink-900 hover:bg-slate-200"
            >
              + {label}
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-600">
          <span>{known.length} drugs in catalog · {drugs.length} selected</span>
          <button className="btn-primary text-sm" disabled={busy} onClick={() => run()}>
            <Search className="h-3.5 w-3.5" />
            {busy ? "Checking…" : "Check interactions"}
          </button>
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
      </div>

      {result && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2 text-xs">
            {(["avoid", "warning", "caution", "info"] as const).map((k) => {
              const meta = SEV_META[k];
              const n = summary[k] ?? 0;
              return (
                <span key={k}
                      className={clsx("pill ring-1", meta.bg, meta.text, meta.ring,
                                     n === 0 && "opacity-50")}>
                  <meta.Icon className="mr-1 h-3 w-3" />
                  {meta.label}: {n}
                </span>
              );
            })}
          </div>

          {ordered.length === 0 && (
            <div className="card flex items-center gap-2 p-5 text-sm text-ink-600">
              <Info className="h-4 w-4" /> No drugs to evaluate yet.
            </div>
          )}

          {ordered.map((row, i) => {
            const meta = SEV_META[row.severity];
            const Icon = meta.Icon;
            return (
              <div key={i}
                   className={clsx("card overflow-hidden ring-1", meta.ring)}>
                <div className={clsx("flex items-start justify-between gap-3 px-4 py-3", meta.bg)}>
                  <div className="flex flex-wrap items-center gap-2">
                    <Icon className={clsx("h-4 w-4", meta.text)} />
                    <span className="font-mono text-sm font-semibold text-ink-900">{row.drug}</span>
                    <span className="font-mono text-xs text-ink-600">via {row.gene}</span>
                    <span className="pill bg-white text-ink-900 ring-1 ring-slate-200 text-xs">
                      {row.phenotype}
                    </span>
                  </div>
                  <span className={clsx("pill text-xs uppercase tracking-wide", meta.bg, meta.text, "ring-1", meta.ring)}>
                    {meta.label}
                  </span>
                </div>
                <div className="px-4 py-3 text-sm">
                  <p className="text-ink-900">{row.summary}</p>
                  {row.note && (
                    <p className="mt-1 text-xs italic text-ink-600">{row.note}</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
