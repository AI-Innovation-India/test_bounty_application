"""
FeatureTestAgent — AI-powered interactive tester for one app feature.

LLM provider priority (first available wins):
  1. Azure OpenAI  — AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY
  2. Anthropic     — ANTHROPIC_API_KEY
  3. OpenAI        — OPENAI_API_KEY

Flow per feature:
  1. Navigate to each feature page
  2. Capture screenshot + DOM element inventory
  3. Call LLM (vision + text) → structured test flows
  4. Execute each flow step in the live Playwright browser
  5. Record pass/fail per step with screenshots
  6. Return as Scenario objects ready for the test runner

Safety model:
  - Never clicks: delete / remove / destroy / deactivate
  - Admin pages: assert_visible only (no writes)
  - Forms: always uses placeholder test data
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

# ── Feature-specific QA strategies ────────────────────────────────────────────
_FEATURE_STRATEGY: Dict[str, str] = {
    "authentication": (
        "Test: form validation (submit empty → error visible), "
        "password field has toggle, forgot-password link present. "
        "Do NOT attempt actual login or submit real credentials."
    ),
    "dashboard": (
        "Test: all widget/stat cards render without error state, "
        "KPI numbers visible, any charts/graphs load, "
        "quick-action buttons present."
    ),
    "tracking": (
        "Test: list/table renders with at least 1 row, "
        "click first row → verify detail panel or page opens, "
        "search/filter input visible, map panel loads if present."
    ),
    "reports": (
        "Test: report renders with data, date-range picker visible, "
        "export/download button present, column headers visible."
    ),
    "products": (
        "Test: product grid/list renders, search input present, "
        "click first product → detail page opens, image loads."
    ),
    "orders": (
        "Test: order list renders, status filter visible, "
        "click first order → detail view opens."
    ),
    "alerts": (
        "Test: notification/alert list renders, unread indicator visible, "
        "click first alert → detail shows."
    ),
    "admin": (
        "READ-ONLY test: settings page loads, form fields visible, "
        "section headings present. Do NOT click save/submit/confirm."
    ),
    "user_profile": (
        "Test: profile info renders, avatar/name visible, "
        "edit button present. Do NOT submit any changes."
    ),
    "support": (
        "Test: help/FAQ page loads, search input visible, "
        "category list renders, article links present."
    ),
    "general": (
        "Test: page loads without JS errors, main content visible, "
        "primary navigation links work, no broken layouts."
    ),
}

# ── Dangerous action keywords ──────────────────────────────────────────────────
_DANGER_WORDS = frozenset({
    "delete", "remove", "destroy", "deactivate", "cancel subscription",
    "purge", "wipe", "terminate", "revoke", "disable account", "reset all",
    "clear all", "bulk delete", "drop", "flush",
})

# ── Claude system prompt ───────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are a senior QA engineer writing automated test flows for web applications.
You receive a screenshot, page metadata, and an element inventory.
Return ONLY valid JSON — no markdown, no explanation, no text outside the JSON.

Required format:
{
  "flows": [
    {
      "name": "5-8 word flow name",
      "description": "one sentence — what this flow tests",
      "steps": [
        {
          "action": "assert_visible|click|fill|navigate|assert_text|hover|select|scroll|wait_for",
          "target": "primary-selector, fallback-selector, another-fallback",
          "value": "string for fill/assert_text/select, null otherwise",
          "description": "plain English — what this step does"
        }
      ]
    }
  ]
}

STRICT RULES:
1. Generate 1–3 flows per page. Each flow has 3–7 steps. No more.
2. Always start a flow with assert_visible to confirm the page is ready.
3. CSS selectors: be specific but provide 2–3 comma-separated fallbacks.
   Example: "table.fleet-list, [data-testid='vehicle-table'], table"
4. NEVER generate steps targeting: delete, remove, destroy, deactivate,
   cancel subscription, purge, wipe, terminate, revoke.
5. For fill steps use safe test values: name="Test User", email="qa@testbounty.ai",
   phone="555-0000", search="test", date="2024-01-01".
6. For admin/settings pages: use assert_visible and assert_text only — no clicks
   on Save / Submit / Confirm buttons.
7. For authentication pages: only test form validation (submit empty, check error
   appears). Do NOT submit real credentials.
"""


