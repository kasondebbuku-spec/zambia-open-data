"""Budget book parsing and checks, on text copied from the real 2024 and 2025 books."""

from __future__ import annotations

from dataclasses import replace

from zod.pipeline.budget import Column, amount, clean_text, parse_book, parse_revenue, parse_spending
from zod.pipeline.checks import check_balanced, check_restated, check_revenue, check_spending

REVENUE_2025 = """\
CODE REVENUE DESCRIPTION APPROVED REVISED BUDGET
BUDGET 2025 BUDGET 2026 ESTIMATE 2027
01 Local taxes/rates
001 Residential 85,077,821 93,585,603 102,944,163
002 Commercial 71,313,664 78,445,030 86,289,533
SubItem Total 156,391,485 172,030,633 189,233,696
001 Personal levy 2,625,000 2,887,500 3,176,250
SubItem Total 2,625,000 2,887,500 3,176,250
CODE REVENUE DESCRIPTION APPROVED REVISED BUDGET
BUDGET 2025 BUDGET 2026 ESTIMATE 2027
04 Levies
004 Pole levy 575,858 633,444 696,789
082 1,560,000 1,716,000 1,887,600
SubItem Total 2,135,858 2,349,444 2,584,389
02 Fees and Charges
007 Rentals/lease of Council�s properties 5,849,830 6,434,813 7,078,294
SubItem Total 5,849,830 6,434,813 7,078,294
Grand Total 167,002,173 183,702,390 202,072,629
4.0 BUDGET SUMMARY
001 Not revenue 1 2 3
"""

SPENDING_2025 = """\
Table:1 Budget Allocation by Economic Classification
No ECONOMIC CLASSIFICATION 2023 2024 2025 BUDGET
APPROVED APPROVED ESTIMATE (K)
21 Personal Emoluments (0) 100 300
41 Current Liabilities (Payable within one year) (0) 67 0
Head Total (0) 167 300
Figure 1: Budget Allocation by Economic Classification
Table:2 Budget Allocation by Programme
2023 2024 2025
Programme
1 Constituency Development (0) 100 250
18 Social Protection and Community Development (0) - 50
17 Fisheries and Livestock (0) 67 -
(0) 167 300
Head Total
Figure 2:Budget Allocation by Programme
"""


def lines(text: str) -> list[str]:
    return text.splitlines()


def test_amounts_and_placeholders() -> None:
    assert amount("1,079,607,654") == 1079607654
    assert amount("-") is None
    assert amount("(0)") is None
    assert clean_text("Council�s   properties") == "Council's properties"


def test_revenue_lines_groups_and_columns() -> None:
    columns, rows = parse_revenue(lines(REVENUE_2025), 2025)
    assert columns == (Column(2025, "budget"), Column(2026, "projection"), Column(2027, "projection"))
    items = [r for r in rows if r.kind == "item"]
    assert [(r.group_code, r.item_code, r.item_name) for r in items] == [
        ("01", "001", "Residential"),
        ("01", "002", "Commercial"),
        ("01", "001", "Personal levy"),
        ("04", "004", "Pole levy"),
        ("04", "082", "Item 082 (no description in the budget book)"),
        ("02", "007", "Rentals/lease of Council's properties"),
    ]
    assert items[0].amounts == (85077821, 93585603, 102944163)


def test_revenue_stops_at_the_budget_summary() -> None:
    _, rows = parse_revenue(lines(REVENUE_2025), 2025)
    assert not any(r.item_name == "Not revenue" for r in rows)
    assert rows[-1].kind == "grand_total"


def test_spending_tables_and_both_total_layouts() -> None:
    tables = parse_spending(lines(SPENDING_2025), 2025)
    econ, prog = tables["economic"], tables["programme"]
    assert econ.columns == (Column(2023, "prior"), Column(2024, "prior"), Column(2025, "budget"))
    assert econ.lines[1] == ("41", "Current Liabilities (Payable within one year)", (None, 67, 0))
    assert econ.head_total == (None, 167, 300)
    # The programme table prints its total on the line *before* "Head Total".
    assert prog.head_total == (None, 167, 300)
    assert [code for code, _, _ in prog.lines] == ["1", "18", "17"]


def book():  # type: ignore[no-untyped-def]
    return parse_book(lines(REVENUE_2025 + SPENDING_2025), 2025)


def test_checks_pass_on_consistent_books() -> None:
    b = book()
    assert [c.status for c in check_revenue(b)] == ["pass"]
    assert [c.status for c in check_spending(b)] == ["pass", "pass"]


def test_small_gaps_are_rounding_and_big_gaps_fail() -> None:
    b = book()
    off_by_one = replace(b.revenue[2], amounts=(156391486, 172030633, 189233696))
    b.revenue[2] = off_by_one
    (check,) = check_revenue(b)
    assert check.status == "warn" and "rounding" in check.detail

    b.revenue[2] = replace(off_by_one, amounts=(150000000, 172030633, 189233696))
    (check,) = check_revenue(b)
    assert check.status == "fail" and "Local taxes/rates 2025" in check.detail


def test_a_missed_line_fails_the_check() -> None:
    b = book()
    b.spending["economic"].lines.pop(0)
    assert check_spending(b)[0].status == "fail"


def test_balanced_budget() -> None:
    b = book()
    b.spending["economic"].head_total = (None, 167, 300)
    checks = check_balanced(b)
    # revenue 167,002,173 vs spending 300 in this cut-down fixture
    assert {c.status for c in checks} == {"fail"}
    assert "revenue K167,002,173, spending K300" in checks[0].detail


def test_restated_figures_are_flagged() -> None:
    this_year = book()
    last_year = parse_book(
        lines(
            REVENUE_2025.replace("2025", "2024").replace("2026", "2025").replace("2027", "2026")
            + SPENDING_2025.replace("2023 2024 2025", "2022 2023 2024")
        ),
        2024,
    )
    # Last year's book approved 300 for salaries; this year's reprints it as 100.
    checks = {c.dataset: c for c in check_restated([last_year, this_year])}
    econ = checks["spending by economic 2025"]
    assert econ.status == "warn"
    assert "Personal Emoluments: K300 to K100" in econ.detail
