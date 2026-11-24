from __future__ import annotations

from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_session
from ..settings import settings
from .routes import router

DESCRIPTION = """
Lusaka City Council's approved budgets and Constituency Development Fund (CDF) projects,
taken from the council's own published documents and checked line by line.

* **Budgets**: revenue and spending for each approved budget book, with year-on-year changes.
* **CDF**: the council's news stories about CDF projects, by constituency and sector.
* **Quality**: every check run on the data, and fingerprints of the source files.

Amounts are whole Zambian kwacha (ZMW). Read-only, no key needed.
"""

app = FastAPI(
    title="Zambia Open Data API",
    version="0.1.0",
    description=DESCRIPTION,
    license_info={"name": "Code MIT; data is public information published by Lusaka City Council"},
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings().cors_origins.split(",") if o.strip()],
    allow_methods=["GET"],
)
app.include_router(router)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse("/docs")


@app.get("/health", tags=["about the data"])
def health(db: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