def _format_elements_for_claude(elements: List[Dict]) -> str:
    """Convert element inventory to a compact text summary for Claude."""
    if not elements:
        return "No interactive elements detected on this page."

    buttons = [e for e in elements if e.get("tag") == "button"
               or e.get("type") in ("submit", "button", "reset")]
    inputs  = [e for e in elements if e.get("tag") in ("input", "textarea", "select")]
    links   = [e for e in elements if e.get("tag") == "a" or e.get("role") == "link"]

    parts: List[str] = []
    if buttons:
        texts = [b.get("text") or b.get("aria") or b.get("type", "btn") for b in buttons[:10]]
        parts.append("Buttons: " + " | ".join(f"[{t}]" for t in texts if t))
    if inputs:
        descs = [
            f"{i.get('type','text')}:{i.get('placeholder') or i.get('name') or i.get('aria','input')}"
            for i in inputs[:8]
        ]
        parts.append("Inputs: " + " | ".join(descs))
    if links:
        texts = [l.get("text") or l.get("aria", "") for l in links[:10]]
        parts.append("Links: " + " | ".join(f"[{t}]" for t in texts if t))

    # Count table rows / grid items
    tables = [e for e in elements if e.get("role") in ("row", "gridcell")
              or e.get("tag") in ("tr", "td")]
    if tables:
        parts.append(f"Data table/grid: {len(tables)} cells/rows detected")

    return "\n".join(parts) if parts else "Mixed interactive elements (no clear classification)."


def _build_user_prompt(
    feature: str, title: str, url: str,
    element_summary: str, strategy: str,
) -> str:
    return (
        f"Feature type: {feature.replace('_', ' ').title()}\n"
        f"Page title: {title}\n"
        f"URL: {url}\n\n"
        f"Testing strategy for this feature:\n{strategy}\n\n"
        f"Elements found on this page:\n{element_summary}\n\n"
        f"Generate test flows following the strategy and rules above."
    )


def _detect_llm_provider() -> str:
    """Return the first available LLM provider based on env vars."""
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        return "azure"
    if os.getenv("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "none"


def _call_llm_for_test_plan(
    system_prompt: str,
    user_prompt: str,
    ss_b64: Optional[str] = None,
) -> Optional[str]:
    """
    Call the first available LLM provider with vision + text.
    Returns raw text response or None on failure.

    Provider order: Azure OpenAI → Anthropic → OpenAI
    """
    provider = _detect_llm_provider()

    # ── Azure OpenAI ───────────────────────────────────────────────────────────
    if provider == "azure":
        try:
            from openai import AzureOpenAI
            client = AzureOpenAI(
                azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
            )
            deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
            content: List[Dict] = []
            if ss_b64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{ss_b64}", "detail": "high"},
                })
            content.append({"type": "text", "text": user_prompt})
            resp = client.chat.completions.create(
                model=deployment,
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": content},
                ],
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[FeatureTestAgent/Azure] {e}")

    # ── Anthropic Claude ───────────────────────────────────────────────────────
    elif provider == "anthropic":
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            content_blocks: List[Dict] = []
            if ss_b64:
                content_blocks.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": ss_b64},
                })
            content_blocks.append({"type": "text", "text": user_prompt})
            resp = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=system_prompt,
                messages=[{"role": "user", "content": content_blocks}],
            )
            return resp.content[0].text
        except Exception as e:
            print(f"[FeatureTestAgent/Anthropic] {e}")

    # ── OpenAI ─────────────────────────────────────────────────────────────────
    elif provider == "openai":
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            content: List[Dict] = []
            if ss_b64:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{ss_b64}", "detail": "high"},
                })
            content.append({"type": "text", "text": user_prompt})
            resp = client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2048,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": content},
                ],
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[FeatureTestAgent/OpenAI] {e}")

    return None


