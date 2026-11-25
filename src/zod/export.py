"""Write the published CSV files back out of the database.

The API's downloads come from here, so they always match what the API serves. They use
the snapshot's headers, row order and formatting, so a downloaded file is byte-for-byte
the committed ``data/snapshot`` file (this is tested).
"""

from __future__ import annotations

import io
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import BudgetBook, CdfStory, QualityCheck, RevenueLine, SpendingLine
from .pipeline.snapshot import HEADERS, write_csv

Rows = Iterable[Sequence[Any]]


def _books(db: Session) -> Rows:
    for b in db.scalars(select(BudgetBook).order_by(BudgetBook.year)):
        yield (b.year, b.revenue_total_zmw, b.spending_total_zmw, b.source_key)


def _revenue(db: Session) -> Rows:
    for r in db.scalars(select(RevenueLine).order_by(RevenueLine.id)):
        yield (
            r.book_year,
            r.line,
            r.fiscal_year,
            r.stage,
            r.group_code,
            r.group_name,
            r.item_code,
            r.item_name,
            r.amount_zmw,
        )


def _spending(db: Session) -> Rows:
    for r in db.scalars(select(SpendingLine).order_by(SpendingLine.id)):
        yield (r.book_year, r.fiscal_year, r.stage, r.basis, r.code, r.name, r.amount_zmw)


def _stories(db: Session) -> Rows:
    order = (CdfStory.published_on.desc(), CdfStory.post_id.desc())
    for s in db.scalars(select(CdfStory).order_by(*order)):
        yield (
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


def _checks(db: Session) -> Rows:
    for c in db.scalars(select(QualityCheck).order_by(QualityCheck.id)):
        yield (c.dataset, c.name, c.status, c.detail)


EXPORTS: dict[str, tuple[str, Callable[[Session], Rows]]] = {
    "budget_books.csv": ("One row per budget book: its year and printed totals", _books),
    "revenue.csv": ("Every revenue line, for each year the book prints", _revenue),
    "spending.csv": ("Every spending line, by type and by programme", _spending),
    "cdf_stories.csv": ("The council's CDF news stories, tagged", _stories),
    "checks.csv": ("The result of every quality check", _checks),
}
assert set(EXPORTS) == set(HEADERS), "every snapshot CSV needs an export"


def csv_text(db: Session, name: str) -> tuple[str, int]:
    """The file's text and its number of data rows."""
    buf = io.StringIO()
    rows = write_csv(buf, HEADERS[name], EXPORTS[name][1](db))
    return buf.getvalue(), rows
