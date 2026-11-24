import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { BarList, ChangeBars } from "@/components/charts";
import { Section, Stat } from "@/components/ui";
import { api, ApiError, type Basis, type RevenueItem } from "@/lib/api";
import { kwacha, kwachaShort, signedPct, tidyName } from "@/lib/format";

export const dynamic = "force-dynamic";

type Props = { params: Promise<{ year: string }>; searchParams: Promise<{ by?: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { year } = await params;
  return { title: `${year} budget` };
}

const BASES: { value: Basis; label: string; blurb: string }[] = [
  { value: "programme", label: "By programme", blurb: "what the money is for" },
  { value: "economic", label: "By type", blurb: "salaries, goods and services, transfers …" },
];

export default async function BudgetYear({ params, searchParams }: Props) {
  const { year: y } = await params;
  const { by } = await searchParams;
  const year = Number(y);
  const basis: Basis = by === "economic" ? "economic" : "programme";
  if (!Number.isInteger(year)) notFound();

  let detail, changes, revenue, books;
  try {
    [detail, changes, revenue, books] = await Promise.all([
      api.budget(year),
      api.changes(year, basis),
      api.revenue(year),
      api.budgets(),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    throw e;
  }
  const spending = basis === "programme" ? detail.spending_by_programme : detail.spending_by_economic;
  const hasPrior = changes.lines.some((l) => l.previous_zmw !== null);
  const groups = groupRevenue(revenue);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{year} approved budget</h1>
          <p className="mt-1 text-ink-2">
            From the council&apos;s{" "}
            <a href={detail.source_url} className="underline" target="_blank" rel="noopener noreferrer">
              {year} budget book
            </a>
            .
          </p>
        </div>
        <nav aria-label="Budget year" className="flex gap-1 rounded-lg border border-line bg-surface p-1 text-sm">
          {books.map((b) => (
            <Link
              key={b.year}
              href={`/budgets/${b.year}${basis === "economic" ? "?by=economic" : ""}`}
              aria-current={b.year === year ? "page" : undefined}
              className={`rounded-md px-3 py-1.5 tabular-nums ${b.year === year ? "bg-brand-soft font-medium text-brand" : "text-ink-2 hover:text-ink"}`}
            >
              {b.year}
            </Link>
          ))}
        </nav>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat
          label="Total budget"
          value={kwachaShort(detail.total_zmw)}
          delta={detail.change_pct !== null ? signedPct(detail.change_pct) : undefined}
          hint={detail.change_pct !== null ? `on ${year - 1}` : "earliest book we have"}
        />
        <Stat label="Biggest source" value={tidyName(detail.revenue_by_group[0]?.name ?? "—")} hint={`${detail.revenue_by_group[0]?.share_pct ?? 0}% of revenue`} />
        <Stat label="Biggest programme" value={tidyName(detail.spending_by_programme[0]?.name ?? "—")} hint={`${detail.spending_by_programme[0]?.share_pct ?? 0}% of spending`} />
      </div>

      <Section
        title="Spending"
        intro="Planned revenue and planned spending are equal: a council budget must balance."
        action={
          <div className="flex gap-1 rounded-lg border border-line p-1 text-sm" role="group" aria-label="Group spending">
            {BASES.map((b) => (
              <Link
                key={b.value}
                href={`/budgets/${year}${b.value === "economic" ? "?by=economic" : ""}`}
                aria-current={b.value === basis ? "true" : undefined}
                title={b.blurb}
                className={`rounded-md px-3 py-1 ${b.value === basis ? "bg-brand-soft font-medium text-brand" : "text-ink-2 hover:text-ink"}`}
              >
                {b.label}
              </Link>
            ))}
          </div>
        }
      >
        <BarList
          caption={`Spending ${basis === "programme" ? "by programme" : "by type"}, ${year}`}
          total={detail.total_zmw}
          bars={spending.map((s) => ({ key: s.code, label: tidyName(s.name), value: s.amount_zmw }))}
        />
      </Section>

      <div id="changes">
        <Section
          title={`Changes from ${year - 1}`}
          intro={
            hasPrior
              ? `Each line against its ${year - 1} figure as reprinted in the ${year} book, so both columns use the same codes. Biggest moves first.`
              : `The ${year} book doesn't reprint ${year - 1} figures, so there is nothing to compare against.`
          }
        >
          {hasPrior && (
            <ChangeBars
              caption={`Spending changes, ${year - 1} to ${year}`}
              before={String(year - 1)}
              after={String(year)}
              rows={changes.lines.map((l) => ({
                key: String(l.code),
                label: tidyName(l.name),
                change: l.change_zmw ?? 0,
                pct: l.change_pct,
                before: l.previous_zmw,
                after: l.current_zmw,
              }))}
            />
          )}
        </Section>
      </div>

      <div id="revenue">
        <Section title="Revenue" intro="Every revenue line in the book, grouped as the council groups them.">
          <BarList
            caption={`Revenue by source, ${year}`}
            total={detail.total_zmw}
            bars={detail.revenue_by_group.map((g) => ({ key: g.code, label: tidyName(g.name), value: g.amount_zmw }))}
          />
          <div className="mt-6 space-y-2">
            {groups.map((g) => (
              <details key={g.code} className="rounded-lg border border-line">
                <summary className="flex cursor-pointer justify-between gap-4 px-4 py-2.5 text-sm">
                  <span className="font-medium">{tidyName(g.name)}</span>
                  <span className="text-ink-2 tabular-nums">
                    {g.items.length} lines · {kwacha(g.total)}
                  </span>
                </summary>
                <table className="w-full border-t border-line text-sm tabular-nums">
                  <caption className="sr-only">{g.name} revenue lines</caption>
                  <thead className="sr-only">
                    <tr>
                      <th scope="col">Line</th>
                      <th scope="col">Amount</th>
                    </tr>
                  </thead>
                  <tbody>
                    {g.items.map((i, n) => (
                      <tr key={n} className="border-b border-line last:border-0">
                        <td className="px-4 py-1.5 text-ink-2">{i.item_name}</td>
                        <td className="px-4 py-1.5 text-right">{kwacha(i.amount_zmw)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </details>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}

function groupRevenue(items: RevenueItem[]) {
  const map = new Map<string, { code: string; name: string; total: number; items: RevenueItem[] }>();
  for (const i of items) {
    const g = map.get(i.group_code) ?? { code: i.group_code, name: i.group_name, total: 0, items: [] };
    g.total += i.amount_zmw;
    g.items.push(i);
    map.set(i.group_code, g);
  }
  return [...map.values()].sort((a, b) => b.total - a.total);
}
