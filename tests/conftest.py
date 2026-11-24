from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest


def read_env(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    pairs = (
        line.split("=", 1)
        for line in path.read_text().splitlines()
        if "=" in line and not line.startswith("#")
    )
    return {k.strip(): v.strip().strip('"') for k, v in pairs}


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "snapshot"

# Point the app at the test database before anything imports the settings.
_test_url = os.environ.get("TEST_DATABASE_URL") or read_env(ROOT / ".env").get("TEST_DATABASE_URL")
if _test_url:
    os.environ["DATABASE_URL"] = _test_url
HAS_DB = bool(_test_url)

needs_db = pytest.mark.skipif(not HAS_DB, reason="TEST_DATABASE_URL is not set")


@pytest.fixture(scope="session")
def migrated() -> Iterator[None]:
    if not HAS_DB:
        pytest.skip("TEST_DATABASE_URL is not set")
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import text

    from zod.db import engine

    # The tests wipe this database, so refuse anything that isn't clearly a test database.
    if not engine().url.database or not engine().url.database.endswith("_test"):
        pytest.exit(f"Refusing to wipe {engine().url.database!r}: test database names must end in _test")
    with engine().begin() as conn:  # start from an empty test database every run
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
    cfg = Config(str(ROOT / "alembic.ini"))
    # Prove the migrations run both ways.
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(scope="session")
def loaded(migrated: None) -> None:
    from zod.db import session_factory
    from zod.load import load

    with session_factory()() as session:
        load(session, SNAPSHOT)


@pytest.fixture
def client(loaded: None):  # type: ignore[no-untyped-def]
    from fastapi.testclient import TestClient

    from zod.api.main import app

    with TestClient(app) as c:
        yield c
