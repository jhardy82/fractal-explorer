#!/usr/bin/env python3
"""Query mutmut's SQLite cache to compute an accurate mutation kill rate."""
import glob
import os
import sqlite3
import sys


def query_db():
    candidates = [".mutmut-cache"] + glob.glob("*.db") + glob.glob("*.sqlite") + glob.glob("*.cache")
    for path in candidates:
        try:
            db = sqlite3.connect(path)
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            for t in tables:
                cols = [r[1] for r in db.execute(f'PRAGMA table_info("{t}")').fetchall()]
                if "status" in cols:
                    rows = dict(db.execute(f'SELECT status, COUNT(*) FROM "{t}" GROUP BY status').fetchall())
                    killed = rows.get("killed", 0)
                    survived = rows.get("survived", 0)
                    if killed + survived > 0:
                        return killed, survived
        except Exception:
            pass
    return None


result = query_db()
if result is None:
    print("::error::mutmut database not found — did mutmut run succeed?")
    sys.exit(1)

killed, survived = result
total = killed + survived
if total == 0:
    print("::error::No mutations recorded in database.")
    sys.exit(1)

pct = killed * 100 // total
print(f"Mutation kill rate: {killed} killed / {total} total = {pct}%")

with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write(f"MUTATION_KILL_RATE={pct}\n")

if pct < 70:
    print(f"::error::Kill rate {pct}% below 70% gate")
    sys.exit(1)
elif pct < 80:
    print(f"::warning::Kill rate {pct}% in acceptable band (target ≥80%)")
