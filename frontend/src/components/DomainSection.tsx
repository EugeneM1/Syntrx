import { useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import clsx from "clsx";
import type { Finding } from "../lib/api";
import { rankFindings } from "../lib/api";
import FindingCard from "./FindingCard";

interface Props {
  title: string;
  description: string;
  findings: Finding[];
  narratives: Record<string, string>;
  defaultOpen?: boolean;
  accent?: string;
  icon?: ReactNode;
}

export default function DomainSection({
  title, description, findings, narratives, defaultOpen = true,
  accent = "bg-accent-600", icon,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  if (findings.length === 0) return null;

  const sorted = rankFindings(findings);
  const physician = findings.filter((f) => f.requires_physician).length;

  return (
    <section className="space-y-3">
      <button
        className="flex w-full items-center justify-between gap-3 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <div>
          <h2 className="flex items-center gap-2 text-xl font-semibold text-ink-900">
            <span className={clsx("h-2.5 w-2.5 rounded-full", accent)} />
            {icon}
            {title}
            <span className="text-sm font-normal text-ink-600">
              · {findings.length}
              {physician > 0 && ` · ${physician} need clinician`}
            </span>
          </h2>
          <p className="text-sm text-ink-600">{description}</p>
        </div>
        <ChevronDown className={clsx("h-5 w-5 text-ink-600 transition", open && "rotate-180")} />
      </button>
      {open && (
        <div className="grid gap-3">
          {sorted.map((f) => (
            <FindingCard key={f.id} finding={f} narration={narratives[f.id]} />
          ))}
        </div>
      )}
    </section>
  );
}
