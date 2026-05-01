import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Beaker, ShieldCheck, FlaskConical, Sparkles, FileSearch,
  GitBranch, BookOpen,
} from "lucide-react";
import Upload from "../components/Upload";
import { listReports, type ReportSummary } from "../lib/api";

const PILLARS = [
  {
    icon: Beaker, accent: "text-accent-700 bg-accent-50",
    title: "Pharmacogenomics",
    body: "CPIC-grounded drug-gene calls — codeine, clopidogrel, warfarin, statins, SSRIs and 20+ more.",
  },
  {
    icon: FlaskConical, accent: "text-emerald-700 bg-emerald-50",
    title: "Nutrigenomics",
    body: "MTHFR, FUT2, VDR, BCO1 — what supplements actually work for your genotype.",
  },
  {
    icon: Sparkles, accent: "text-amber-700 bg-amber-50",
    title: "Diet & fitness",
    body: "Lactase, ACTN3 muscle type, ALDH2 alcohol — concrete daily-life shifts.",
  },
  {
    icon: ShieldCheck, accent: "text-rose-700 bg-rose-50",
    title: "Risk awareness",
    body: "Only lifestyle-modifiable risks — APOE, HFE, Factor V Leiden — never unactionable scores.",
  },
];

const STATS = [
  { value: "49+", label: "curated SNPs" },
  { value: "12",  label: "star-allele genes" },
  { value: "100%", label: "CPIC concordance" },
  { value: "0", label: "LLM hallucinations in clinical layer" },
];

export default function Home() {
  const [history, setHistory] = useState<ReportSummary[]>([]);
  useEffect(() => { listReports().then(setHistory).catch(() => setHistory([])); }, []);

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="grid gap-8 lg:grid-cols-[3fr,2fr] lg:items-start">
        <div className="space-y-5">
          <span className="pill bg-accent-100 text-accent-700">
            Personalized medicine, grounded in CPIC
          </span>
          <h1 className="text-4xl font-bold leading-tight tracking-tight text-ink-900 sm:text-5xl">
            Turn the raw DNA you already have into an{" "}
            <span className="text-accent-700">actionable health report</span>.
          </h1>
          <p className="max-w-xl text-lg leading-relaxed text-ink-600">
            Drop your 23andMe or AncestryDNA file. Syntrx parses the clinically
            actionable variants, cross-references PharmGKB and CPIC, and generates a
            cited, plain-English report on drug metabolism, nutrient optimization,
            diet, fitness, and lifestyle-modifiable risk.
          </p>
          <div className="grid gap-3 text-sm sm:grid-cols-2">
            {PILLARS.map(({ icon: Icon, accent, title, body }) => (
              <div key={title} className="card flex gap-3 p-4">
                <span className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${accent}`}>
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="font-semibold text-ink-900">{title}</p>
                  <p className="text-ink-600">{body}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <Upload />
      </section>

      {/* Headline stats */}
      <section className="card grid grid-cols-2 gap-4 p-6 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className="text-center">
            <p className="text-3xl font-bold text-accent-700">{s.value}</p>
            <p className="mt-1 text-xs uppercase tracking-wider text-ink-600">{s.label}</p>
          </div>
        ))}
      </section>

      {/* How it works */}
      <section className="space-y-4">
        <div>
          <h2 className="text-2xl font-semibold text-ink-900">How Syntrx generates a report</h2>
          <p className="text-sm text-ink-600">
            A four-stage agent pipeline. Recommendations are produced by a deterministic
            CPIC engine — the LLM only adds plain-English narration on top.
          </p>
        </div>
        <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { n: 1, t: "Parse",   d: "Extract genotypes at the 49 catalog SNPs from your file." },
            { n: 2, t: "Lookup",  d: "Retrieve evidence chunks per SNP (PharmGKB / SNPedia / PubMed)." },
            { n: 3, t: "Synthesize", d: "Run the deterministic CPIC engine; LLM adds friendly narration." },
            { n: 4, t: "Safety check", d: "Strip diagnostic phrases; append clinician disclaimers." },
          ].map((step) => (
            <li key={step.n} className="card p-4">
              <p className="text-xs font-semibold uppercase tracking-wider text-accent-700">
                Stage {step.n}
              </p>
              <p className="mt-1 font-semibold text-ink-900">{step.t}</p>
              <p className="mt-1 text-sm text-ink-600">{step.d}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* History */}
      {history.length > 0 && (
        <section className="space-y-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-ink-900">
            <FileSearch className="h-4 w-4" /> Your past reports
          </h2>
          <div className="card divide-y divide-slate-100">
            {history.map((h) => (
              <Link
                key={h.id} to={`/report/${h.id}`}
                className="flex items-center justify-between gap-4 px-4 py-3 text-sm hover:bg-slate-50"
              >
                <span className="font-mono text-xs text-ink-600">{h.id.slice(0, 8)}</span>
                <span className="flex-1 truncate">{h.headline ?? "—"}</span>
                <span className="text-xs text-ink-600">
                  {h.matched_variants} SNPs · {h.finding_count} findings
                </span>
                <span className="text-xs text-ink-600">
                  {new Date(h.created_at).toLocaleString()}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Trust footer */}
      <section className="grid gap-4 sm:grid-cols-2">
        <div className="card flex items-start gap-3 p-4">
          <BookOpen className="h-5 w-5 shrink-0 text-accent-600" />
          <div>
            <p className="font-semibold text-ink-900">Every recommendation cites its source</p>
            <p className="text-sm text-ink-600">
              CPIC clinical guidelines, FDA pharmacogenomic labels, and peer-reviewed PubMed IDs.
            </p>
          </div>
        </div>
        <div className="card flex items-start gap-3 p-4">
          <GitBranch className="h-5 w-5 shrink-0 text-accent-600" />
          <div>
            <p className="font-semibold text-ink-900">Deterministic + LLM, not pure-LLM</p>
            <p className="text-sm text-ink-600">
              The clinical layer is closed-form Python. The LLM only paraphrases. That is what
              keeps the system auditable and reproducible.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
