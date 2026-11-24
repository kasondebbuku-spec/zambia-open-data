from __future__ import annotations

from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import (
    BudgetBook,
    CdfStory,
    LoadRun,
    QualityCheck,
    RevenueLine,
    SourceRow,
    SpendingLine,
    get_session,
)
from ..pipeline.news import CONSTITUENCIES, SECTORS
from . import schemas as s

router = APIRouter(prefix="/v1")
DB = Annotated[Session, Depends(get_session)]


def _pct(part: int, whole: int) -> float:
    return round(part * 100 / whole, 1) if whole else 0.0


def _book(db: Session, year: int) -> BudgetBook:
    book = db.get(BudgetBook, year)
    if book is None:
        years = ", ".join(str(y) for y in db.scalars(select(BudgetBook.year).order_by(BudgetBook.year)))
        raise HTTPException(404, f"No budget book for {year}. Years available: {years or 'none'}.")
    return book


def _summary(db: Session, book: BudgetBook) -> s.BudgetSummary:
    prev = db.get(BudgetBook, book.year - 1)
    source = db.get(SourceRow, book.source_key)
    return s.BudgetSummary(
        year=book.year,
        total_zmw=book.revenue_total_zmw,
        change_pct=_pct(book.revenue_total_zmw - prev.revenue_total_zmw, prev.revenue_total_zmw)
        if prev
        else None,
        source_url=source.url if source else "",
    )


@router.get("/budgets", response_model=list[s.BudgetSummary], tags=["budgets"])
def list_budgets(db: DB) -> list[s.BudgetSummary]:
    """Every approved budget book we have, with its total and the change from the year before."""
    return [_summary(db, b) for b in db.scalars(select(BudgetBook).order_by(BudgetBook.year))]


@router.get("/budgets/{year}", response_model=s.BudgetDetail, tags=["budgets"])
def budget(year: int, db: DB) -> s.BudgetDetail:
    """Where the year's money comes from and where it goes, as shares of the total."""
    book = _book(db, year)
    total = book.revenue_total_zmw

    groups = db.execute(
        select(RevenueLine.group_code, RevenueLine.group_name, func.sum(RevenueLine.amount_zmw))
        .where(RevenueLine.book_year == year, RevenueLine.stage == "budget")
        .group_by(RevenueLine.group_code, RevenueLine.group_name)
        .order_by(func.sum(RevenueLine.amount_zmw).desc())
    ).all()

    def spending(basis: str) -> list[s.Share]:
        rows = db.execute(
            select(SpendingLine.code, SpendingLine.name, SpendingLine.amount_zmw)
            .where(
                SpendingLine.book_year == year, SpendingLine.stage == "budget", SpendingLine.basis == basis
            )
            .order_by(SpendingLine.amount_zmw.desc())
        ).all()
        return [s.Share(code=str(c), name=n, amount_zmw=a, share_pct=_pct(a, total)) for c, n, a in rows]

    return s.BudgetDetail(
        **_summary(db, book).model_dump(),
        revenue_by_group=[
            s.Share(code=c, name=n, amount_zmw=int(a), share_pct=_pct(int(a), total)) for c, n, a in groups
        ],
        spending_by_economic=spending("economic"),
        spending_by_programme=spending("programme"),
    )


@router.get("/budgets/{year}/revenue", response_model=list[s.RevenueItem], tags=["budgets"])
def revenue(
    year: int,
    db: DB,
    group_code: Annotated[
        str | None, Query(description="Only one revenue group, e.g. 02 for fees and charges")
    ] = None,
    projections: Annotated[bool, Query(description="Include the book's forward estimates")] = False,
) -> list[RevenueLine]:
    """Every revenue line in the book: rates, fees, levies, permits, grants and the CDF."""
    _book(db, year)
    q = select(RevenueLine).where(RevenueLine.book_year == year)
    if not projections:
        q = q.where(RevenueLine.stage == "budget")
    if group_code:
        q = q.where(RevenueLine.group_code == group_code)
    return list(db.scalars(q.order_by(RevenueLine.line, RevenueLine.fiscal_year)))


