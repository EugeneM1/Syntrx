import { useEffect, useMemo, useRef, useState } from "react";
import { X, Plus } from "lucide-react";

interface Props {
  drugs: string[];
  onChange: (drugs: string[]) => void;
  suggestions: string[];          // /api/interactions/drugs response
  placeholder?: string;
}

/**
 * Chip-style autocompleting input. Type a drug name + Enter / Tab to add a chip.
 * Backspace on empty input removes the last chip. Suggestions filter live.
 */
export default function DrugInput({ drugs, onChange, suggestions, placeholder }: Props) {
  const [text, setText] = useState("");
  const [highlight, setHighlight] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    const q = text.trim().toLowerCase();
    if (!q) return [];
    return suggestions
      .filter((s) => s.toLowerCase().includes(q) && !drugs.includes(s))
      .slice(0, 6);
  }, [text, suggestions, drugs]);

  useEffect(() => setHighlight(0), [text]);

  function add(drug: string) {
    const d = drug.trim().toLowerCase();
    if (!d) return;
    if (drugs.includes(d)) return;
    onChange([...drugs, d]);
    setText("");
    inputRef.current?.focus();
  }

  function remove(drug: string) {
    onChange(drugs.filter((x) => x !== drug));
    inputRef.current?.focus();
  }

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3 py-2 focus-within:ring-2 focus-within:ring-accent-500">
        {drugs.map((d) => (
          <span
            key={d}
            className="inline-flex items-center gap-1 rounded-md bg-accent-100 px-2 py-1 text-sm text-accent-800"
          >
            <span className="font-mono">{d}</span>
            <button
              onClick={() => remove(d)}
              className="rounded-full p-0.5 hover:bg-accent-200"
              aria-label={`Remove ${d}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={drugs.length === 0 ? (placeholder ?? "Type a drug name…") : ""}
          className="min-w-[8rem] flex-1 border-0 bg-transparent text-sm outline-none"
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              if (filtered.length > 0) add(filtered[highlight]);
              else if (text.trim()) add(text);
            } else if (e.key === "Backspace" && !text && drugs.length > 0) {
              remove(drugs[drugs.length - 1]);
            } else if (e.key === "ArrowDown") {
              e.preventDefault();
              setHighlight((h) => Math.min(h + 1, filtered.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setHighlight((h) => Math.max(h - 1, 0));
            } else if (e.key === "Tab" && filtered.length > 0) {
              e.preventDefault();
              add(filtered[highlight]);
            }
          }}
        />
      </div>

      {filtered.length > 0 && (
        <ul className="absolute left-0 right-0 top-full z-10 mt-1 max-h-56 overflow-auto rounded-xl border border-slate-200 bg-white shadow-lg">
          {filtered.map((s, i) => (
            <li key={s}>
              <button
                onMouseDown={(e) => { e.preventDefault(); add(s); }}
                className={`flex w-full items-center justify-between px-3 py-2 text-left text-sm font-mono ${
                  i === highlight ? "bg-accent-50 text-accent-800" : "hover:bg-slate-50"
                }`}
              >
                {s}
                <Plus className="h-3.5 w-3.5 text-ink-600" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
