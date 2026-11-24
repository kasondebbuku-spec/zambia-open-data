"""Turn the council's news posts into a table of Constituency Development Fund (CDF) stories.

The posts are prose, so the honest grain is one row per story: when it was published,
which of Lusaka's seven constituencies it's about, what kind of project (a clinic, a
school, a market, empowerment loans ...), how far along it is, and the largest kwacha
amount it mentions. Every row links back to the original post so a reader can check.
"""

from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from typing import Any

CDF_CATEGORY_ID = 56

CONSTITUENCIES = ("Chawama", "Kabwata", "Kanyama", "Lusaka Central", "Mandevu", "Matero", "Munali")

SECTORS: dict[str, tuple[str, ...]] = {
    "education": (
        "school",
        "classroom",
        "desk",
        "desks",
        "bursary",
        "bursaries",
        "skills",
        "laboratory",
        "early childhood",
        "education",
    ),
    "health": (
        "clinic",
        "health post",
        "health centre",
        "health center",
        "hospital",
        "maternity",
        "mortuary",
        "ambulance",
        "mothers shelter",
        "mother's shelter",
    ),
    "water_sanitation": ("water", "borehole", "boreholes", "reticulation", "sanitation", "ablution", "sewer"),
    "roads_drainage": ("road", "roads", "bridge", "culvert", "drainage", "paving", "street lights"),
    "markets": ("market", "markets", "market shelter", "stalls", "traders"),
    "empowerment": (
        "loan",
        "loans",
        "grant",
        "grants",
        "empowerment",
        "cooperative",
        "cooperatives",
        "youth",
        "youths",
        "women",
        "start-up",
        "startup",
    ),
    "community_safety": ("police post", "civic centre", "community hall", "guard house", "recreation"),
}
_SECTOR_RE = {
    s: re.compile(r"\b(?:" + "|".join(map(re.escape, kws)) + r")\b", re.I) for s, kws in SECTORS.items()
}

# The stage a story reports, read from its words. The headline is checked first because the
# body often recalls earlier stages ("the school, once under construction, was handed over").
_STATUS_PATTERNS = {
    "planned": r"\b(?:soon to|set to|to be (?:built|constructed)|will be (?:built|constructed)|earmarked|poised for)\b",
    "handed_over": r"\bhand(?:ed|ing|s)?\s+over\b|officially handed",
    "commissioned": r"\bcommission(?:ed|ing|s)\b",
    "under_construction": r"under construction|underway|ongoing|in progress|progress update|"
    r"almost complete|nearing completion|takes shape|gain(?:s|ing)? momentum|\bconstructing\b|\bcommenced\b",
    "completed": r"\bcompleted\b|\bnow complete\b|successfully complet",
}
_STATUS_RE = {k: re.compile(v, re.I) for k, v in _STATUS_PATTERNS.items()}
_TITLE_ORDER = ("planned", "handed_over", "commissioned", "under_construction", "completed")
_BODY_ORDER = ("handed_over", "commissioned", "under_construction", "completed", "planned")


def status(title: str, body: str) -> str | None:
    for text, order in ((title, _TITLE_ORDER), (body, _BODY_ORDER)):
        for label in order:
            if _STATUS_RE[label].search(text):
                return label
    return None


_MONEY = re.compile(r"\b(?:K|ZMW)\s?(\d[\d,]*(?:\.\d+)?)\s?(million|m|billion|bn)?\b", re.I)
_PERCENT = re.compile(r"\b(\d{1,3})\s?(?:%|percent\b)", re.I)
_TAGS = re.compile(r"<(script|style)\b.*?</\1>|<[^>]+>", re.S | re.I)


def plain_text(rendered: str) -> str:
    # NFKC turns the "fancy" bold letters some headlines use (𝑾𝒐𝒎𝒆𝒏) into plain ones.
    text = unicodedata.normalize("NFKC", html.unescape(_TAGS.sub(" ", rendered or "")))
    return re.sub(r"\s+", " ", text).strip()


def kwacha(number: str, unit: str | None) -> int:
    value = float(number.replace(",", ""))
    scale = {"million": 1e6, "m": 1e6, "billion": 1e9, "bn": 1e9}.get((unit or "").lower(), 1)
    return round(value * scale)


@dataclass(frozen=True)
class Story:
    post_id: int
    published_on: date
    title: str
    url: str
    summary: str
    constituencies: tuple[str, ...]
    sectors: tuple[str, ...]
    status: str | None
    largest_amount_zmw: int | None
    completion_pct: int | None


def is_cdf(post: dict[str, Any], text: str) -> bool:
    return CDF_CATEGORY_ID in post.get("categories", []) or bool(
        re.search(r"\bCDF\b|constituency development fund", text, re.I)
    )


def story(post: dict[str, Any]) -> Story | None:
    title = plain_text(post["title"]["rendered"])
    body = plain_text(post["content"]["rendered"])
    text = f"{title}. {body}"
    if not is_cdf(post, text):
        return None
    amounts = [kwacha(n, u) for n, u in _MONEY.findall(text)]
    percents = [int(p) for p in _PERCENT.findall(text) if 0 < int(p) <= 100]
    summary = body if len(body) <= 280 else body[:280].rsplit(" ", 1)[0] + "…"
    return Story(
        post_id=int(post["id"]),
        published_on=date.fromisoformat(post["date"][:10]),
        title=title,
        url=post["link"],
        summary=summary,
        constituencies=tuple(c for c in CONSTITUENCIES if re.search(rf"\b{c}\b", text, re.I)),
        sectors=tuple(s for s, rx in _SECTOR_RE.items() if rx.search(text)),
        status=status(title, body),
        largest_amount_zmw=max(amounts) if amounts else None,
        # Only a percentage near the words "complete"/"completion" is a progress figure.
        completion_pct=max(percents) if percents and re.search(r"complet", text, re.I) else None,
    )


def stories(posts: list[dict[str, Any]]) -> tuple[list[Story], list[int]]:
    """CDF stories, newest first, plus the ids of posts dropped as duplicates.

    The council sometimes publishes the same article twice under different posts;
    we keep the newest post and drop the copies.
    """
    by_text: dict[str, dict[str, Any]] = {}
    dropped: list[int] = []
    for post in sorted(posts, key=lambda p: int(p["id"]), reverse=True):
        key = hashlib.sha1(plain_text(post["content"]["rendered"]).encode()).hexdigest()
        if key in by_text:
            dropped.append(int(post["id"]))
            continue
        by_text[key] = post
    found = [s for p in by_text.values() if (s := story(p)) is not None]
    found.sort(key=lambda s: (s.published_on, s.post_id), reverse=True)
    return found, sorted(dropped)
