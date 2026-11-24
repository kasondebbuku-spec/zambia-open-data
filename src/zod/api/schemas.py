from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

Basis = Literal["economic", "programme"]


class BudgetSummary(BaseModel):
    year: int
    total_zmw: int = Field(description="Planned revenue for the year, which equals planned spending.")
    change_pct: float | None = Field(description="Change from the previous year's book, if we have it.")
    source_url: str


class Share(BaseModel):
    code: str
    name: str
    amount_zmw: int
    share_pct: float


class BudgetDetail(BudgetSummary):
    revenue_by_group: list[Share]
    spending_by_economic: list[Share]
    spending_by_programme: list[Share]


class RevenueItem(BaseModel):
    group_code: str
    group_name: str
    item_code: str | None
    item_name: str
    fiscal_year: int
    stage: str
    amount_zmw: int


class Change(BaseModel):
    code: int
    name: str
    previous_zmw: int | None = Field(description="Last year's figure as reprinted in this year's book.")
    current_zmw: int | None
    change_zmw: int | None
    change_pct: float | None


class Changes(BaseModel):
    year: int
    previous_year: int
    basis: Basis
    lines: list[Change]


class Story(BaseModel):
    post_id: int
    published_on: date
    title: str
    url: str
    summary: str
    constituencies: list[str]
    sectors: list[str]
    status: str | None = Field(description="Stage the story reports, read from its wording. Check the link.")
    largest_amount_zmw: int | None = Field(description="The largest kwacha amount the story mentions.")
    completion_pct: int | None


class Page[T](BaseModel):
    total: int
    limit: int
    offset: int
    items: list[T]


class ConstituencySummary(BaseModel):
    name: str
    stories: int
    latest_story_on: date | None
    sectors: dict[str, int]


class CheckOut(BaseModel):
    dataset: str
    name: str
    status: Literal["pass", "warn", "fail"]
    detail: str


class SourceOut(BaseModel):
    key: str
    title: str
    url: str
    sha256: str
    bytes: int
    fetched_at: datetime


class Quality(BaseModel):
    loaded_at: datetime | None
    snapshot_sha256: str | None
    summary: dict[str, int]
    checks: list[CheckOut]
    sources: list[SourceOut]
