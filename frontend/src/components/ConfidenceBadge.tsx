import clsx from "clsx";
import type { Confidence } from "../lib/api";

const STYLES: Record<Confidence, string> = {
  high: "bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200",
  moderate: "bg-amber-50 text-amber-700 ring-1 ring-amber-200",
  emerging: "bg-slate-100 text-ink-600 ring-1 ring-slate-200",
};

const LABEL: Record<Confidence, string> = {
  high: "High evidence",
  moderate: "Moderate",
  emerging: "Emerging",
};

export default function ConfidenceBadge({ value }: { value: Confidence }) {
  return <span className={clsx("pill", STYLES[value])}>{LABEL[value]}</span>;
}
