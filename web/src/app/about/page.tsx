import type { Metadata } from "next";
import { Section } from "@/components/ui";
import { api, type Check } from "@/lib/api";
import { longDate } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "About the data" };

const STATUS: Record<Check["status"], { icon: string; label: string; className: string }> = {
  pass: { icon: "✓", label: "Pass", className: "bg-good" },
  warn: { icon: "!", label: "Warning", className: "bg-warning text-black" },
  fail: { icon: "✕", label: "Failed", className: "bg-critical" },
};

export default async function About() {
  const q = await api.quality();
  const order = { fail: 0, warn: 1, pass: 2 };
  const checks = [...q.checks].sort((a, b) => order[a.status] - order[b.status]);

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-tight">About the data</h1>
        <p className="mt-2 text-ink-2">
          Every number on this site comes from documents Lusaka City Council publishes. We download them, read
          each table line by line, and then check the result against the totals printed in the books
          before anything is published.
        </p>
      </div>

      <Section title="How it's made">
        <ol className="list-decimal space-y-2 pl-5 text-sm text-ink-2">
          <li>
            <strong className="text-ink">Fetch.</strong> The approved budget books (PDF) and every news post are
            downloaded from lcc.gov.zm, and each file is fingerprinted.
          </li>
          <li>
            <strong className="text-ink">Read.</strong> Revenue, spending by type and spending by programme are read
            from each book. News posts about the CDF are tagged by constituency, sector and stage.
          </li>
          <li>
            <strong className="text-ink">Check.</strong> Every total in the books is added up again from its lines. A
            real mismatch stops publication. Small rounding gaps in the books and restated figures are published
            as warnings, below.
          </li>
          <li>
            <strong className="text-ink">Publish.</strong> The result is saved as plain CSV files anyone can open in
            Excel, and served through a free public API.
          </li>
        </ol>
      </Section>

      <Section
        title="Quality checks"
        intro={`${q.summary.pass ?? 0} passed, ${q.summary.warn ?? 0} warnings, ${q.summary.fail ?? 0} failed.${
          q.loaded_at ? ` Data loaded ${longDate(q.loaded_at.slice(0, 10))}.` : ""
        }`}
      >
        <ul className="divide-y divide-line">
          {checks.map((c, i) => {
            const s = STATUS[c.status];
            return (
              <li key={i} className="flex gap-3 py-3">
                <span
                  className={`mt-0.5 inline-flex h-5 shrink-0 items-center gap-1 rounded-full px-2 text-xs font-semibold text-white ${s.className}`}
                >
                  <span aria-hidden>{s.icon}</span>
                  {s.label}
                </span>
                <div className="min-w-0 text-sm">
                  <div className="font-medium">
                    {c.name} <span className="font-normal text-ink-2">· {c.dataset}</span>
                  </div>
                  <p className="mt-0.5 break-words text-ink-2">{c.detail}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </Section>

      <Section title="Sources" intro="The exact files the data was built from, with their SHA-256 fingerprints.">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-ink-2">
                <th scope="col" className="py-2 pr-4 font-medium">Source</th>
                <th scope="col" className="py-2 pr-4 font-medium">Fetched</th>
                <th scope="col" className="py-2 font-medium">SHA-256</th>
              </tr>
            </thead>
            <tbody>
              {q.sources.map((s) => (
                <tr key={s.key} className="border-b border-line last:border-0">
                  <td className="py-2 pr-4">
                    <a href={s.url} className="underline" target="_blank" rel="noopener noreferrer">
                      {s.title}
                    </a>
                  </td>
                  <td className="py-2 pr-4 whitespace-nowrap text-ink-2">{longDate(s.fetched_at.slice(0, 10))}</td>
                  <td className="py-2 font-mono text-xs text-ink-2" title={s.sha256}>
                    {s.sha256.slice(0, 16)}…
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>

      <Section title="Use the data">
        <ul className="space-y-2 text-sm text-ink-2">
          <li>
            <strong className="text-ink">CSV files:</strong>{" "}
            <a className="underline" href="https://github.com/kasondebbuku-spec/zambia-open-data/tree/main/data/snapshot">
              data/snapshot on GitHub
            </a>
            , with a{" "}
            <a className="underline" href="https://github.com/kasondebbuku-spec/zambia-open-data/blob/main/data/README.md">
              data dictionary
            </a>
            .
          </li>
          <li>
            <strong className="text-ink">API:</strong> free, read-only, no key. The interactive documentation is
            at <code className="rounded bg-plane px-1">/docs</code> on the API server.
          </li>
          <li>
            <strong className="text-ink">Limits:</strong> only the 2024 and 2025 books have readable text; earlier
            financial statements are scanned images. CDF stages and sectors are read from the stories&apos;
            wording, so check the linked post.
          </li>
        </ul>
      </Section>
    </div>
  );
}
