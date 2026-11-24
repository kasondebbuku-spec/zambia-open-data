import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { BarList } from "@/components/charts";
import { Section, StoryCard } from "@/components/ui";
import { api, storiesQuery, type StoryFilters } from "@/lib/api";
import { SECTORS, STATUSES, sectorLabel, statusLabel } from "@/lib/format";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "CDF projects" };

const PAGE = 12;

type Props = { searchParams: Promise<Record<string, string | undefined>> };

export default async function Cdf({ searchParams }: Props) {
  const sp = await searchParams;
  const page = Math.max(1, Number.parseInt(sp.page ?? "1", 10) || 1);
  const constituencies = await api.constituencies();
  // Ignore filter values that aren't real options (an edited or old link) instead of erroring.
  const pick = (v: string | undefined, options: string[]) =>
    options.find((o) => o.toLowerCase() === v?.toLowerCase());
  const filters: StoryFilters = {
    constituency: pick(sp.constituency, constituencies.map((c) => c.name)),
    sector: pick(sp.sector, SECTORS),
    status: pick(sp.status, STATUSES),
    q: sp.q?.trim().slice(0, 100) || undefined,
  };
  const result = await api.stories({ ...filters, limit: PAGE, offset: (page - 1) * PAGE });
  const pages = Math.max(1, Math.ceil(result.total / PAGE));
  const filtered = Object.values(filters).some(Boolean);
  const pageHref = (p: number) => {
    const q = new URLSearchParams(storiesQuery({ ...filters, limit: PAGE }));
    q.delete("limit");
    if (p > 1) q.set("page", String(p));
    const s = q.toString();
    return s ? `/cdf?${s}` : "/cdf";
  };
  if (page > pages) redirect(pageHref(pages)); // an old link past the last page

  return (
    <div className="space-y-6">
      <div className="max-w-3xl">
        <h1 className="text-3xl font-semibold tracking-tight">Constituency Development Fund projects</h1>
        <p className="mt-2 text-ink-2">
          The CDF gives each of Lusaka&apos;s seven constituencies money for local projects: classrooms, clinics,
          markets, roads, and loans and grants for youth and women. These are the council&apos;s own news
          stories about those projects, each linked to the original post.
        </p>
      </div>

      <Section
        title="Stories by constituency"
        intro="How often each constituency appears in the council's CDF news. A story can mention more than one."
      >
        <BarList
          unit="stories"
          caption="CDF stories per constituency"
          bars={constituencies.map((c) => ({
            key: c.name,
            label: c.name,
            value: c.stories,
            note: Object.keys(c.sectors).slice(0, 3).map(sectorLabel).join(", ") || undefined,
          }))}
        />
      </Section>

      <form method="get" action="/cdf" className="card flex flex-wrap items-end gap-3 p-4" role="search" aria-label="Filter stories">
        <Field label="Constituency">
          <select name="constituency" defaultValue={filters.constituency ?? ""} className={inputClass}>
            <option value="">All</option>
            {constituencies.map((c) => (
              <option key={c.name}>{c.name}</option>
            ))}
          </select>
        </Field>
        <Field label="Sector">
          <select name="sector" defaultValue={filters.sector ?? ""} className={inputClass}>
            <option value="">All</option>
            {SECTORS.map((s) => (
              <option key={s} value={s}>
                {sectorLabel(s)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Stage">
          <select name="status" defaultValue={filters.status ?? ""} className={inputClass}>
            <option value="">All</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Words">
          <input
            type="search"
            name="q"
            defaultValue={filters.q ?? ""}
            placeholder="clinic, market, Ward 30…"
            maxLength={100}
            className={`${inputClass} w-56`}
          />
        </Field>
        <button type="submit" className="rounded-md bg-brand px-4 py-2 text-sm font-medium text-white dark:text-black">
          Show stories
        </button>
        {filtered && (
          <Link href="/cdf" className="py-2 text-sm text-ink-2 underline">
            Clear
          </Link>
        )}
      </form>

      <p className="text-sm text-ink-2" aria-live="polite">
        {result.total === 0
          ? "No stories match. Try fewer filters."
          : `${result.total} ${result.total === 1 ? "story" : "stories"}${filtered ? " match" : ""}, newest first.`}
      </p>

      <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
        {result.items.map((s) => (
          <StoryCard key={s.post_id} story={s} />
        ))}
      </div>

      {pages > 1 && (
        <nav aria-label="Pages" className="flex items-center justify-center gap-3 text-sm">
          {page > 1 ? (
            <Link href={pageHref(page - 1)} className="rounded-md border border-line bg-surface px-3 py-1.5">
              Newer
            </Link>
          ) : (
            <span className="px-3 py-1.5 text-muted">Newer</span>
          )}
          <span className="tabular-nums text-ink-2">
            Page {Math.min(page, pages)} of {pages}
          </span>
          {page < pages ? (
            <Link href={pageHref(page + 1)} className="rounded-md border border-line bg-surface px-3 py-1.5">
              Older
            </Link>
          ) : (
            <span className="px-3 py-1.5 text-muted">Older</span>
          )}
        </nav>
      )}

      <p className="text-xs text-muted">
        Stage and sector are read from each story&apos;s wording, and the amount is the largest one the story
        mentions, which may not be the project&apos;s cost. Check the linked post for details.
      </p>
    </div>
  );
}

const inputClass = "rounded-md border border-line bg-surface px-3 py-2 text-sm";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="text-ink-2">{label}</span>
      {children}
    </label>
  );
}
