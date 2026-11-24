"""Parse Lusaka City Council's approved budget books ("Output Based Annual Budget").

The books have a real text layer, but pdfplumber's table detection collapses their
columns, so we read the text line by line. Three tables are taken from each book:

* revenue estimates: one line per revenue item, grouped (taxes, fees, levies, grants ...)
* Table 1: spending by economic classification (salaries, goods and services ...)
* Table 2: spending by programme (constituency development, public health ...)

Every money column is tagged with the fiscal year it refers to and a *stage* relative
to the book: ``budget`` is the year the book approves, ``prior`` is an earlier year's
figure as printed in this book, and ``projection`` is a forward estimate.

The parser never guesses silently. Totals printed in the book are kept and checked
against the lines in :mod:`zod.pipeline.checks`, so a line the parser missed shows up
as a failed check instead of a quietly wrong number.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Stage = Literal["budget", "prior", "projection"]
Basis = Literal["economic", "programme"]

_NUM = r"\d[\d,]*"
# A spending cell can be a number, a dash or the "(0)" placeholder the books print for blanks.
_CELL = r"\(0\)|-|\d[\d,]*"


def amount(cell: str) -> int | None:
    """``"1,079,607,654"`` -> 1079607654; dashes and ``(0)`` placeholders are blank."""
    cell = cell.strip()
    if cell in ("", "-", "(0)"):
        return None
    return int(cell.replace(",", ""))


def clean_text(s: str) -> str:
    # The books' font maps the apostrophe to U+FFFD ("Council�s properties").
    return re.sub(r"\s+", " ", s.replace("�", "'")).strip()


@dataclass(frozen=True)
class Column:
    fiscal_year: int
    stage: Stage


@dataclass
class RevenueRow:
    group_code: str
    group_name: str
    item_code: str | None
    item_name: str
    kind: Literal["item", "subtotal", "grand_total"]
    amounts: tuple[int | None, ...]


@dataclass
class SpendingTable:
    basis: Basis
    columns: tuple[Column, ...]
    lines: list[tuple[str, str, tuple[int | None, ...]]] = field(default_factory=list)
    head_total: tuple[int | None, ...] | None = None


@dataclass
class BudgetBook:
    year: int
    revenue_columns: tuple[Column, ...]
    revenue: list[RevenueRow]
    spending: dict[Basis, SpendingTable]


# --------------------------------------------------------------------------- revenue

_REV_HEADER = re.compile(r"BUDGET\s+(\d{4})\s+BUDGET\s+(\d{4})\s+ESTIMATE\s+(\d{4})")
_REV_GROUP = re.compile(r"^(\d{2})\s+([A-Za-z].*?)$")
# The description can be missing: the 2025 book prints "082 1,560,000 1,716,000 1,887,600".
_REV_ITEM = re.compile(rf"^(\d{{3}})\s+(?:(.*?)\s+)?({_NUM})\s+({_NUM})\s+({_NUM})$")
_REV_TOTAL = re.compile(rf"^(SubItem Total|Grand Total)\s+({_NUM})\s+({_NUM})\s+({_NUM})$")


def parse_revenue(lines: Iterable[str], book_year: int) -> tuple[tuple[Column, ...], list[RevenueRow]]:
    columns: tuple[Column, ...] = ()
    rows: list[RevenueRow] = []
    group_code = group_name = ""
    for raw in lines:
        line = clean_text(raw)
        if "BUDGET SUMMARY" in line and rows:
            break  # the revenue section is over; later pages reuse similar codes
        if m := _REV_HEADER.search(line):
            years = [int(y) for y in m.groups()]
            columns = tuple(Column(y, "budget" if y == book_year else "projection") for y in years)
            continue
        if not columns:
            continue
        if m := _REV_TOTAL.match(line):
            kind: Literal["subtotal", "grand_total"] = (
                "subtotal" if m[1] == "SubItem Total" else "grand_total"
            )
            rows.append(
                RevenueRow(group_code, group_name, None, m[1], kind, tuple(amount(m[i]) for i in (2, 3, 4)))
            )
            continue
        if m := _REV_ITEM.match(line):
            name = clean_text(m[2] or "") or f"Item {m[1]} (no description in the budget book)"
            rows.append(
                RevenueRow(group_code, group_name, m[1], name, "item", tuple(amount(m[i]) for i in (3, 4, 5)))
            )
            continue
        if (m := _REV_GROUP.match(line)) and not re.search(rf"{_NUM}$", line):
            group_code, group_name = m[1], clean_text(m[2])
    return columns, rows


# -------------------------------------------------------------------------- spending

_TABLE_HEADING: dict[Basis, re.Pattern[str]] = {
    "economic": re.compile(r"^Table\s*:?\s*1\b.*Economic Classification", re.I),
    "programme": re.compile(r"^Table\s*:?\s*2\b.*Allocation by Programme", re.I),
}
_YEARS = re.compile(r"\b(20\d{2})\b")
_SPEND_LINE = re.compile(rf"^(\d{{1,2}})\s+([A-Za-z].*?)\s+({_CELL})\s+({_CELL})\s+({_CELL})$")
_BARE_TOTAL = re.compile(rf"^(?:Head Total:?\s+)?({_CELL})\s+({_CELL})\s+({_CELL})$")


def parse_spending(lines: list[str], book_year: int) -> dict[Basis, SpendingTable]:
    tables: dict[Basis, SpendingTable] = {}
    i = 0
    while i < len(lines):
        basis = next((b for b, rx in _TABLE_HEADING.items() if rx.search(clean_text(lines[i]))), None)
        if basis is None or basis in tables:
            i += 1
            continue
        table: SpendingTable | None = None
        pending_total: tuple[int | None, ...] | None = None
        i += 1
        while i < len(lines):
            line = clean_text(lines[i])
            i += 1
            if table is None:
                years = [int(y) for y in _YEARS.findall(line)]
                if len(years) >= 3:
                    cols = tuple(Column(y, "budget" if y == book_year else "prior") for y in years[:3])
                    table = SpendingTable(basis, cols)
                continue
            if m := _SPEND_LINE.match(line):
                table.lines.append((m[1], clean_text(m[2]), tuple(amount(m[k]) for k in (3, 4, 5))))
                continue
            # The total is printed either on the "Head Total" line or on the line just before it.
            if m := _BARE_TOTAL.match(line):
                pending_total = tuple(amount(m[k]) for k in (1, 2, 3))
                if line.startswith("Head Total"):
                    break
                continue
            if line.startswith("Head Total") or line.startswith("Figure"):
                break
        if table is not None:
            table.head_total = pending_total
            tables[basis] = table
    return tables


# ------------------------------------------------------------------------------ book


def pdf_lines(path: Path) -> list[str]:
    import pdfplumber  # only needed when rebuilding from the PDFs

    with pdfplumber.open(path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text.split("\n")


def parse_book(lines: list[str], book_year: int) -> BudgetBook:
    columns, revenue = parse_revenue(lines, book_year)
    if not columns:
        raise ValueError(f"No revenue table found in the {book_year} budget book")
    spending = parse_spending(lines, book_year)
    missing = {"economic", "programme"} - spending.keys()
    if missing:
        raise ValueError(f"The {book_year} budget book is missing table(s): {', '.join(sorted(missing))}")
    return BudgetBook(book_year, columns, revenue, spending)
