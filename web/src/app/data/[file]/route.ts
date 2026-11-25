// /data/revenue.csv etc.: the API's CSV downloads, served from the site's own address so
// visitors never need to know where the API lives.
import { apiUrl } from "@/lib/api";

export async function GET(_req: Request, { params }: { params: Promise<{ file: string }> }) {
  const { file } = await params;
  if (!/^[a-z_]+\.csv$/.test(file)) return new Response("Not found", { status: 404 });
  let res: Response;
  try {
    res = await fetch(`${apiUrl()}/v1/downloads/${file}`, { next: { revalidate: 600 } });
  } catch {
    return new Response("The data service isn't reachable right now. Please try again in a minute.", {
      status: 503,
    });
  }
  if (!res.ok) return new Response("Not found", { status: res.status === 404 ? 404 : 502 });
  return new Response(res.body, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": res.headers.get("content-disposition") ?? `attachment; filename="${file}"`,
      "Cache-Control": "public, max-age=600",
    },
  });
}
