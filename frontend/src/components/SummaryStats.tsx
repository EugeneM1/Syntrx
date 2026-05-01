import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { CircleAlert, FileCheck2, Stethoscope } from "lucide-react";
import type { Report } from "../lib/api";
import { domainLabel } from "../lib/api";

const COLORS = ["#4f46e5", "#10b981", "#f59e0b", "#ef4444"];

export default function SummaryStats({ report }: { report: Report }) {
  const findings = report.findings ?? [];
  const byDomain = report.by_domain ?? {} as any;
  const counts = (Object.entries(byDomain) as [string, any[]][])
    .map(([k, v]) => ({ name: domainLabel(k), value: (v ?? []).length }))
    .filter((d) => d.value > 0);

  const total = counts.reduce((s, c) => s + c.value, 0);
  const physician = findings.filter((f) => f.requires_physician).length;
  const high = findings.filter((f) => f.confidence === "high").length;

  return (
    <div className="card grid items-center gap-4 p-5 lg:grid-cols-[2fr,3fr]">
      <div>
        <p className="text-xs uppercase tracking-wider text-ink-600">Findings</p>
        <p className="text-4xl font-bold text-ink-900">{total}</p>
        <p className="mt-2 text-xs text-ink-600">
          {report.parse.matched_variants} catalog SNPs read · {report.parse.coverage_pct}% coverage ·
          format <span className="font-mono">{report.parse.file_format}</span>
        </p>
        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
          <span className="pill bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200">
            <FileCheck2 className="mr-1 h-3 w-3" /> {high} high evidence
          </span>
          <span className="pill bg-rose-50 text-rose-700 ring-1 ring-rose-200">
            <Stethoscope className="mr-1 h-3 w-3" /> {physician} clinician notes
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {report.trace.map((t) => (
            <span key={t.name} className="pill bg-slate-100 text-ink-600 font-mono">
              {t.name} · {t.duration_ms}ms
            </span>
          ))}
        </div>
      </div>
      <div className="h-44">
        {counts.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={counts} dataKey="value" nameKey="name" innerRadius={42} outerRadius={68}
                   paddingAngle={2} stroke="white" strokeWidth={2}
                   label={({ name, value }) => `${name} (${value})`}
                   labelLine={false}>
                {counts.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(v: number, n) => [v, n]} />
            </PieChart>
          </ResponsiveContainer>
        ) : (
          <div className="grid h-full place-items-center text-sm text-ink-600">
            <div className="flex items-center gap-2">
              <CircleAlert className="h-4 w-4" /> No findings — try a different sample.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
