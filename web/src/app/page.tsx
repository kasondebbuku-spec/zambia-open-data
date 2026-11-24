import Link from "next/link";
import { BarList, ChangeBars } from "@/components/charts";
import { Section, Stat, StoryCard } from "@/components/ui";
import { api } from "@/lib/api";
import { kwachaShort, signedPct, tidyName } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function Overview() {
  const budgets = await api.budgets();
  const latest = budgets.at(-1);
  if (!latest) return <p>No budget data has been loaded yet.</p>;
  const [detail, changes, stories, quality] = await Promise.all([
    api.budget(latest.year),
    api.changes(latest.year, "programme"),
    api.stories({ limit: 3 }),
    api.quality(),
  ]);
  const cdf = detail.spending_by_programme.find((p) => /constituency development/i.test(p.name));
  const prev = budgets.at(-2);

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <p className="text-sm font-medium text-brand">Lusaka City Council · {latest.year} approved budget</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight sm:text-4xl">
          {kwachaShort(latest.total_zmw)} to run Lusaka in {latest.year}
        </h1>
        <p className="mt-3 text-ink-2">
          Where the council&apos;s money comes from, where it goes, and what the Constituency Development Fund
          is building, all from the council&apos;s own published budget books and news posts.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          label={`${latest.year} budget`}
          value={kwachaShort(latest.total_zmw)}
          delta={latest.change_pct !== null ? signedPct(latest.change_pct) : undefined}
          hint={prev ? `on ${prev.year} (${kwachaShort(prev.total_zmw)})` : undefined}
        />
        {cdf && (
          <Stat
            label="Constituency Development Fund"
            value={kwachaShort(cdf.amount_zmw)}
            hint={`${cdf.share_pct}% of spending, across 7 constituencies`}
          />
        )}
        <Stat label="CDF stories tracked" value={String(stories.total)} hint="from the council's news posts" />
        <Stat
          label="Data quality checks"
          value={`${quality.summary.pass ?? 0} pass`}
          hint={`${quality.summary.warn ?? 0} warnings, ${quality.summary.fail ?? 0} failures`}
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Section
          title="Where the money comes from"
          action={<Link href={`/budgets/${latest.year}#revenue`} className="text-sm text-brand hover:underline">All revenue lines</Link>}
        >
          <BarList
            caption={`Revenue by source, ${latest.year}`}
            total={detail.total_zmw}
            bars={detail.revenue_by_group.map((g) => ({ key: g.code, label: tidyName(g.name), value: g.amount_zmw }))}
          />
        </Section>
        <Section
          title="Where it goes"
          action={<Link href={`/budgets/${latest.year}`} className="text-sm text-brand hover:underline">By programme and type</Link>}
        >
          <BarList
            caption={`Spending by programme, ${latest.year}`}
            total={detail.total_zmw}
            bars={detail.spending_by_programme.slice(0, 8).map((p) => ({
              key: p.code,
              label: tidyName(p.name),
              value: p.amount_zmw,
            }))}
          />
        </Section>
      </div>

      <Section
        title={`What changed from ${changes.previous_year}`}
        intro={`Each programme's ${latest.year} budget against its ${changes.previous_year} figure, as reprinted in the ${latest.year} book. The six biggest moves are shown.`}
        action={<Link href={`/budgets/${latest.year}#changes`} className="text-sm text-brand hover:underline">Every programme</Link>}
      >
        <ChangeBars
          caption={`Biggest spending changes, ${changes.previous_year} to ${latest.year}`}
          before={String(changes.previous_year)}
          after={String(latest.year)}
          rows={changes.lines.slice(0, 6).map((l) => ({
            key: String(l.code),
            label: tidyName(l.name),
            change: l.change_zmw ?? 0,
            pct: l.change_pct,
            before: l.previous_zmw,
            after: l.current_zmw,
          }))}
        />
      </Section>

      <section>
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Latest CDF projects</h2>
          <Link href="/cdf" className="text-sm text-brand hover:underline">
            All {stories.total} stories
          </Link>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {stories.items.map((s) => (
            <StoryCard key={s.post_id} story={s} />
          ))}
        </div>
      </section>
    </div>
  );
}
