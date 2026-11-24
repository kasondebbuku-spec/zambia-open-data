"""Database tables and the session factory.

The API only ever reads. The tables are filled by ``zod load``, which replaces their
contents from the snapshot in a single transaction, so readers see either the old
dataset or the new one and never a half-loaded mix.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, datetime
from functools import lru_cache

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from .settings import settings

STAGES = ("budget", "prior", "projection")


class Base(DeclarativeBase):
    pass


class SourceRow(Base):
    """A file the data came from, with its SHA-256 fingerprint."""

    __tablename__ = "source"

    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    file: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    bytes: Mapped[int] = mapped_column(BigInteger)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BudgetBook(Base):
    __tablename__ = "budget_book"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    revenue_total_zmw: Mapped[int] = mapped_column(BigInteger)
    spending_total_zmw: Mapped[int] = mapped_column(BigInteger)
    source_key: Mapped[str] = mapped_column(ForeignKey("source.key"))


class RevenueLine(Base):
    __tablename__ = "revenue_line"
    __table_args__ = (CheckConstraint(f"stage IN {STAGES}", name="revenue_stage"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_year: Mapped[int] = mapped_column(ForeignKey("budget_book.year", ondelete="CASCADE"), index=True)
    line: Mapped[int] = mapped_column(Integer)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(12))
    group_code: Mapped[str] = mapped_column(String(4))
    group_name: Mapped[str] = mapped_column(Text)
    item_code: Mapped[str | None] = mapped_column(String(6))
    item_name: Mapped[str] = mapped_column(Text)
    amount_zmw: Mapped[int] = mapped_column(BigInteger)


class SpendingLine(Base):
    __tablename__ = "spending_line"
    __table_args__ = (
        CheckConstraint(f"stage IN {STAGES}", name="spending_stage"),
        CheckConstraint("basis IN ('economic', 'programme')", name="spending_basis"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_year: Mapped[int] = mapped_column(ForeignKey("budget_book.year", ondelete="CASCADE"), index=True)
    fiscal_year: Mapped[int] = mapped_column(Integer)
    stage: Mapped[str] = mapped_column(String(12))
    basis: Mapped[str] = mapped_column(String(12))
    code: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(Text)
    amount_zmw: Mapped[int] = mapped_column(BigInteger)


class CdfStory(Base):
    __tablename__ = "cdf_story"

    post_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    published_on: Mapped[date] = mapped_column(Date, index=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    constituencies: Mapped[list[str]] = mapped_column(ARRAY(Text))
    sectors: Mapped[list[str]] = mapped_column(ARRAY(Text))
    status: Mapped[str | None] = mapped_column(String(24))
    largest_amount_zmw: Mapped[int | None] = mapped_column(BigInteger)
    completion_pct: Mapped[int | None] = mapped_column(Integer)


class QualityCheck(Base):
    __tablename__ = "quality_check"
    __table_args__ = (CheckConstraint("status IN ('pass', 'warn', 'fail')", name="check_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(4))
    detail: Mapped[str] = mapped_column(Text)


class LoadRun(Base):
    """One row per ``zod load``, so the API can say how fresh the data is."""

    __tablename__ = "load_run"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    snapshot_sha256: Mapped[str] = mapped_column(String(64))
    rows: Mapped[int] = mapped_column(Integer)


@lru_cache
def engine() -> Engine:
    return create_engine(settings().database_url, pool_pre_ping=True)


@lru_cache
def session_factory() -> sessionmaker[Session]:
    return sessionmaker(engine(), expire_on_commit=False)


def get_session() -> Iterator[Session]:
    with session_factory()() as session:
        yield session
