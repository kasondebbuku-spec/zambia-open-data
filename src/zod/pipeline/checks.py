"""Data quality checks, run every time the snapshot is rebuilt.

``fail`` means the numbers can't be trusted: a total in the book doesn't match its
lines, so the parser probably missed or misread something. The build stops.
``warn`` means the data is as published but a reader should know something about it,
for example last year's figures being restated in this year's book.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .budget import BudgetBook, RevenueRow

Status = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class Check:
    dataset: str
    name: str
    status: Status
    detail: str


def _k(n: int | None) -> str:
    return "blank" if n is None else f"K{n:,}"


def _rounding_ok(got: int | None, printed: int | None, n_lines: int) -> bool:
    """The books print whole kwacha but add up the unrounded figures, so a total can be
    off by up to half a kwacha per line. Anything bigger is a real mismatch."""
    if got is None or printed is None:
        return got == printed
    return abs(got - printed) <= max(1, n_lines // 2)


def _verdict(bad: list[str], rounding: list[str], ok: str) -> tuple[Status, str]:
    if bad:
        return "fail", "; ".join(bad + rounding)
    if rounding:
        return "warn", "Off by rounding in the book itself: " + "; ".join(rounding)
    return "pass", ok


def _sum(values: list[int | None]) -> int | None:
    present = [v for v in values if v is not None]
    return sum(present) if present else None


def check_revenue(book: BudgetBook) -> list[Check]:
    ds = f"revenue {book.year}"
    out: list[Check] = []
    items: list[RevenueRow] = []
    subtotals: list[RevenueRow] = []
    bad: list[str] = []
    rounding: list[str] = []
    for row in book.revenue:
        if row.kind == "item":
            items.append(row)
        elif row.kind == "subtotal":
            for c, col in enumerate(book.revenue_columns):
                got = _sum([r.amounts[c] for r in items])
                if got != row.amounts[c]:
                    msg = f"{row.group_name} {col.fiscal_year}: lines add up to {_k(got)}, book says {_k(row.amounts[c])}"
                    (rounding if _rounding_ok(got, row.amounts[c], len(items)) else bad).append(msg)
            subtotals.append(row)
            items = []
        else:
            for c, col in enumerate(book.revenue_columns):
                got = _sum([r.amounts[c] for r in subtotals])
                if got != row.amounts[c]:
                    msg = f"Grand total {col.fiscal_year}: sub-totals add up to {_k(got)}, book says {_k(row.amounts[c])}"
                    (rounding if _rounding_ok(got, row.amounts[c], len(subtotals)) else bad).append(msg)
    n_items = sum(r.kind == "item" for r in book.revenue)
    has_grand = any(r.kind == "grand_total" for r in book.revenue)
    if items:
        bad.append(f"{len(items)} revenue line(s) after the last sub-total")
    if not has_grand:
        bad.append("no grand total found")
    status, detail = _verdict(
        bad, rounding, f"{n_items} lines, {len(subtotals)} sub-totals and the grand total agree"
    )
    out.append(Check(ds, "Revenue lines add up to the book's totals", status, detail))
    return out


def check_spending(book: BudgetBook) -> list[Check]:
    out: list[Check] = []
    for basis, table in book.spending.items():
        ds = f"spending by {basis} {book.year}"
        bad: list[str] = []
        rounding: list[str] = []
        if table.head_total is None:
            bad.append("no head total found")
        else:
            for c, col in enumerate(table.columns):
                got = _sum([line[2][c] for line in table.lines])
                if got != table.head_total[c]:
                    msg = f"{col.fiscal_year}: lines add up to {_k(got)}, book says {_k(table.head_total[c])}"
                    (rounding if _rounding_ok(got, table.head_total[c], len(table.lines)) else bad).append(
                        msg
                    )
        status, detail = _verdict(bad, rounding, f"{len(table.lines)} lines agree with the head total")
        out.append(Check(ds, "Spending lines add up to the head total", status, detail))
    return out


def check_balanced(book: BudgetBook) -> list[Check]:
    """A council budget is balanced: planned spending equals planned revenue."""
    revenue = next(
        (
            r.amounts[c]
            for r in book.revenue
            if r.kind == "grand_total"
            for c, col in enumerate(book.revenue_columns)
            if col.stage == "budget"
        ),
        None,
    )
    out: list[Check] = []
    for basis, table in book.spending.items():
        spend = next(
            (
                table.head_total[c]
                for c, col in enumerate(table.columns)
                if col.stage == "budget" and table.head_total
            ),
            None,
        )
        ok = revenue is not None and revenue == spend
        out.append(
            Check(
                f"budget {book.year}",
                f"Revenue equals spending by {basis}",
                "pass" if ok else "fail",
                f"revenue {_k(revenue)}, spending {_k(spend)}",
            )
        )
    return out


def check_restated(books: list[BudgetBook]) -> list[Check]:
    """Each book reprints last year's approved spending. Flag lines that changed."""
    by_year = {b.year: b for b in books}
    out: list[Check] = []
    for book in books:
        prev = by_year.get(book.year - 1)
        if prev is None:
            continue
        for basis, table in book.spending.items():
            col = next((c for c, cl in enumerate(table.columns) if cl.fiscal_year == prev.year), None)
            prev_table = prev.spending[basis]
            prev_col = next(c for c, cl in enumerate(prev_table.columns) if cl.stage == "budget")
            if col is None:
                continue
            original = {code: amounts[prev_col] for code, _, amounts in prev_table.lines}
            names = {code: name for code, name, _ in prev_table.lines}
            changed = [
                f"{names.get(code, name)}: {_k(original.get(code))} to {_k(amounts[col])}"
                for code, name, amounts in table.lines
                if amounts[col] is not None and original.get(code) != amounts[col]
            ]
            out.append(
                Check(
                    f"spending by {basis} {book.year}",
                    f"{prev.year} figures match the {prev.year} book",
                    "warn" if changed else "pass",
                    ("The " + str(book.year) + " book restates: " + "; ".join(changed))
                    if changed
                    else f"all {prev.year} lines match",
                )
            )
    return out


def run_all(books: list[BudgetBook]) -> list[Check]:
    checks: list[Check] = []
    for book in books:
        checks += check_revenue(book) + check_spending(book) + check_balanced(book)
    return checks + check_restated(books)
