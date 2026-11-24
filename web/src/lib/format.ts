// Display helpers. Amounts arrive as whole kwacha.

/** K1,079,607,654 */
export function kwacha(n: number): string {
  return `K${Math.round(n).toLocaleString("en-ZM")}`;
}

/** K1.08 bn, K732.1 m, K818.5 k, K950 — for headlines, axes and bar labels. */
export function kwachaShort(n: number): string {
  const abs = Math.abs(n);
  const sign = n < 0 ? "−" : "";
  if (abs >= 1e9) return `${sign}K${trim((abs / 1e9).toFixed(2))} bn`;
  if (abs >= 1e6) return `${sign}K${trim((abs / 1e6).toFixed(1))} m`;
  if (abs >= 1e3) return `${sign}K${trim((abs / 1e3).toFixed(1))} k`;
  return `${sign}K${Math.round(abs)}`;
}

function trim(s: string): string {
  return s.replace(/\.0+$/, "").replace(/(\.\d*?)0+$/, "$1");
}

/** +47.5% / −17.7% / 0% */
export function signedPct(n: number): string {
  if (n === 0) return "0%";
  return `${n > 0 ? "+" : "−"}${Math.abs(n).toLocaleString("en-ZM", { maximumFractionDigits: 1 })}%`;
}

/** +K37.96 m */
export function signedKwachaShort(n: number): string {
  return n > 0 ? `+${kwachaShort(n)}` : kwachaShort(n);
}

export function longDate(iso: string): string {
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

const SECTOR_LABELS: Record<string, string> = {
  education: "Education",
  health: "Health",
  water_sanitation: "Water and sanitation",
  roads_drainage: "Roads and drainage",
  markets: "Markets",
  empowerment: "Empowerment",
  community_safety: "Community and safety",
};

const STATUS_LABELS: Record<string, string> = {
  planned: "Planned",
  under_construction: "Under construction",
  completed: "Completed",
  commissioned: "Commissioned",
  handed_over: "Handed over",
};

export const sectorLabel = (s: string) => SECTOR_LABELS[s] ?? s;
export const statusLabel = (s: string) => STATUS_LABELS[s] ?? s;
export const SECTORS = Object.keys(SECTOR_LABELS);
export const STATUSES = Object.keys(STATUS_LABELS);

/** The books' names are inconsistent ("District Health servcies"); tidy only the casing. */
export function tidyName(name: string): string {
  return name.replace(/servcies/i, "services").replace(/\(Transfers\)/, " (transfers)");
}

/** Many council headlines are in capitals; show them in sentence case so they read calmly. */
export function sentenceCase(title: string): string {
  const letters = title.replace(/[^A-Za-z]/g, "");
  const upper = letters.replace(/[^A-Z]/g, "").length;
  if (letters.length === 0 || upper / letters.length < 0.7) return title;
  // Words with digits ("K3.7M", "21,000") keep their case.
  const lower = title
    .split(/(\s+)/)
    .map((w) => (/\d/.test(w) ? w : w.toLowerCase()))
    .join("");
  const keep = ["CDF", "LCC", "IMS", "NGOCC", "CDFC", "DC", "ECE"];
  let out = lower.charAt(0).toUpperCase() + lower.slice(1);
  for (const k of keep) out = out.replace(new RegExp(`\\b${k}\\b`, "gi"), k);
  // Proper nouns we can be sure of: the city, the country and its constituencies.
  for (const p of ["Lusaka", "Zambia", "Chawama", "Kabwata", "Kanyama", "Mandevu", "Matero", "Munali", "Central"])
    out = out.replace(new RegExp(`\\b${p}\\b`, "gi"), p);
  return out.replace(/(^|[.!?:;]\s+)([a-z])/g, (_, a: string, b: string) => a + b.toUpperCase());
}
