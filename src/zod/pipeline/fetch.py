"""Download the raw sources from lcc.gov.zm into ``data/raw`` (not committed).

Only this step talks to the council's website. Everything after it works from the
downloaded files, and the cleaned result is committed under ``data/snapshot`` so the
API and tests never depend on the site being up.

The site's TLS certificate has been expired since at least September 2026, so
certificate checks are turned off for this one host. Nothing is sent to it; we only
read public pages, and every file is fingerprinted with SHA-256 in the manifest.
"""

from __future__ import annotations

import hashlib
import json
import re
import warnings
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx

BASE = "https://www.lcc.gov.zm"
USER_AGENT = "zambia-open-data/0.1 (public-interest data project)"

# The approved budget books, by year, as Download Manager packages on the site.
BUDGET_BOOKS = {
    2024: "lusaka-city-council-approved-budget-for-2024",
    2025: "lusaka-city-council-approved-2025-budget-yellow-book",
}


@dataclass
class Source:
    key: str
    title: str
    url: str
    file: str
    sha256: str
    bytes: int
    fetched_at: str


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _client() -> httpx.Client:
    import httpx

    warnings.filterwarnings("ignore", message="Unverified HTTPS request")
    return httpx.Client(
        base_url=BASE, verify=False, timeout=60, follow_redirects=True, headers={"User-Agent": USER_AGENT}
    )


def fetch_posts(raw: Path) -> Source:
    out = raw / "posts.json"
    posts: list[dict[str, object]] = []
    with _client() as http:
        page = 1
        while True:
            r = http.get("/wp-json/wp/v2/posts", params={"per_page": 100, "page": page})
            if r.status_code == 400:  # WordPress answers 400 past the last page
                break
            r.raise_for_status()
            batch = r.json()
            posts += batch
            if page >= int(r.headers.get("X-WP-TotalPages", "1")):
                break
            page += 1
    out.write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding="utf-8")
    return _source("news", "Lusaka City Council news posts", f"{BASE}/wp-json/wp/v2/posts", out)


def fetch_budget_book(raw: Path, year: int) -> Source:
    slug = BUDGET_BOOKS[year]
    out = raw / f"budget-{year}.pdf"
    with _client() as http:
        page = http.get(f"/download/{slug}/")
        page.raise_for_status()
        m = re.search(r'data-downloadurl="([^"]+)"', page.text)
        if not m:
            raise RuntimeError(f"No download link on {BASE}/download/{slug}/")
        pdf = http.get(m[1].replace("&amp;", "&"))
        pdf.raise_for_status()
        if not pdf.content.startswith(b"%PDF"):
            raise RuntimeError(f"{slug} did not return a PDF")
        out.write_bytes(pdf.content)
    return _source(f"budget-{year}", f"Approved budget {year}", f"{BASE}/download/{slug}/", out)


def _source(key: str, title: str, url: str, path: Path) -> Source:
    return Source(
        key,
        title,
        url,
        path.name,
        sha256(path),
        path.stat().st_size,
        datetime.now(UTC).isoformat(timespec="seconds"),
    )


def fetch_all(raw: Path) -> list[Source]:
    raw.mkdir(parents=True, exist_ok=True)
    sources = [fetch_budget_book(raw, y) for y in BUDGET_BOOKS] + [fetch_posts(raw)]
    (raw / "manifest.json").write_text(json.dumps([asdict(s) for s in sources], indent=1), encoding="utf-8")
    return sources
