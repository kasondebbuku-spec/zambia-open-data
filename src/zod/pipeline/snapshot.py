"""Build the committed snapshot (``data/snapshot/*.csv``) from the raw downloads.

The snapshot is the project's published dataset: plain CSV files anyone can open in
Excel, plus ``checks.csv`` with the result of every quality check and ``sources.json``
saying exactly which files they came from. The build refuses to write anything if a
check fails.
"""

from __future__ import annotations

import csv
import json
import shutil
from collections.abc import Iterable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .budget import BudgetBook, parse_book, pdf_lines
from .checks import Check, run_all
from .fetch import BUDGET_BOOKS
from .news import Story, stories

FILES = ("budget_books.csv", "revenue.csv", "spending.csv", "cdf_stories.csv", "checks.csv", "sources.json")


class ChecksFailed(Exception):
    def __init__(self, failed: list[Check]):
        super().__init__("; ".join(f"{c.dataset}: {c.detail}" for c in failed))
        self.failed = failed


def _write(path: Path, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> int:
    n = 0
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(["" if v is None else v for v in row])
            n += 1
    return n


def book_rows(book: BudgetBook) -> list[tuple[Any, ...]]:
    grand = next(r for r in book.revenue if r.kind == "grand_total")
    rev_col = next(c for c, col in enumerate(book.revenue_columns) if col.stage == "budget")
    spend = book.spending["economic"]
    sp_col = next(c for c, col in enumerate(spend.columns) if col.stage == "budget")
    assert spend.head_total is not None
    return [(book.year, grand.amounts[rev_col], spend.head_total[sp_col], f"budget-{book.year}")]


def revenue_rows(book: BudgetBook) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    line = 0
    for r in book.revenue:
        if r.kind != "item":
            continue
        line += 1
        for col, value in zip(book.revenue_columns, r.amounts, strict=True):
            if value is not None:
                rows.append(
                    (
                        book.year,
                        line,
                        col.fiscal_year,
                        col.stage,
                        r.group_code,
                        r.group_name,
                        r.item_code,
                        r.item_name,
                        value,
                    )
                )
    return rows


def spending_rows(book: BudgetBook) -> list[tuple[Any, ...]]:
    rows: list[tuple[Any, ...]] = []
    for basis, table in book.spending.items():
        for code, name, amounts in table.lines:
            for col, value in zip(table.columns, amounts, strict=True):
                if value is not None:
                    rows.append((book.year, col.fiscal_year, col.stage, basis, int(code), name, value))
    return rows


def story_rows(found: list[Story]) -> list[tuple[Any, ...]]:
    return [
        (
            s.post_id,
            s.published_on.isoformat(),
            s.title,
            s.url,
            s.summary,
            ";".join(s.constituencies),
            ";".join(s.sectors),
            s.status,
            s.largest_amount_zmw,
            s.completion_pct,
        )
        for s in found
    ]


def build(raw: Path, out: Path) -> dict[str, int]:
    books = [parse_book(pdf_lines(raw / f"budget-{year}.pdf"), year) for year in BUDGET_BOOKS]
    posts = json.loads((raw / "posts.json").read_text(encoding="utf-8"))
    found, duplicates = stories(posts)
    checks = run_all(books)
    if duplicates:
        checks.append(
            Check(
                "cdf stories",
                "Duplicate posts removed",
                "warn",
                "The same article was posted more than once; kept the newest. Dropped post ids: "
                + ", ".join(map(str, duplicates)),
            )
        )
    failed = [c for c in checks if c.status == "fail"]
    if failed:
        raise ChecksFailed(failed)

    out.mkdir(parents=True, exist_ok=True)
    counts = {
        "budget_books.csv": _write(
            out / "budget_books.csv",
            ("year", "revenue_total_zmw", "spending_total_zmw", "source"),
            [r for b in books for r in book_rows(b)],
        ),
        "revenue.csv": _write(
            out / "revenue.csv",
            (
                "book_year",
                "line",
                "fiscal_year",
                "stage",
                "group_code",
                "group_name",
                "item_code",
                "item_name",
                "amount_zmw",
            ),
            [r for b in books for r in revenue_rows(b)],
        ),
        "spending.csv": _write(
            out / "spending.csv",
            ("book_year", "fiscal_year", "stage", "basis", "code", "name", "amount_zmw"),
            [r for b in books for r in spending_rows(b)],
        ),
        "cdf_stories.csv": _write(
            out / "cdf_stories.csv",
            (
                "post_id",
                "published_on",
                "title",
                "url",
                "summary",
                "constituencies",
                "sectors",
                "status",
                "largest_amount_zmw",
                "completion_pct",
            ),
            story_rows(found),
        ),
        "checks.csv": _write(
            out / "checks.csv",
            ("dataset", "name", "status", "detail"),
            [tuple(asdict(c).values()) for c in checks],
        ),
    }
    shutil.copyfile(raw / "manifest.json", out / "sources.json")
    return counts
