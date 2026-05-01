import { Link, Outlet, useLocation } from "react-router-dom";
import { Dna } from "lucide-react";

export default function App() {
  const loc = useLocation();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-slate-200 bg-white/70 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2 font-semibold text-ink-900">
            <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent-600 text-white">
              <Dna className="h-4 w-4" />
            </span>
            Syntrx
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            <Link to="/" className={`btn-ghost ${loc.pathname === "/" ? "text-ink-900" : ""}`}>
              Upload
            </Link>
            <a className="btn-ghost" href="https://github.com" target="_blank" rel="noreferrer">
              GitHub
            </a>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-10">
        <Outlet />
      </main>
      <footer className="border-t border-slate-200 bg-white/70">
        <div className="mx-auto max-w-6xl px-6 py-4 text-xs text-ink-600">
          Syntrx is a genetic literacy and wellness tool — it does not diagnose disease or
          replace medical advice. All findings cite CPIC, PharmGKB, and peer-reviewed sources.
        </div>
      </footer>
    </div>
  );
}
