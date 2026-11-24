"use client";

// Two chart forms cover everything on the site:
//  * BarList: ranked horizontal bars for "how big is each part" (one series, one hue).
//  * ChangeBars: diverging bars from a zero line for "what went up and down".
// Both follow the same specs: bars <= 24px thick with a 4px rounded data-end and a square
// baseline, values at the bar tip in text ink (never the bar colour), a hover/focus tooltip
// on every bar, and a table view so nothing depends on hovering or on colour.

import { useId, useState } from "react";
import { kwacha, kwachaShort, signedKwachaShort, signedPct } from "@/lib/format";

export type Bar = { key: string; label: string; value: number; note?: string };

function Tooltip({ title, value, note }: { title: string; value: string; note?: string }) {
  return (
    <div
      role="tooltip"
      className="pointer-events-none absolute top-full left-0 z-10 mt-1 max-w-xs rounded-lg border border-line bg-surface px-3 py-2 text-sm shadow-lg"
    >
      <div className="font-semibold tabular-nums">{value}</div>
      <div className="text-ink-2">{title}</div>
      {note && <div className="text-muted">{note}</div>}
    </div>
  );
}

function TableView({ caption, head, rows }: { caption: string; head: string[]; rows: (string | number)[][] }) {
  return (
    <details className="mt-3 text-sm">
      <summary className="cursor-pointer text-ink-2 hover:text-ink">Show as a table</summary>
      <table className="mt-2 w-full border-collapse tabular-nums">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr className="border-b border-line text-left text-ink-2">
            {head.map((h, i) => (
              <th key={h} scope="col" className={`py-1.5 font-medium ${i > 0 ? "text-right" : ""}`}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={String(r[0])} className="border-b border-line last:border-0">
              {r.map((c, i) => (
                <td key={i} className={`py-1.5 ${i > 0 ? "text-right" : ""}`}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

/** Ranked horizontal bars. `total` turns each value into a share in the tooltip and table. */
export function BarList({
  bars,
  total,
  caption,
  unit = "kwacha",
}: {
  bars: Bar[];
  total?: number;
  caption: string;
  unit?: "kwacha" | "stories";
}) {
  const [active, setActive] = useState<string | null>(null);
  const full = (v: number) => (unit === "kwacha" ? kwacha(v) : `${v} ${v === 1 ? "story" : "stories"}`);
  const short = (v: number) => (unit === "kwacha" ? kwachaShort(v) : String(v));
  const max = Math.max(...bars.map((b) => b.value), 1);
  const share = (v: number) => (total ? `${((v * 100) / total).toFixed(1)}% of the total` : undefined);

  return (
    <figure>
      <ul className="space-y-2.5" aria-label={caption}>
        {bars.map((b) => {
          const pct = (b.value / max) * 100;
          return (
            <li
              key={b.key}
              tabIndex={0}
              aria-label={`${b.label}: ${full(b.value)}${total ? `, ${share(b.value)}` : ""}`}
              onPointerEnter={() => setActive(b.key)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(b.key)}
              onBlur={() => setActive(null)}
              className="relative grid grid-cols-1 gap-1 rounded-md py-0.5 outline-offset-4 sm:grid-cols-[minmax(10rem,16rem)_1fr] sm:items-center sm:gap-3"
            >
              <span className="text-sm leading-tight text-ink-2">{b.label}</span>
              <span className="flex items-center gap-2">
                <span className="relative h-5 flex-1">
                  <span
                    className={`absolute inset-y-0 left-0 rounded-r-[4px] transition-opacity ${
                      active && active !== b.key ? "opacity-50" : ""
                    } bg-series`}
                    style={{ width: `max(${pct}%, 2px)` }}
                  />
                </span>
                <span className="w-20 shrink-0 text-right text-sm font-medium tabular-nums">
                  {short(b.value)}
                </span>
              </span>
              {active === b.key && <Tooltip title={b.label} value={full(b.value)} note={b.note ?? share(b.value)} />}
            </li>
          );
        })}
      </ul>
      <TableView
        caption={caption}
        head={total ? ["Line", "Amount", "Share"] : ["Line", unit === "kwacha" ? "Amount" : "Stories"]}
        rows={bars.map((b) =>
          total ? [b.label, full(b.value), `${((b.value * 100) / total).toFixed(1)}%`] : [b.label, full(b.value)],
        )}
      />
    </figure>
  );
}

export type Delta = { key: string; label: string; change: number; pct: number | null; before: number | null; after: number | null };

/** Diverging bars around zero: increases to the right in blue, decreases to the left in orange.
 *  The sign is also written out (+/−), so direction never depends on colour. */
export function ChangeBars({ rows, caption, before, after }: { rows: Delta[]; caption: string; before: string; after: string }) {
  const [active, setActive] = useState<string | null>(null);
  const max = Math.max(...rows.map((r) => Math.abs(r.change)), 1);
  const legendId = useId();

  return (
    <figure>
      <div id={legendId} className="mb-3 flex flex-wrap gap-4 text-sm text-ink-2">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-3 w-3 rounded-[3px] bg-up" aria-hidden /> More than {before}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-3 w-3 rounded-[3px] bg-down" aria-hidden /> Less than {before}
        </span>
      </div>
      <ul className="space-y-2.5" aria-label={caption} aria-describedby={legendId}>
        {rows.map((r) => {
          const w = (Math.abs(r.change) / max) * 50;
          const up = r.change >= 0;
          const label = r.before === null ? "new this year" : r.pct === null ? "" : signedPct(r.pct);
          return (
            <li
              key={r.key}
              tabIndex={0}
              aria-label={`${r.label}: ${signedKwachaShort(r.change)}${label ? `, ${label}` : ""}`}
              onPointerEnter={() => setActive(r.key)}
              onPointerLeave={() => setActive(null)}
              onFocus={() => setActive(r.key)}
              onBlur={() => setActive(null)}
              className="relative grid grid-cols-1 gap-1 rounded-md py-0.5 sm:grid-cols-[minmax(10rem,16rem)_1fr] sm:items-center sm:gap-3"
            >
              <span className="text-sm leading-tight text-ink-2">{r.label}</span>
              <span className="relative h-5">
                <span className="absolute inset-y-[-4px] left-1/2 w-px bg-axis" aria-hidden />
                <span
                  className={`absolute inset-y-0 ${up ? "left-1/2 rounded-r-[4px] bg-up" : "right-1/2 rounded-l-[4px] bg-down"} ${
                    active && active !== r.key ? "opacity-50" : ""
                  }`}
                  style={{ width: `max(${w}%, 2px)` }}
                />
                <span
                  className={`absolute top-1/2 -translate-y-1/2 text-xs font-medium whitespace-nowrap tabular-nums ${
                    up ? "right-[calc(50%+6px)]" : "left-[calc(50%+6px)]"
                  }`}
                >
                  {signedKwachaShort(r.change)}
                </span>
              </span>
              {active === r.key && (
                <Tooltip
                  title={r.label}
                  value={`${signedKwachaShort(r.change)}${label ? ` (${label})` : ""}`}
                  note={`${before}: ${r.before === null ? "none" : kwacha(r.before)} · ${after}: ${
                    r.after === null ? "none" : kwacha(r.after)
                  }`}
                />
              )}
            </li>
          );
        })}
      </ul>
      <TableView
        caption={caption}
        head={["Line", before, after, "Change"]}
        rows={rows.map((r) => [
          r.label,
          r.before === null ? "—" : kwacha(r.before),
          r.after === null ? "—" : kwacha(r.after),
          `${signedKwachaShort(r.change)}${r.pct !== null ? ` (${signedPct(r.pct)})` : ""}`,
        ])}
      />
    </figure>
  );
}
