"""The API against a real PostgreSQL loaded with the committed snapshot."""

from __future__ import annotations

from typing import Any

import pytest
from conftest import SNAPSHOT, needs_db
from sqlalchemy import func, select

pytestmark = needs_db


def get(client: Any, url: str) -> Any:
    r = client.get(url)
    assert r.status_code == 200, r.text
    return r.json()


def test_health(client: Any) -> None:
    assert get(client, "/health") == {"status": "ok"}


def test_budget_list_with_growth(client: Any) -> None:
    books = get(client, "/v1/budgets")
    assert [(b["year"], b["total_zmw"]) for b in books] == [(2024, 732_090_165), (2025, 1_079_607_654)]
    assert books[0]["change_pct"] is None
    assert books[1]["change_pct"] == 47.5  # the 2025 book itself says "a 47.5% increase"


def test_budget_detail_shares(client: Any) -> None:
    b = get(client, "/v1/budgets/2025")
    top = b["revenue_by_group"][0]
    assert top["name"] == "National Support (Grants)" and top["amount_zmw"] == 354_738_832
    # Shares are of the book's printed total, so they add up to about 100 (rounding aside).
    for key in ("revenue_by_group", "spending_by_economic", "spending_by_programme"):
        assert 99.5 <= sum(x["share_pct"] for x in b[key]) <= 100.5
    assert sum(x["amount_zmw"] for x in b["spending_by_economic"]) == b["total_zmw"]


def test_unknown_year_says_which_years_exist(client: Any) -> None:
    r = client.get("/v1/budgets/2019")
    assert r.status_code == 404
    assert "2024, 2025" in r.json()["detail"]


def test_revenue_lines_and_projections(client: Any) -> None:
    levies = get(client, "/v1/budgets/2025/revenue?group_code=04")
    assert {x["item_name"] for x in levies} >= {"Pole levy", "Trading (Wholesale) Business Levy"}
    assert {x["stage"] for x in levies} == {"budget"}
    with_projections = get(client, "/v1/budgets/2025/revenue?group_code=04&projections=true")
    assert {x["fiscal_year"] for x in with_projections} == {2025, 2026, 2027}


def test_changes_use_the_books_own_prior_column(client: Any) -> None:
    c = get(client, "/v1/budgets/2025/changes?basis=programme")
    by_name = {x["name"]: x for x in c["lines"]}
    cdf = by_name["Constituency Development"]
    assert (cdf["previous_zmw"], cdf["current_zmw"], cdf["change_pct"]) == (214_449_494, 252_407_054, 17.7)
    new = by_name["Social Protection and Community Development"]
    assert new["previous_zmw"] is None and new["change_pct"] is None
    # Biggest movers first.
    assert c["lines"][0]["name"] == "Social Protection and Community Development"
    assert client.get("/v1/budgets/2025/changes?basis=nonsense").status_code == 422


def test_cdf_stories_filters_and_paging(client: Any) -> None:
    page = get(client, "/v1/cdf/stories?constituency=MATERO&limit=2")
    assert page["total"] >= 2 and len(page["items"]) == 2
    assert all("Matero" in s["constituencies"] for s in page["items"])
    dates = [s["published_on"] for s in page["items"]]
    assert dates == sorted(dates, reverse=True)

    second = get(client, "/v1/cdf/stories?constituency=matero&limit=2&offset=2")
    assert {s["post_id"] for s in second["items"]}.isdisjoint(s["post_id"] for s in page["items"])

    health = get(client, "/v1/cdf/stories?sector=health&limit=100")
    assert health["total"] > 0 and all("health" in s["sectors"] for s in health["items"])

    found = get(client, "/v1/cdf/stories?q=market")
    assert all("market" in (s["title"] + s["summary"]).lower() for s in found["items"])
    assert get(client, "/v1/cdf/stories?q=%25")["total"] == get(client, "/v1/cdf/stories")["total"]


@pytest.mark.parametrize("url", ["/v1/cdf/stories?constituency=Atlantis", "/v1/cdf/stories?limit=1000"])
def test_bad_filters_are_rejected(client: Any, url: str) -> None:
    assert client.get(url).status_code == 422


