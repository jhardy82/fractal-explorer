#!/usr/bin/env python3
"""scripts/dashboard.py — refreshable CI + DoD status dashboard.

Queries the latest GitHub Actions run on main via `gh` CLI and renders
a live table of job statuses and DoD gate verdicts.

Usage:
    uv run python scripts/dashboard.py           # one-shot
    uv run python scripts/dashboard.py --watch   # refresh every 30s
    uv run python scripts/dashboard.py --watch 60
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import UTC, datetime

from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

REPO = "jhardy82/fractal-explorer"
BRANCH = "main"

# DoD definitions: id, description, gate, the CI job whose success proves it
DODS = [
    ("A.3", "Mutation kill-rate ≥70%", "mutation"),
    ("C.2", "Property tests (Hypothesis) pass", "property"),
    ("C.3", "3D perf ≤0.500s CI / 30 frames @ 480×360", "integration-3d"),
    # v0.3.0
    ("D.1", "Numba ≥60fps @ 800×600 (escape-time)", "perf-numba"),
    ("D.2", "Wheel builds cleanly (hatch)", "build"),
]

# Friendly display order for CI jobs
JOB_ORDER = [
    "lint",
    "unit (3.11)", "unit (3.12)", "unit (3.13)",
    "integration", "integration-3d",
    "regression", "property", "mutation",
    "perf-numba", "build",
]


def _gh(*args: str) -> dict | list | str:
    """Run a gh CLI command and return parsed JSON (or raw string)."""
    cmd = ["gh", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return {}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return result.stdout.strip()


def fetch_latest_run() -> dict:
    """Return metadata for the most recent run on BRANCH."""
    runs = _gh(
        "run", "list",
        "--repo", REPO,
        "--branch", BRANCH,
        "--limit", "1",
        "--json", "databaseId,conclusion,status,headSha,headBranch,displayTitle,createdAt",
    )
    if isinstance(runs, list) and runs:
        return runs[0]
    return {}


def fetch_jobs(run_id: int) -> list[dict]:
    """Return job list for a given run ID."""
    data = _gh("run", "view", str(run_id), "--repo", REPO, "--json", "jobs")
    if isinstance(data, dict):
        return data.get("jobs", [])
    return []


def fetch_kill_rate(run_id: int) -> str | None:
    """Parse mutation kill rate from the run log."""
    log = _gh("run", "view", str(run_id), "--repo", REPO, "--log")
    if not isinstance(log, str):
        return None
    m = re.search(r"Mutation kill rate:\s*(\d+)\s*killed\s*/\s*(\d+)\s*total.*?=\s*(\d+)%", log)
    if m:
        return f"{m.group(1)}/{m.group(2)} = {m.group(3)}%"
    return None


def _status_cell(conclusion: str | None, status: str | None) -> Text:
    if status in ("queued", "in_progress", "waiting", "requested"):
        return Text("⏳ running", style="yellow")
    if conclusion == "success":
        return Text("✓ pass", style="green bold")
    if conclusion in ("failure", "timed_out"):
        return Text("✗ fail", style="red bold")
    if conclusion == "skipped":
        return Text("– skip", style="dim")
    if conclusion == "cancelled":
        return Text("⊘ cancel", style="dim red")
    return Text("? unknown", style="dim")


def build_jobs_table(jobs: list[dict]) -> Table:
    t = Table(title="CI Jobs", show_lines=False, expand=True)
    t.add_column("Job", style="bold", min_width=22)
    t.add_column("Status", min_width=12)
    t.add_column("Duration", min_width=8, justify="right", style="dim")

    job_map: dict[str, dict] = {j["name"]: j for j in jobs}

    for name in JOB_ORDER:
        j = job_map.get(name)
        if j is None:
            t.add_row(name, Text("– not run", style="dim"), "")
            continue
        cell = _status_cell(j.get("conclusion"), j.get("status"))
        # duration from startedAt / completedAt (may be None while running)
        duration = ""
        started = j.get("startedAt")
        completed = j.get("completedAt")
        if started and completed and j.get("conclusion"):
            try:
                s = datetime.fromisoformat(started.replace("Z", "+00:00"))
                c = datetime.fromisoformat(completed.replace("Z", "+00:00"))
                secs = int((c - s).total_seconds())
                if 0 < secs < 86400:   # guard against Go zero-time completedAt
                    duration = f"{secs // 60}m{secs % 60:02d}s"
            except Exception:
                pass
        t.add_row(name, cell, duration)

    return t


def build_dod_table(jobs: list[dict], kill_rate: str | None) -> Table:
    t = Table(title="DoD Status", show_lines=False, expand=True)
    t.add_column("ID", style="bold cyan", min_width=5)
    t.add_column("Description", min_width=34)
    t.add_column("Gate", min_width=10)
    t.add_column("Evidence", style="dim", min_width=18)

    job_map: dict[str, dict] = {j["name"]: j for j in jobs}

    for dod_id, desc, ci_job in DODS:
        j = job_map.get(ci_job)
        if j is None:
            gate = Text("– not run", style="dim")
            evidence = "job missing"
        else:
            conclusion = j.get("conclusion")
            status = j.get("status")
            gate = _status_cell(conclusion, status)
            # enrich evidence for mutation job
            if ci_job == "mutation" and conclusion == "success" and kill_rate:
                evidence = kill_rate
            elif ci_job == "mutation" and conclusion == "success":
                evidence = "log unavailable"
            else:
                evidence = f"{ci_job}: {conclusion or status or '?'}"
        t.add_row(dod_id, desc, gate, evidence)

    return t


def render(console: Console) -> None:
    console.clear()

    run = fetch_latest_run()
    if not run:
        console.print("[red]Could not reach GitHub — is `gh` authenticated?[/]")
        return

    run_id: int = run.get("databaseId") or 0
    if not run_id:
        console.print("[red]No run ID returned — check gh auth status.[/]")
        return
    sha = (run.get("headSha") or "")[:7]
    title = run.get("displayTitle", "")[:60]
    overall = run.get("conclusion") or run.get("status") or "?"
    overall_col = "green bold" if overall == "success" else ("red bold" if overall == "failure" else "yellow")

    header = Text.assemble(
        ("fractal-explorer", "bold cyan"),
        " · CI Dashboard · ",
        (BRANCH, "bold"),
        f"   [{datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}]",
    )
    console.print(Panel(header, expand=True))

    meta = (
        f"Run [bold]#{run_id}[/] · commit [bold]{sha}[/] · "
        f"[{overall_col}]{overall}[/{overall_col}]  — {title}"
    )
    console.print(meta)
    console.print()

    jobs = fetch_jobs(run_id)
    kill_rate = None
    if any(j.get("name") == "mutation" and j.get("conclusion") == "success" for j in jobs):
        kill_rate = fetch_kill_rate(run_id)

    console.print(Columns([build_jobs_table(jobs), build_dod_table(jobs, kill_rate)], expand=True))
    console.print()
    console.print(f"[dim]Run URL: https://github.com/{REPO}/actions/runs/{run_id}[/]")


def main() -> None:
    parser = argparse.ArgumentParser(description="fractal-explorer CI status dashboard")
    parser.add_argument(
        "--watch", nargs="?", const=30, type=int, metavar="SECONDS",
        help="Auto-refresh every N seconds (default 30)",
    )
    args = parser.parse_args()

    console = Console()

    if args.watch is None:
        render(console)
        return

    console.print(f"[dim]Watching — refreshing every {args.watch}s. Ctrl-C to quit.[/]")
    try:
        while True:
            render(console)
            console.print(f"[dim]Next refresh in {args.watch}s…[/]")
            time.sleep(args.watch)
    except KeyboardInterrupt:
        console.print("\n[dim]Stopped.[/]")
        sys.exit(0)


if __name__ == "__main__":
    main()
