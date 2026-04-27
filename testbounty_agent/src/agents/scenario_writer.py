"""
ScenarioWriter — saves autonomously generated scenarios into the plans system
so they can be re-run via the existing test runner.

Creates:
  • An entry in test_plans.json  (plan_id = "autonomous_<session_id[:8]>")
  • An optional entry in test_suites.json
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

PLANS_FILE      = Path("test_plans.json")
SUITES_FILE     = Path("test_suites.json")


def _load_json(path: Path) -> Dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_json(path: Path, data: Dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def save_scenarios_as_plan(
    session_id: str,
    base_url: str,
    scenarios: List[Dict],
    suite_name: Optional[str] = None,
) -> Dict:
    """
    Persist generated scenarios and return
    {"plan_id": str, "suite_id": str | None}.
    """
    plan_id = f"autonomous_{session_id[:8]}"

    # ── 1. Write plan into test_plans.json ────────────────────────────────────
    plans = _load_json(PLANS_FILE)
    plans[plan_id] = {
        "id":            plan_id,
        "url":           base_url,
        "status":        "complete",
        "source":        "autonomous",
        "session_id":    session_id,
        "created_at":    datetime.now().isoformat(),
        "app_map":       None,
        "app_knowledge": None,
        "test_plan": {
            "scenarios":     scenarios,
            "generated_at":  datetime.now().isoformat(),
            "total":         len(scenarios),
        },
    }
    _save_json(PLANS_FILE, plans)

    # ── 2. Create a Test Suite (optional) ─────────────────────────────────────
    suite_id: Optional[str] = None
    if suite_name:
        suite_id = str(uuid.uuid4())
        suites   = _load_json(SUITES_FILE)
        suites[suite_id] = {
            "id":          suite_id,
            "name":        suite_name,
            "description": f"Auto-generated — {base_url}",
            "plan_id":     plan_id,
            "tests":       [s["id"] for s in scenarios],
            "source":      "autonomous",
            "session_id":  session_id,
            "created_at":  datetime.now().isoformat(),
            "last_run":    None,
            "status":      "idle",
        }
        _save_json(SUITES_FILE, suites)

    return {"plan_id": plan_id, "suite_id": suite_id}