@router.get("/budgets/{year}/changes", response_model=s.Changes, tags=["budgets"])
def changes(year: int, db: DB, basis: s.Basis = "programme") -> s.Changes:
    """How each spending line moved from last year, using last year's figures as reprinted in
    this year's book, so both columns use the same codes and any restatements."""
    _book(db, year)
    rows = db.scalars(
        select(SpendingLine).where(
            SpendingLine.book_year == year,
            SpendingLine.basis == basis,
            SpendingLine.fiscal_year.in_([year - 1, year]),
        )
    ).all()
    by_code: dict[int, dict[str, int | str | None]] = {}
    for r in rows:
        line = by_code.setdefault(r.code, {"name": r.name, "previous": None, "current": None})
        line["current" if r.fiscal_year == year else "previous"] = r.amount_zmw
        if r.fiscal_year == year:
            line["name"] = r.name
    out = []
    for code, line in sorted(by_code.items()):
        prev, cur = line["previous"], line["current"]
        assert prev is None or isinstance(prev, int)
        assert cur is None or isinstance(cur, int)
        diff = (cur or 0) - (prev or 0) if prev is not None or cur is not None else None
        out.append(
            s.Change(
                code=code,
                name=str(line["name"]),
                previous_zmw=prev,
                current_zmw=cur,
                change_zmw=diff,
                change_pct=_pct(diff, prev) if prev and diff is not None else None,
            )
        )
    out.sort(key=lambda c: abs(c.change_zmw or 0), reverse=True)
    return s.Changes(year=year, previous_year=year - 1, basis=basis, lines=out)


@router.get("/cdf/stories", response_model=s.Page[s.Story], tags=["cdf"])
def cdf_stories(
    db: DB,
    constituency: Annotated[str | None, Query(description=f"One of: {', '.join(CONSTITUENCIES)}")] = None,
    sector: Annotated[str | None, Query(description=f"One of: {', '.join(SECTORS)}")] = None,
    status: str | None = None,
    q: Annotated[str | None, Query(max_length=100, description="Words in the title or summary")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> s.Page[s.Story]:
    """The council's news stories about Constituency Development Fund projects, newest first."""
    where = []
    if constituency:
        match = next((c for c in CONSTITUENCIES if c.lower() == constituency.lower()), None)
        if match is None:
            raise HTTPException(422, f"Unknown constituency. Use one of: {', '.join(CONSTITUENCIES)}.")
        where.append(CdfStory.constituencies.contains([match]))
    if sector:
        where.append(CdfStory.sectors.contains([sector]))
    if status:
        where.append(CdfStory.status == status)
    if q:
        like = f"%{q.replace('%', '').replace('_', '')}%"
        where.append(or_(CdfStory.title.ilike(like), CdfStory.summary.ilike(like)))
    total = db.scalar(select(func.count()).select_from(CdfStory).where(*where)) or 0
    items = db.scalars(
        select(CdfStory)
        .where(*where)
        .order_by(CdfStory.published_on.desc(), CdfStory.post_id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return s.Page[s.Story](
        total=total,
        limit=limit,
        offset=offset,
        items=[s.Story.model_validate(i, from_attributes=True) for i in items],
    )


@router.get("/cdf/constituencies", response_model=list[s.ConstituencySummary], tags=["cdf"])
def constituencies(db: DB) -> list[s.ConstituencySummary]:
    """How many CDF stories mention each of Lusaka's seven constituencies, and on what."""
    stories = db.scalars(select(CdfStory)).all()
    out = []
    for name in CONSTITUENCIES:
        mine = [st for st in stories if name in st.constituencies]
        sectors = Counter(sec for st in mine for sec in st.sectors)
        out.append(
            s.ConstituencySummary(
                name=name,
                stories=len(mine),
                latest_story_on=max((st.published_on for st in mine), default=None),
                sectors=dict(sectors.most_common()),
            )
        )
    return sorted(out, key=lambda c: c.stories, reverse=True)


@router.get("/quality", response_model=s.Quality, tags=["about the data"])
def quality(db: DB) -> s.Quality:
    """Every data quality check, the source files with their fingerprints, and when the data was loaded."""
    run = db.scalars(select(LoadRun).order_by(LoadRun.id.desc()).limit(1)).first()
    checks = db.scalars(select(QualityCheck).order_by(QualityCheck.id)).all()
    return s.Quality(
        loaded_at=run.loaded_at if run else None,
        snapshot_sha256=run.snapshot_sha256 if run else None,
        summary=dict(Counter(c.status for c in checks)),
        checks=[s.CheckOut.model_validate(c, from_attributes=True) for c in checks],
        sources=[
            s.SourceOut.model_validate(x, from_attributes=True)
            for x in db.scalars(select(SourceRow).order_by(SourceRow.key))
        ],
    )