def test_constituencies(client: Any) -> None:
    rows = get(client, "/v1/cdf/constituencies")
    assert len(rows) == 7
    assert [r["stories"] for r in rows] == sorted((r["stories"] for r in rows), reverse=True)


def test_quality_report(client: Any) -> None:
    q = get(client, "/v1/quality")
    assert q["summary"].get("fail", 0) == 0
    assert {s["key"] for s in q["sources"]} == {"budget-2024", "budget-2025", "news"}
    assert all(len(s["sha256"]) == 64 for s in q["sources"])
    assert q["loaded_at"] is not None
    restated = [c for c in q["checks"] if "restates" in c["detail"]]
    assert restated, "the 2025 book's restated 2024 figures should be reported"


def test_loading_twice_gives_the_same_data(loaded: None) -> None:
    from zod.db import CdfStory, LoadRun, RevenueLine, session_factory
    from zod.load import load

    def counts() -> tuple[int, int]:
        with session_factory()() as s:
            return (
                s.scalar(select(func.count()).select_from(RevenueLine)) or 0,
                s.scalar(select(func.count()).select_from(CdfStory)) or 0,
            )

    before = counts()
    with session_factory()() as s:
        load(s, SNAPSHOT)
    assert counts() == before
    with session_factory()() as s:
        runs = s.scalars(select(LoadRun).order_by(LoadRun.id.desc()).limit(2)).all()
        assert runs[0].snapshot_sha256 == runs[1].snapshot_sha256


def test_a_failed_load_keeps_the_old_data(loaded: None, tmp_path: Any) -> None:
    import shutil

    from zod.db import RevenueLine, session_factory
    from zod.load import load

    broken = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, broken)
    text = (broken / "cdf_stories.csv").read_text(encoding="utf-8").splitlines()
    (broken / "cdf_stories.csv").write_text("\n".join([text[0], text[1], text[1]]) + "\n", encoding="utf-8")

    with session_factory()() as s:
        before = s.scalar(select(func.count()).select_from(RevenueLine))
    with session_factory()() as s, pytest.raises(Exception, match="duplicate key"):
        load(s, broken)  # two stories with the same post id
    with session_factory()() as s:
        assert s.scalar(select(func.count()).select_from(RevenueLine)) == before


def test_downloads_are_the_committed_files(client: Any) -> None:
    import csv
    import hashlib
    import io

    listing = client.get("/v1/downloads").json()
    assert [d["file"] for d in listing] == [
        "budget_books.csv",
        "revenue.csv",
        "spending.csv",
        "cdf_stories.csv",
        "checks.csv",
    ]
    for d in listing:
        r = client.get(d["url"])
        assert r.status_code == 200
        assert r.headers["content-type"] == "text/csv; charset=utf-8"
        assert f'filename="lusaka-{d["file"]}"' in r.headers["content-disposition"]
        committed = (SNAPSHOT / d["file"]).read_bytes().replace(b"\r\n", b"\n")
        assert r.content == committed, f"{d['file']} differs from data/snapshot"
        assert hashlib.sha256(r.content).hexdigest() == d["sha256"]
        assert d["rows"] == len(list(csv.reader(io.StringIO(committed.decode())))) - 1


def test_unknown_download_lists_the_files(client: Any) -> None:
    r = client.get("/v1/downloads/passwords.csv")
    assert r.status_code == 404
    assert "revenue.csv" in r.json()["detail"]


def test_load_skips_a_snapshot_that_is_already_loaded(loaded: None, tmp_path: Any, capsys: Any) -> None:
    import shutil

    from zod.cli import main
    from zod.db import LoadRun, session_factory
    from zod.load import is_loaded

    changed = tmp_path / "snapshot"
    shutil.copytree(SNAPSHOT, changed)
    (changed / "checks.csv").write_text("dataset,name,status,detail\n", encoding="utf-8")
    with session_factory()() as s:
        assert is_loaded(s, SNAPSHOT)
        assert not is_loaded(s, changed)
        runs = s.scalar(select(func.count()).select_from(LoadRun))

    assert main(["load", "--snapshot", str(SNAPSHOT)]) == 0
    assert "already loaded" in capsys.readouterr().out
    with session_factory()() as s:
        assert s.scalar(select(func.count()).select_from(LoadRun)) == runs
