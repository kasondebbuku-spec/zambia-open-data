"""Load the committed snapshot into PostgreSQL.

Everything happens in one transaction: the old rows are deleted and the new ones
inserted, so if anything goes wrong the database keeps the previous dataset. Loading
the same snapshot twice gives the same result.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from .db import BudgetBook, CdfStory, LoadRun, QualityCheck, RevenueLine, SourceRow, SpendingLine
from .pipeline.snapshot import FILES


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _int(v: str) -> int | None:
    return int(v) if v != "" else None


def _list(v: str) -> list[str]:
    return [x for x in v.split(";") if x]


def snapshot_sha256(folder: Path) -> str:
    h = hashlib.sha256()
    for name in FILES:
        h.update(name.encode())
        # Normalise line endings so a Windows checkout hashes the same as Linux.
        h.update((folder / name).read_bytes().replace(b"\r\n", b"\n"))
    return h.hexdigest()


def read_snapshot(folder: Path) -> dict[type[Any], list[dict[str, Any]]]:
    sources = json.loads((folder / "sources.json").read_text(encoding="utf-8"))
    return {
        SourceRow: [{**s, "fetched_at": datetime.fromisoformat(s["fetched_at"])} for s in sources],
        BudgetBook: [
            {
                "year": int(r["year"]),
                "revenue_total_zmw": int(r["revenue_total_zmw"]),
                "spending_total_zmw": int(r["spending_total_zmw"]),
                "source_key": r["source"],
            }
            for r in _rows(folder / "budget_books.csv")
        ],
        RevenueLine: [
            {
                "book_year": int(r["book_year"]),
                "line": int(r["line"]),
                "fiscal_year": int(r["fiscal_year"]),
                "stage": r["stage"],
                "group_code": r["group_code"],
                "group_name": r["group_name"],
                "item_code": r["item_code"] or None,
                "item_name": r["item_name"],
                "amount_zmw": int(r["amount_zmw"]),
            }
            for r in _rows(folder / "revenue.csv")
        ],
        SpendingLine: [
            {
                "book_year": int(r["book_year"]),
                "fiscal_year": int(r["fiscal_year"]),
                "stage": r["stage"],
                "basis": r["basis"],
                "code": int(r["code"]),
                "name": r["name"],
                "amount_zmw": int(r["amount_zmw"]),
            }
            for r in _rows(folder / "spending.csv")
        ],
        CdfStory: [
            {
                "post_id": int(r["post_id"]),
                "published_on": date.fromisoformat(r["published_on"]),
                "title": r["title"],
                "url": r["url"],
                "summary": r["summary"],
                "constituencies": _list(r["constituencies"]),
                "sectors": _list(r["sectors"]),
                "status": r["status"] or None,
                "largest_amount_zmw": _int(r["largest_amount_zmw"]),
                "completion_pct": _int(r["completion_pct"]),
            }
            for r in _rows(folder / "cdf_stories.csv")
        ],
        QualityCheck: _rows(folder / "checks.csv"),
    }


def load(session: Session, folder: Path) -> int:
    data = read_snapshot(folder)
    with session.begin():
        # Children first, because of the foreign keys.
        for model in (RevenueLine, SpendingLine, BudgetBook, SourceRow, CdfStory, QualityCheck):
            session.execute(delete(model))
        total = 0
        for model, rows in data.items():
            if rows:
                session.execute(insert(model), rows)
                total += len(rows)
        session.add(LoadRun(snapshot_sha256=snapshot_sha256(folder), rows=total))
    return total
