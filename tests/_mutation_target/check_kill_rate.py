#!/usr/bin/env python3
"""Compute mutation kill rate from mutmut run log output.

mutmut 3.x stores its SQLite cache in the platformdirs user-cache directory
(not the CWD), so we avoid looking for the DB entirely. Instead we parse:
  - mutmut_run.log   : progress lines emitted by `mutmut run`, last line has
                       the final totals in the form  "X/TOTAL  🎉 K ... 🙁 S"
  - mutmut_results.txt (fallback): count of survived-mutant lines
"""
import os
import re
import sys


def parse_run_log(path: str) -> tuple[int, int] | None:
    """Return (killed, total) from the last summary line of mutmut_run.log."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            content = f.read()
    except FileNotFoundError:
        return None

    # Progress lines look like:  "⠹ 130/130  🎉 112 🫥 0  ⏰ 0  🤔 0  🙁 18  🔇 0  🧙 0"
    # We want the LAST line that has the N/N pattern (final tally).
    total_matches = re.findall(r"\d+/(\d+)", content)
    killed_matches = re.findall(r"\U0001f389\s+(\d+)", content)  # 🎉

    if not total_matches or not killed_matches:
        return None

    total = int(total_matches[-1])
    killed = int(killed_matches[-1])
    return killed, total


def count_survived(path: str) -> int:
    """Count lines containing 'survived' in mutmut_results.txt."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if "survived" in line)
    except FileNotFoundError:
        return 0


result = parse_run_log("mutmut_run.log")

if result is None:
    # Fallback: derive totals from results file (survived only — killed unknown)
    survived = count_survived("../../artifacts/mutmut_results.txt")
    print(f"::warning::Could not parse mutmut_run.log; survived={survived} but total unknown")
    print("::error::mutmut_run.log missing or unparseable — cannot compute kill rate")
    sys.exit(1)

killed, total = result

if total == 0:
    print("::error::No mutations recorded in mutmut_run.log.")
    sys.exit(1)

survived = total - killed
pct = killed * 100 // total
print(f"Mutation kill rate: {killed} killed / {total} total ({survived} survived) = {pct}%")

with open(os.environ["GITHUB_ENV"], "a") as f:
    f.write(f"MUTATION_KILL_RATE={pct}\n")

if pct < 70:
    print(f"::error::Kill rate {pct}% below 70% gate")
    sys.exit(1)
elif pct < 80:
    print(f"::warning::Kill rate {pct}% in acceptable band (target ≥80%)")
