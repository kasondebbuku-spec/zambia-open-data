// Builds the API query string for CDF stories. Kept apart from api.ts so it can be unit tested.

export function storiesQuery(f: StoryFilters): string {
  const q = new URLSearchParams();
  if (f.constituency) q.set("constituency", f.constituency);
  if (f.sector) q.set("sector", f.sector);
  if (f.status) q.set("status", f.status);
  if (f.q) q.set("q", f.q);
  q.set("limit", String(f.limit ?? 12));
  if (f.offset) q.set("offset", String(f.offset));
  return q.toString();
}

export type StoryFilters = {
  constituency?: string;
  sector?: string;
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
};
