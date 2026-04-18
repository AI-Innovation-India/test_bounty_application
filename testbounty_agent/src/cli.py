"""
TestBounty CLI — Run suites and scenarios from the command line.

Usage in CI/CD pipelines:
    python -m testbounty_agent.cli run-suite "Regression" --wait --fail-on-failure
    python -m testbounty_agent.cli run-suite --id <suite_id> --env staging
    python -m testbounty_agent.cli status <run_id>
    python -m testbounty_agent.cli export-junit <run_id> -o results.xml

Exit codes (standard for CI gates):
    0  — all scenarios passed
    1  — one or more scenarios failed
    2  — setup / connection error
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Optional

import urllib.request
import urllib.error


# ── HTTP helpers (no extra deps) ──────────────────────────────────────────────

def _api(base: str, path: str, method: str = "GET", body: dict = None) -> dict:
    url = base.rstrip("/") + path
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error {e.code}: {e.read().decode()}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Cannot reach TestBounty at {base} — is the backend running? ({e.reason})")


def _get_raw(base: str, path: str) -> str:
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Accept": "application/xml, text/xml"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except Exception as e:
        raise SystemExit(f"Failed to fetch {path}: {e}")


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_list_suites(args):
    suites = _api(args.api, "/api/test-suites")
    if not suites:
        print("No test suites found.")
        return
    print(f"{'ID':<38}  {'Name':<30}  {'Type':<12}  {'Scenarios':<10}  {'Last Run'}")
    print("-" * 110)
    for s in suites:
        count = len(s.get("scenario_refs") or [])
        last = (s.get("last_run") or "never")[:19]
        print(f"{s['id']:<38}  {s['name']:<30}  {s.get('suite_type','?'):<12}  {count:<10}  {last}")


def cmd_run_suite(args):
    # Resolve suite by name or ID
    suites = _api(args.api, "/api/test-suites")
    suite = None
    if args.id:
        suite = next((s for s in suites if s["id"] == args.id), None)
    elif args.name:
        suite = next((s for s in suites if s["name"].lower() == args.name.lower()), None)

    if not suite:
        identifier = args.id or args.name
        print(f"Suite not found: {identifier}", file=sys.stderr)
        print("Available suites:")
        for s in suites:
            print(f"  {s['id']}  {s['name']}")
        sys.exit(2)

    print(f"Triggering suite: {suite['name']} ({suite.get('suite_type','?')})")
    print(f"  Scenarios: {len(suite.get('scenario_refs') or [])}")

    result = _api(args.api, f"/api/test-suites/{suite['id']}/run", method="POST")
    run_ids = result.get("run_ids", [])
    total_scenarios = result.get("scenarios_count", 0)
    print(f"  Run IDs: {run_ids}")
    print(f"  Scenarios queued: {total_scenarios}")

    if not args.wait:
        print(f"\nRun started. Check status:")
        for rid in run_ids:
            print(f"  python -m testbounty_agent.cli status {rid} --api {args.api}")
        return

    # ── Poll until complete ───────────────────────────────────────────────────
    print("\nWaiting for results", end="", flush=True)
    overall_passed = 0
    overall_failed = 0
    overall_total = 0

    for run_id in run_ids:
        deadline = time.time() + args.timeout
        while time.time() < deadline:
            run = _api(args.api, f"/api/run/{run_id}")
            status = run.get("status")
            if status in ("completed", "failed"):
                break
            print(".", end="", flush=True)
            time.sleep(args.poll)
        else:
            print(f"\nTimeout waiting for run {run_id}", file=sys.stderr)
            sys.exit(2)

        results = run.get("results") or {}
        passed = sum(1 for r in results.values() if r.get("status") == "passed")
        failed = sum(1 for r in results.values() if r.get("status") == "failed")
        total = len(results)
        overall_passed += passed
        overall_failed += failed
        overall_total += total

    print()  # newline after dots

    # ── Print summary ─────────────────────────────────────────────────────────
    pct = (overall_passed / overall_total * 100) if overall_total else 0
    print(f"\n{'='*60}")
    print(f"  Suite:   {suite['name']}")
    print(f"  Result:  {'PASSED' if overall_failed == 0 else 'FAILED'}")
    print(f"  Passed:  {overall_passed}/{overall_total} ({pct:.0f}%)")
    if overall_failed:
        print(f"  Failed:  {overall_failed}")
    print(f"{'='*60}")

    # Export JUnit if requested
    if args.junit:
        for run_id in run_ids:
            xml = _get_raw(args.api, f"/api/run/{run_id}/junit.xml")
            out = args.junit if len(run_ids) == 1 else args.junit.replace(".xml", f"_{run_id[:8]}.xml")
            with open(out, "w", encoding="utf-8") as f:
                f.write(xml)
            print(f"JUnit report: {out}")

    if args.fail_on_failure and overall_failed > 0:
        sys.exit(1)


def cmd_status(args):
    run = _api(args.api, f"/api/run/{args.run_id}")
    print(f"Run: {run['id']}")
    print(f"Status: {run['status']}")
    results = run.get("results") or {}
    if results:
        passed = sum(1 for r in results.values() if r.get("status") == "passed")
        failed = sum(1 for r in results.values() if r.get("status") == "failed")
        print(f"Passed: {passed}/{len(results)}  Failed: {failed}")
        if failed:
            print("\nFailed scenarios:")
            for sid, r in results.items():
                if r.get("status") == "failed":
                    print(f"  [{sid}] {r.get('name', sid)}: {r.get('error', '')[:120]}")


def cmd_export_junit(args):
    xml = _get_raw(args.api, f"/api/run/{args.run_id}/junit.xml")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(xml)
        print(f"Saved: {args.output}")
    else:
        print(xml)


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="testbounty",
        description="TestBounty CLI — run AI test suites from CI/CD pipelines",
    )
    parser.add_argument("--api", default="http://localhost:8000", help="TestBounty API base URL")

    sub = parser.add_subparsers(dest="command", required=True)

    # list-suites
    sub.add_parser("list-suites", help="List all test suites")

    # run-suite
    rs = sub.add_parser("run-suite", help="Run a test suite")
    rs_target = rs.add_mutually_exclusive_group(required=True)
    rs_target.add_argument("name", nargs="?", help="Suite name (quoted)")
    rs_target.add_argument("--id", help="Suite ID")
    rs.add_argument("--wait", action="store_true", default=True, help="Wait for results (default: true)")
    rs.add_argument("--no-wait", dest="wait", action="store_false")
    rs.add_argument("--fail-on-failure", action="store_true", default=True, help="Exit 1 if any test fails (default: true)")
    rs.add_argument("--timeout", type=int, default=600, help="Max seconds to wait (default: 600)")
    rs.add_argument("--poll", type=int, default=5, help="Poll interval in seconds (default: 5)")
    rs.add_argument("--junit", metavar="FILE", help="Export JUnit XML to file")

    # status
    st = sub.add_parser("status", help="Check run status")
    st.add_argument("run_id", help="Run ID")

    # export-junit
    ej = sub.add_parser("export-junit", help="Export run results as JUnit XML")
    ej.add_argument("run_id", help="Run ID")
    ej.add_argument("-o", "--output", help="Output file (default: stdout)")

    args = parser.parse_args()

    if args.command == "list-suites":
        cmd_list_suites(args)
    elif args.command == "run-suite":
        cmd_run_suite(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "export-junit":
        cmd_export_junit(args)


if __name__ == "__main__":
    main()
