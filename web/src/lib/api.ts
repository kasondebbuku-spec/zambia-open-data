// Typed client for the Zambia Open Data API. Runs on the server only: pages are server
// components, so the browser never talks to the API directly.
import "server-only";
import { storiesQuery, type StoryFilters } from "./query";

export { storiesQuery, type StoryFilters };

export type BudgetSummary = { year: number; total_zmw: number; change_pct: number | null; source_url: string };
export type Share = { code: string; name: string; amount_zmw: number; share_pct: number };
export type BudgetDetail = BudgetSummary & {
  revenue_by_group: Share[];
  spending_by_economic: Share[];
  spending_by_programme: Share[];
};
export type RevenueItem = {
  group_code: string;
  group_name: string;
  item_code: string | null;
  item_name: string;
  fiscal_year: number;
  stage: string;
  amount_zmw: number;
};
export type Change = {
  code: number;
  name: string;
  previous_zmw: number | null;
  current_zmw: number | null;
  change_zmw: number | null;
  change_pct: number | null;
};
export type Changes = { year: number; previous_year: number; basis: Basis; lines: Change[] };
export type Basis = "economic" | "programme";
export type Story = {
  post_id: number;
  published_on: string;
  title: string;
  url: string;
  summary: string;
  constituencies: string[];
  sectors: string[];
  status: string | null;
  largest_amount_zmw: number | null;
  completion_pct: number | null;
};
export type Page<T> = { total: number; limit: number; offset: number; items: T[] };
export type ConstituencySummary = {
  name: string;
  stories: number;
  latest_story_on: string | null;
  sectors: Record<string, number>;
};
export type Check = { dataset: string; name: string; status: "pass" | "warn" | "fail"; detail: string };
export type Source = { key: string; title: string; url: string; sha256: string; bytes: number; fetched_at: string };
export type Quality = {
  loaded_at: string | null;
  snapshot_sha256: string | null;
  summary: Record<string, number>;
  checks: Check[];
  sources: Source[];
};

export type Download = {
  file: string;
  description: string;
  rows: number;
  bytes: number;
  sha256: string;
  url: string;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export function apiUrl(): string {
  return (process.env.API_URL ?? "http://localhost:4100").replace(/\/$/, "");
}

async function get<T>(path: string): Promise<T> {
  let res: Response;
  try {
    // The data changes when the snapshot is reloaded (monthly at most), so cache for 10 minutes.
    res = await fetch(`${apiUrl()}${path}`, { next: { revalidate: 600 } });
  } catch {
    throw new ApiError(503, "The data service isn't reachable right now. Please try again in a minute.");
  }
  if (!res.ok) {
    const body = (await res.json().catch(() => null)) as { detail?: unknown } | null;
    throw new ApiError(res.status, typeof body?.detail === "string" ? body.detail : `Request failed (${res.status})`);
  }
  return (await res.json()) as T;
}

export const api = {
  budgets: () => get<BudgetSummary[]>("/v1/budgets"),
  budget: (year: number) => get<BudgetDetail>(`/v1/budgets/${year}`),
  revenue: (year: number) => get<RevenueItem[]>(`/v1/budgets/${year}/revenue`),
  changes: (year: number, basis: Basis) => get<Changes>(`/v1/budgets/${year}/changes?basis=${basis}`),
  stories: (f: StoryFilters) => get<Page<Story>>(`/v1/cdf/stories?${storiesQuery(f)}`),
  constituencies: () => get<ConstituencySummary[]>("/v1/cdf/constituencies"),
  quality: () => get<Quality>("/v1/quality"),
  downloads: () => get<Download[]>("/v1/downloads"),
};
