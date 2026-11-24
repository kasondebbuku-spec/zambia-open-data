import Link from "next/link";
import type { Story } from "@/lib/api";
import { kwachaShort, longDate, sectorLabel, sentenceCase, statusLabel } from "@/lib/format";

export function Section({ title, intro, children, action }: {
  title: string;
  intro?: React.ReactNode;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="card p-5 sm:p-6">
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        {action}
      </div>
      {intro && <p className="-mt-2 mb-4 max-w-prose text-sm text-ink-2">{intro}</p>}
      {children}
    </section>
  );
}

/** label · value · optional delta. The delta is direction-only (up/down), not good/bad. */
export function Stat({ label, value, delta, hint }: { label: string; value: string; delta?: string; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="text-sm text-ink-2">{label}</div>
      <div className="mt-1 text-2xl font-semibold tracking-tight tabular-nums">{value}</div>
      {(delta || hint) && (
        <div className="mt-1 text-sm text-ink-2">
          {delta && <span className="font-medium text-ink tabular-nums">{delta}</span>} {hint}
        </div>
      )}
    </div>
  );
}

export function StoryCard({ story }: { story: Story }) {
  return (
    <article className="card flex flex-col p-4">
      <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-ink-2">
        <time dateTime={story.published_on}>{longDate(story.published_on)}</time>
        {story.constituencies.length > 0 && <span aria-hidden>·</span>}
        {story.constituencies.length > 0 && <span>{story.constituencies.join(", ")}</span>}
      </div>
      <h3 className="mb-2 font-semibold leading-snug">
        <a href={story.url} className="hover:underline" target="_blank" rel="noopener noreferrer">
          {sentenceCase(story.title)}
          <span className="sr-only"> (opens the council&apos;s post)</span>
        </a>
      </h3>
      <p className="mb-3 text-sm text-ink-2">{story.summary}</p>
      <div className="mt-auto flex flex-wrap gap-1.5 text-xs">
        {story.status && (
          <span className="rounded-full border border-line px-2 py-0.5 font-medium">{statusLabel(story.status)}</span>
        )}
        {story.sectors.map((s) => (
          <Link key={s} href={`/cdf?sector=${s}`} className="rounded-full bg-plane px-2 py-0.5 text-ink-2 hover:text-ink">
            {sectorLabel(s)}
          </Link>
        ))}
        {story.largest_amount_zmw !== null && (
          <span className="rounded-full bg-plane px-2 py-0.5 text-ink-2" title="The largest amount the story mentions">
            mentions {kwachaShort(story.largest_amount_zmw)}
          </span>
        )}
      </div>
    </article>
  );
}
