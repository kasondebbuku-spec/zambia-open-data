"""``zod`` command line: fetch -> build -> load.

zod fetch    download the budget books and news posts from lcc.gov.zm into data/raw
zod build    parse and check them, then write data/snapshot (stops if a check fails)
zod load     put data/snapshot into PostgreSQL in one transaction (skipped if already loaded)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

RAW = Path("data/raw")
SNAPSHOT = Path("data/snapshot")


def main(argv: list[str] | None = None) -> int:
    # Council names and the checks' wording use non-ASCII characters; Windows consoles default to cp1252.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        prog="zod", description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="download the raw sources").add_argument("--raw", type=Path, default=RAW)
    build_cmd = sub.add_parser("build", help="parse, check and write the snapshot")
    build_cmd.add_argument("--raw", type=Path, default=RAW)
    build_cmd.add_argument("--out", type=Path, default=SNAPSHOT)
    load_cmd = sub.add_parser("load", help="load the snapshot into the database")
    load_cmd.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    load_cmd.add_argument("--force", action="store_true", help="load even if this snapshot is already loaded")
    args = parser.parse_args(argv)

    if args.command == "fetch":
        from .pipeline.fetch import fetch_all

        for s in fetch_all(args.raw):
            print(f"{s.key:<12} {s.bytes:>10,} bytes  {s.sha256[:12]}  {s.url}")
        return 0

    if args.command == "build":
        from .pipeline.snapshot import ChecksFailed, build

        try:
            counts = build(args.raw, args.out)
        except ChecksFailed as e:
            print("Snapshot not written. These checks failed:", file=sys.stderr)
            for c in e.failed:
                print(f"  {c.dataset}: {c.name}: {c.detail}", file=sys.stderr)
            return 1
        for name, n in counts.items():
            print(f"{name:<18} {n:>5} rows")
        return 0

    from .db import session_factory
    from .load import is_loaded, load

    # The API container runs this on every start; skip the work when nothing changed.
    with session_factory()() as session:
        if not args.force and is_loaded(session, args.snapshot):
            print(f"{args.snapshot} is already loaded; nothing to do (use --force to reload)")
            return 0
    with session_factory()() as session:
        print(f"Loaded {load(session, args.snapshot):,} rows from {args.snapshot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
