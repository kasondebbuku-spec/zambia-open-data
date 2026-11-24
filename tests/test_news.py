from __future__ import annotations

from datetime import date
from typing import Any

from zod.pipeline.news import kwacha, plain_text, status, stories, story


def post(
    pid: int, title: str, body: str, categories: list[int] | None = None, day: str = "2025-11-25"
) -> dict[str, Any]:
    return {
        "id": pid,
        "date": f"{day}T10:00:00",
        "link": f"https://www.lcc.gov.zm/p{pid}/",
        "title": {"rendered": title},
        "content": {"rendered": body},
        "categories": categories or [],
    }


MARKET = post(
    7700,
    "MINISTER HANDS OVER NEWLY CONSTRUCTED KATAMBALALA MARKET IN MATERO",
    "<div><style>.x{}</style><p>A market shelter built with the Constituency Development Fund (CDF) in "
    "Lima Ward 30 of <b>Matero</b> Constituency was handed over. It cost K1.6 million and serves 300 traders.</p></div>",
)


def test_plain_text_strips_markup_and_fancy_letters() -> None:
    assert plain_text("<p>Hello&nbsp;<b>Lusaka</b></p><script>x()</script>") == "Hello Lusaka"
    assert plain_text("𝑾𝒐𝒎𝒆𝒏’𝒔 𝑪𝒉𝒊𝒄𝒌𝒆𝒏") == "Women’s Chicken"


def test_kwacha_amounts() -> None:
    assert kwacha("1.6", "million") == 1_600_000
    assert kwacha("818,546", None) == 818_546
    assert kwacha("1.08", "bn") == 1_080_000_000


def test_a_cdf_story() -> None:
    s = story(MARKET)
    assert s is not None
    assert s.published_on == date(2025, 11, 25)
    assert s.constituencies == ("Matero",)
    assert "markets" in s.sectors
    assert s.status == "handed_over"
    assert s.largest_amount_zmw == 1_600_000
    assert s.completion_pct is None


def test_non_cdf_posts_are_skipped_unless_in_the_cdf_category() -> None:
    news = post(1, "Council upskills IT team", "<p>Training on cybersecurity.</p>")
    assert story(news) is None
    assert story({**news, "categories": [56]}) is not None


def test_headline_wins_over_body_for_status() -> None:
    assert (
        status("CLASSROOM BLOCK ALMOST COMPLETE", "The works were completed in phases")
        == "under_construction"
    )
    assert status("LCC SOON TO COMMISSION 14 HEALTH FACILITIES", "were commissioned") == "planned"
    assert status("A day in Munali", "The clinic was officially handed over") == "handed_over"
    assert status("Bursary stories", "Pupils shared their stories") is None


def test_completion_only_counts_near_progress_words() -> None:
    s = story(post(2, "CDF school block", "<p>The CDF block is 85 percent complete.</p>"))
    assert s is not None and s.completion_pct == 85
    s = story(post(3, "CDF loans", "<p>CDF loans at 10% interest.</p>"))
    assert s is not None and s.completion_pct is None


def test_duplicate_articles_keep_the_newest_post() -> None:
    copy = {**MARKET, "id": 5953}
    found, dropped = stories(
        [MARKET, copy, post(10, "CDF desks", "<p>CDF desks delivered.</p>", day="2025-01-02")]
    )
    assert [s.post_id for s in found] == [7700, 10]
    assert dropped == [5953]
