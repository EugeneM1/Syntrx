// Tiny typed API client.
//
// Dev:  Vite's dev server proxies /api → backend (vite.config.ts).
// Prod: VITE_API_URL (set at build time on the Vercel side) points at the
//       deployed backend. When unset, requests fall back to same-origin /api.

const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export type Confidence = "high" | "moderate" | "emerging";
export type Domain = "drug_metabolism" | "nutrient" | "diet_fitness" | "risk_awareness";

export interface Finding {
  id: string;
  domain: Domain;
  gene: string;
  title: string;
  summary: string;
  detail: string;
  actions: string[];
  confidence: Confidence;
  evidence: string[];
  related_drugs: string[];
  related_nutrients: string[];
  diplotype: string | null;
  activity_score: number | null;
  requires_physician: boolean;
}

export interface Phenotype {
  gene: string;
  diplotype: string;
  phenotype: string;
  activity_score: number | null;
  confidence: Confidence;
  source: string;
}

export interface Trace {
  name: string;
  duration_ms: number;
  summary: string;
  metadata: Record<string, unknown>;
}

export interface Report {
  id: string;
  created_at: string;
  parse: {
    file_format: string;
    total_variants: number;
    matched_variants: number;
    no_calls: number;
    coverage_pct: number;
  };
  catalog: Record<string, number>;
  phenotypes: Record<string, Phenotype>;
  findings: Finding[];
  by_domain: Record<Domain, Finding[]>;
  narratives: Record<string, string>;
  disclaimer: string;
  trace: Trace[];
}

export interface ReportSummary {
  id: string;
  created_at: string;
  matched_variants: number;
  finding_count: number;
  headline: string | null;
}

export async function uploadFile(file: File, useLLM = true): Promise<Report> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload?use_llm=${useLLM}`, { method: "POST", body: fd });
  if (!res.ok) {
    // FastAPI error responses come as { detail: "..." } — surface the detail
    let detail = `${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      detail = await res.text();
    }
    throw new Error(detail);
  }
  return res.json();
}

export async function getReport(id: string): Promise<Report> {
  const res = await fetch(`${API_BASE}/api/reports/${id}`);
  if (!res.ok) throw new Error("Report not found");
  return res.json();
}

export async function listReports(): Promise<ReportSummary[]> {
  const res = await fetch(`${API_BASE}/api/reports`);
  if (!res.ok) throw new Error("Could not load reports");
  return res.json();
}

export async function checkInteractions(reportId: string, drugs: string[]) {
  const fd = new FormData();
  fd.append("drugs", drugs.join(","));
  fd.append("report_id", reportId);
  const res = await fetch(`${API_BASE}/api/interactions/check`, { method: "POST", body: fd });
  if (!res.ok) throw new Error("Check failed");
  return res.json() as Promise<{
    drugs: string[];
    interactions: {
      drug: string;
      gene: string;
      phenotype: string;
      severity: "info" | "caution" | "warning" | "avoid";
      summary: string;
      note: string;
    }[];
    summary: Record<string, number>;
  }>;
}

export async function knownDrugs(): Promise<string[]> {
  const r = await fetch(`${API_BASE}/api/interactions/drugs`);
  return r.json();
}

// ---------- helpers ----------

const LABEL_MAP: Record<Domain, string> = {
  drug_metabolism: "Drug metabolism",
  nutrient: "Nutrients",
  diet_fitness: "Diet & fitness",
  risk_awareness: "Risk awareness",
};
export const domainLabel = (d: Domain | string) => LABEL_MAP[d as Domain] ?? d;

const SEVERITY_RANK: Record<Confidence, number> = { high: 0, moderate: 1, emerging: 2 };
export function rankFindings(findings: Finding[]): Finding[] {
  // Highest impact first: physician-required + high evidence wins.
  return [...findings].sort((a, b) => {
    if (a.requires_physician !== b.requires_physician) return a.requires_physician ? -1 : 1;
    return SEVERITY_RANK[a.confidence] - SEVERITY_RANK[b.confidence];
  });
}