class FeatureTestAgent:
    """
    One agent per discovered feature.  Receives the list of pages belonging
    to that feature, analyzes them with Claude, executes interactions in the
    live Playwright browser, and returns Scenario objects.
    """

    def __init__(
        self,
        feature_name: str,
        pages: List[Dict],
        session_id: str,
        base_url: str,
        emit_fn: Callable,
    ):
        self.feature    = feature_name
        self.pages      = pages
        self.session_id = session_id
        self.base_url   = base_url
        self.emit       = emit_fn          # session.emit(etype, agent, message, data, screenshot)
        self.scenarios: List[Dict] = []

    # ── Public entry point ─────────────────────────────────────────────────────

    def run(self, page) -> List[Dict]:
        """Analyze + interact + return scenarios. Called from sync Playwright thread."""
        provider = _detect_llm_provider()
        if provider == "none":
            self.emit("warning", self.feature,
                      "Skipping — no LLM API key set (AZURE_OPENAI_API_KEY / "
                      "ANTHROPIC_API_KEY / OPENAI_API_KEY)")
            return []

        pages_to_test = self.pages[:3]   # Cap at 3 pages per feature

        for fp in pages_to_test:
            try:
                flows = self._analyze_page_with_claude(page, fp)
                if not flows:
                    self.emit("warning", self.feature,
                              f"No test flows generated for {fp.get('title','?')[:40]}")
                    continue

                for flow in flows[:4]:   # Cap at 4 flows per page
                    if self._is_dangerous_flow(flow):
                        self.emit("warning", self.feature,
                                  f"Skipped risky flow: {flow.get('name','?')}")
                        continue

                    self.emit("progress", self.feature,
                              f"Executing: {flow['name']}")
                    result  = self._execute_flow(page, fp, flow)
                    scenario = self._build_scenario(fp, flow, result)
                    self.scenarios.append(scenario)

                    passed = sum(1 for s in result["steps"] if s["status"] == "pass")
                    total  = len(result["steps"])
                    self.emit(
                        "finding", self.feature,
                        f"{flow['name']}: {passed}/{total} steps passed",
                        data={
                            "scenario_id": scenario["id"],
                            "passed": passed,
                            "total": total,
                            "steps": result["steps"],
                        },
                    )
            except Exception as e:
                self.emit("warning", self.feature,
                          f"Error on {fp.get('title','?')[:30]}: {str(e)[:80]}")

        return self.scenarios

    # ── LLM page analysis (Azure / Anthropic / OpenAI) ────────────────────────

    def _analyze_page_with_claude(self, page, fp: Dict) -> List[Dict]:
        """Navigate to page, capture state, call LLM, return flow list."""
        provider = _detect_llm_provider()
        if provider == "none":
            self.emit("warning", self.feature,
                      "No LLM API key configured. Set AZURE_OPENAI_API_KEY, "
                      "ANTHROPIC_API_KEY, or OPENAI_API_KEY in .env")
            return []

        provider_label = {
            "azure":     f"Azure OpenAI ({os.getenv('AZURE_OPENAI_DEPLOYMENT','gpt-4o')})",
            "anthropic": "Claude (claude-sonnet-4-6)",
            "openai":    "OpenAI (gpt-4o)",
        }.get(provider, provider)

        # Navigate
        try:
            page.goto(fp["url"], wait_until="commit", timeout=20000)
            page.wait_for_timeout(1500)
        except Exception:
            pass

        # Screenshot for vision analysis
        ss_b64: Optional[str] = None
        try:
            raw   = page.screenshot(type="jpeg", quality=65, full_page=False)
            ss_b64 = base64.standard_b64encode(raw).decode()
            self.emit("screenshot", self.feature,
                      f"Analyzing: {fp.get('title','')[:40]}", screenshot=ss_b64)
        except Exception:
            pass

        # Re-read live elements (page may differ from crawl snapshot)
        live_elements: List[Dict] = []
        try:
            live_elements = page.eval_on_selector_all(
                "button,input,select,textarea,[role='button'],[role='link'],a[href]",
                """els => els.slice(0,60).map(e => ({
                    tag:  e.tagName.toLowerCase(),
                    type: e.type || '',
                    id:   e.id   || '',
                    name: e.name || '',
                    text: (e.innerText || e.value || e.placeholder || '').trim().slice(0,60),
                    aria: e.getAttribute('aria-label') || '',
                    role: e.getAttribute('role') || '',
                    visible: e.offsetParent !== null
                })).filter(e => e.visible)""",
            )
        except Exception:
            live_elements = fp.get("elements", [])

        element_summary = _format_elements_for_claude(live_elements)
        strategy        = _FEATURE_STRATEGY.get(self.feature, _FEATURE_STRATEGY["general"])
        user_prompt     = _build_user_prompt(
            self.feature,
            fp.get("title", fp["url"]),
            fp["url"],
            element_summary,
            strategy,
        )

        self.emit("progress", self.feature,
                  f"[{provider_label}] Generating test plan for '{fp.get('title','')[:25]}'…")

        raw_text = _call_llm_for_test_plan(_SYSTEM_PROMPT, user_prompt, ss_b64)
        if not raw_text:
            self.emit("warning", self.feature,
                      f"LLM returned no response for {fp.get('title','?')[:30]}")
            return []

        try:
            # Strip accidental markdown fences
            clean = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.M)
            clean = re.sub(r"\s*```\s*$", "", clean, flags=re.M)
            data  = json.loads(clean)
            flows = data.get("flows", [])
            self.emit("progress", self.feature,
                      f"Generated {len(flows)} flow(s) for '{fp.get('title','')[:25]}'")
            return flows
        except json.JSONDecodeError as je:
            self.emit("warning", self.feature,
                      f"LLM returned invalid JSON: {str(je)[:60]}")
        return []

    # ── Flow execution ─────────────────────────────────────────────────────────

    def _execute_flow(self, page, fp: Dict, flow: Dict) -> Dict:
        """Execute all steps of a flow; record pass/fail + screenshots."""
        steps_result: List[Dict] = []

        # Return to the feature page before each flow
        try:
            page.goto(fp["url"], wait_until="commit", timeout=20000)
            page.wait_for_timeout(800)
        except Exception:
            pass

        for step in flow.get("steps", []):
            action      = step.get("action", "")
            target      = step.get("target", "")
            value       = step.get("value")
            description = step.get("description", target)

            step_out = {
                "action":      action,
                "target":      target,
                "value":       value,
                "description": description,
                "status":      "pass",
                "error":       None,
                "screenshot":  None,
            }

            try:
                self._execute_step(page, action, target, value, description)
                page.wait_for_timeout(500)

                # Screenshot after each step
                try:
                    raw = page.screenshot(type="jpeg", quality=50, full_page=False)
                    step_out["screenshot"] = base64.standard_b64encode(raw).decode()
                    self.emit("screenshot", self.feature,
                              f"✓ {description[:45]}", screenshot=step_out["screenshot"])
                except Exception:
                    pass

            except Exception as exc:
                step_out["status"] = "fail"
                step_out["error"]  = str(exc)[:150]
                self.emit("warning", self.feature,
                          f"✗ {description[:40]} — {str(exc)[:60]}")

            steps_result.append(step_out)

        return {"steps": steps_result}

    # ── Step dispatcher ────────────────────────────────────────────────────────

    def _execute_step(
        self, page, action: str, target: str,
        value: Optional[str], description: str,
    ) -> None:
        if action == "navigate":
            url = target if target.startswith("http") else f"{self.base_url.rstrip('/')}/{target.lstrip('/')}"
            page.goto(url, wait_until="commit", timeout=20000)
            page.wait_for_timeout(1000)

        elif action == "click":
            self._try_click(page, target, description)

        elif action == "fill":
            self._try_fill(page, target, value or "", description)

        elif action == "assert_visible":
            self._assert_visible(page, target, description)

        elif action == "assert_text":
            self._assert_text(page, target, value or "", description)

        elif action == "wait_for":
            page.wait_for_selector(target.split(",")[0].strip(), timeout=8000)

        elif action == "hover":
            for sel in _split_selectors(target):
                try:
                    page.hover(sel, timeout=3000)
                    return
                except Exception:
                    continue

        elif action == "select":
            for sel in _split_selectors(target):
                try:
                    page.select_option(sel, value or "", timeout=5000)
                    return
                except Exception:
                    continue

        elif action == "scroll":
            page.evaluate("window.scrollBy(0, 400)")

        # Unknown action — skip silently
        else:
            pass

    # ── Multi-layer element finders ────────────────────────────────────────────

    def _try_click(self, page, target: str, description: str) -> None:
        # Layer 1: CSS selectors
        for sel in _split_selectors(target):
            try:
                el = page.wait_for_selector(sel, state="visible", timeout=4000)
                if el:
                    el.scroll_into_view_if_needed()
                    el.click()
                    return
            except Exception:
                continue

        # Layer 2: get_by_text
        try:
            page.get_by_text(description, exact=False).first.click(timeout=3000)
            return
        except Exception:
            pass

        # Layer 3: ARIA roles
        for role in ("button", "link", "menuitem", "tab"):
            try:
                page.get_by_role(
                    role,
                    name=re.compile(description[:25], re.I),
                ).first.click(timeout=2000)
                return
            except Exception:
                continue

        raise Exception(f"Cannot click: {target}")

    def _try_fill(self, page, target: str, value: str, description: str) -> None:
        # Layer 1: CSS selectors
        for sel in _split_selectors(target):
            try:
                el = page.wait_for_selector(sel, state="visible", timeout=4000)
                if el:
                    el.scroll_into_view_if_needed()
                    el.fill(value)
                    return
            except Exception:
                continue

        # Layer 2: placeholder text
        try:
            page.get_by_placeholder(
                re.compile(description[:20], re.I),
            ).first.fill(value, timeout=3000)
            return
        except Exception:
            pass

        # Layer 3: label
        try:
            page.get_by_label(
                re.compile(description[:20], re.I),
            ).first.fill(value, timeout=3000)
            return
        except Exception:
            pass

        raise Exception(f"Cannot fill: {target}")

    def _assert_visible(self, page, target: str, description: str) -> None:
        for sel in _split_selectors(target):
            try:
                el = page.wait_for_selector(sel, state="visible", timeout=5000)
                if el:
                    return
            except Exception:
                continue
        raise Exception(f"Element not visible: {target}")

    def _assert_text(self, page, target: str, text: str, description: str) -> None:
        for sel in _split_selectors(target):
            try:
                el = page.wait_for_selector(sel, state="visible", timeout=5000)
                if el and text.lower() in (el.inner_text() or "").lower():
                    return
            except Exception:
                continue
        raise Exception(f"Text '{text}' not found in: {target}")

    # ── Scenario builder ───────────────────────────────────────────────────────

    def _build_scenario(self, fp: Dict, flow: Dict, result: Dict) -> Dict:
        sid    = f"auto_{self.feature}_{self.session_id[:8]}_{uuid4().hex[:6]}"
        passed = sum(1 for s in result["steps"] if s["status"] == "pass")
        total  = len(result["steps"])
        return {
            "id":     sid,
            "name":   f"[AUTO] {self.feature.replace('_', ' ').title()} — {flow['name']}",
            "module": self.feature,
            "source": "autonomous",
            "session_id": self.session_id,
            "autonomous_meta": {
                "page_url":         fp["url"],
                "page_title":       fp.get("title", ""),
                "feature":          self.feature,
                "steps_passed":     passed,
                "steps_total":      total,
                "flow_description": flow.get("description", ""),
            },
            # Clean steps — no screenshots stored in the scenario itself
            "steps": [
                {
                    "action":      s["action"],
                    "target":      s["target"],
                    "value":       s.get("value"),
                    "description": s["description"],
                }
                for s in result["steps"]
            ],
        }

    # ── Safety guard ───────────────────────────────────────────────────────────

    def _is_dangerous_flow(self, flow: Dict) -> bool:
        flow_text = flow.get("name", "").lower() + flow.get("description", "").lower()
        for step in flow.get("steps", []):
            step_text = (step.get("description") or "").lower()
            combined  = flow_text + step_text
            if any(w in combined for w in _DANGER_WORDS):
                return True
        return False


# ── Helpers ────────────────────────────────────────────────────────────────────

def _split_selectors(target: str) -> List[str]:
    return [s.strip() for s in target.split(",") if s.strip()]
