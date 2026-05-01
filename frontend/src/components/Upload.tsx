import { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CloudUpload, Loader2, FileText, Lock } from "lucide-react";
import { uploadFile } from "../lib/api";

const STAGES = [
  "Parsing genotypes…",
  "Looking up evidence…",
  "Synthesizing recommendations…",
  "Running safety checks…",
];

export default function Upload() {
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stageIdx, setStageIdx] = useState(0);
  const navigate = useNavigate();

  const handle = useCallback(async (file: File) => {
    setBusy(true); setError(null); setStageIdx(0);
    const tick = setInterval(() => setStageIdx((i) => (i + 1) % STAGES.length), 700);
    try {
      const report = await uploadFile(file, true);
      clearInterval(tick);
      navigate(`/report/${report.id}`);
    } catch (e: any) {
      clearInterval(tick);
      setError(e.message || "Upload failed");
      setBusy(false);
    }
  }, [navigate]);

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault(); setDrag(false);
          const f = e.dataTransfer.files?.[0]; if (f) handle(f);
        }}
        className={`card flex flex-col items-center justify-center gap-3 px-8 py-14 text-center transition
          ${drag
            ? "ring-2 ring-accent-500 bg-accent-50 border-accent-500"
            : "border-dashed border-2 border-slate-300 hover:border-accent-300"}`}
      >
        <div className="grid h-12 w-12 place-items-center rounded-2xl bg-accent-50 text-accent-600">
          <CloudUpload className="h-6 w-6" />
        </div>
        <h2 className="text-lg font-semibold">Upload your raw genetic data</h2>
        <p className="max-w-md text-sm leading-relaxed text-ink-600">
          Drop a <span className="font-mono text-ink-900">.txt</span>,{" "}
          <span className="font-mono text-ink-900">.zip</span>,{" "}
          <span className="font-mono text-ink-900">.gz</span>, or{" "}
          <span className="font-mono text-ink-900">.pdf</span> file from
          23andMe, AncestryDNA, or any pharmacogenomic test report — or click to browse.
        </p>
        <label className="btn-primary cursor-pointer">
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CloudUpload className="h-4 w-4" />}
          {busy ? "Analyzing…" : "Choose file"}
          <input
            type="file"
            accept=".txt,.zip,.gz,.pdf,text/plain,application/pdf,application/zip,application/gzip"
            className="hidden"
            disabled={busy}
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handle(f); }}
          />
        </label>

        {busy && (
          <div className="mt-1 w-full max-w-xs">
            <div className="text-xs text-ink-600">{STAGES[stageIdx]}</div>
            <div className="mt-2 h-1 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-accent-600 transition-all"
                style={{ width: `${((stageIdx + 1) / STAGES.length) * 100}%` }}
              />
            </div>
          </div>
        )}
        {error && <p className="text-sm text-rose-600">{error}</p>}
      </div>

      {/* Trust + sample data hint */}
      <div className="grid grid-cols-2 gap-3 text-xs text-ink-600">
        <div className="card flex items-center gap-2 p-3">
          <Lock className="h-4 w-4 text-emerald-600" />
          <span>Files are processed locally — never sent to a third party.</span>
        </div>
        <div className="card flex items-center gap-2 p-3">
          <FileText className="h-4 w-4 text-accent-600" />
          <span>
            No file? Try <span className="font-mono">backend/data/sample/sample_warfarin_sensitive_pgx_storm.txt</span>
          </span>
        </div>
      </div>
    </div>
  );
}
