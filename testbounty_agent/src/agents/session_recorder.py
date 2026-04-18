"""
SessionRecorderAgent — Shadow Mode.

Records a real user session in a visible (headful) Playwright browser,
then converts the recorded events into test scenarios.

Flow:
  1. POST /api/session-record/start  → opens visible browser, returns session_id
  2. User browses app normally
  3. POST /api/session-record/{id}/stop → closes browser, AI analyses events → scenarios

Events captured via CDP + injected JS:
  - navigation (URL changes)
  - click (element selector, text, tag)
  - fill (input name/id, value masked for passwords)
  - submit (form)
  - assertion hints (page title, h1, success/error messages)
"""

from __future__ import annotations

import json
import platform
import re
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── In-memory session store ───────────────────────────────────────────────────
# { session_id: { status, events, url, plan_id, browser_ref, page_ref, thread } }
SESSIONS: Dict[str, Dict] = {}


# ── JS recorder snippet injected into every page ─────────────────────────────
_RECORDER_JS = """
(function() {
  if (window.__tbRecorderAttached) return;
  window.__tbRecorderAttached = true;
  window.__tbEvents = window.__tbEvents || [];

  function getSelector(el) {
    if (!el || el.nodeType !== 1) return 'unknown';
    if (el.id) return '#' + el.id;
    if (el.name) return '[name="' + el.name + '"]';
    const type = el.getAttribute('type');
    if (type) return el.tagName.toLowerCase() + '[type="' + type + '"]';
    const cls = Array.from(el.classList).filter(c => !c.match(/^(ng|js|is|has|active|open|show|hide)/)).slice(0,2).join('.');
    if (cls) return el.tagName.toLowerCase() + '.' + cls;
    return el.tagName.toLowerCase();
  }

  function getVisibleText(el) {
    return (el.innerText || el.value || el.placeholder || el.getAttribute('aria-label') || '').trim().substring(0, 60);
  }

  // Track clicks
  document.addEventListener('click', function(e) {
    const el = e.target;
    window.__tbEvents.push({
      type: 'click',
      selector: getSelector(el),
      text: getVisibleText(el),
      tag: el.tagName.toLowerCase(),
      ts: Date.now()
    });
  }, true);

  // Track input changes
  document.addEventListener('change', function(e) {
    const el = e.target;
    const isPassword = el.type === 'password';
    window.__tbEvents.push({
      type: 'fill',
      selector: getSelector(el),
      value: isPassword ? '[PASSWORD]' : (el.value || '').substring(0, 200),
      tag: el.tagName.toLowerCase(),
      inputType: el.type || 'text',
      ts: Date.now()
    });
  }, true);

  // Track form submits
  document.addEventListener('submit', function(e) {
    const form = e.target;
    window.__tbEvents.push({
      type: 'submit',
      selector: getSelector(form),
      action: form.action || window.location.href,
      ts: Date.now()
    });
  }, true);

  console.log('[TestBounty] Session recorder attached');
})();
"""


# ── Recorder Thread ────────────────────────────────────────────────────────────

def _run_recorder_sync(session_id: str, url: str):
    """Runs in a background thread — opens headful browser and keeps it open."""
    from playwright.sync_api import sync_playwright

    session = SESSIONS[session_id]
    session["status"] = "recording"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
            context = browser.new_context(no_viewport=True)
            page = context.new_page()

            # Store refs for stop()
            session["_browser"] = browser
            session["_context"] = context
            session["_page"] = page

            # Inject recorder on every navigation
            page.add_init_script(_RECORDER_JS)

            # Track URL changes
            def on_framenavigated(frame):
                if frame == page.main_frame:
                    session["events"].append({
                        "type": "navigate",
                        "url": frame.url,
                        "title": "",
                        "ts": int(datetime.now().timestamp() * 1000),
                    })

            page.on("framenavigated", on_framenavigated)

            # Navigate to starting URL
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # Poll for events from JS and harvest them
            while session["status"] == "recording":
                try:
                    js_events = page.evaluate("window.__tbEvents || []")
                    if js_events:
                        page.evaluate("window.__tbEvents = []")
                        for ev in js_events:
                            ev["_url"] = page.url
                            session["events"].append(ev)
                except Exception:
                    pass
                import time; time.sleep(0.5)

            # Final harvest
            try:
                js_events = page.evaluate("window.__tbEvents || []")
                for ev in js_events:
                    ev["_url"] = page.url
                    session["events"].append(ev)
            except Exception:
                pass

            try:
                browser.close()
            except Exception:
                pass

    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)


# ── Public API ────────────────────────────────────────────────────────────────

class SessionRecorderAgent:
    def __init__(self, llm_service=None):
        self.llm = llm_service

    def start_session(self, url: str, plan_id: Optional[str] = None) -> str:
        """Start a recording session. Returns session_id."""
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "id": session_id,
            "url": url,
            "plan_id": plan_id,
            "status": "starting",
            "events": [],
            "scenarios": None,
            "created_at": datetime.now().isoformat(),
            "stopped_at": None,
            "error": None,
        }

        # Launch browser in background thread
        t = threading.Thread(target=_run_recorder_sync, args=(session_id, url), daemon=True)
        t.start()
        SESSIONS[session_id]["_thread"] = t

        return session_id

    def stop_session(self, session_id: str) -> Dict:
        """Stop recording and analyse events into scenarios."""
        if session_id not in SESSIONS:
            return {"error": "Session not found"}

        session = SESSIONS[session_id]
        session["status"] = "analysing"
        session["stopped_at"] = datetime.now().isoformat()

        # Signal the thread to stop
        # It will stop on next loop iteration when status != "recording"

        events = session.get("events", [])
        url = session.get("url", "/")

        # Convert events to scenarios
        scenarios = self._events_to_scenarios(events, url)
        session["scenarios"] = scenarios
        session["status"] = "ready"

        return {
            "session_id": session_id,
            "events_count": len(events),
            "scenarios": scenarios,
            "status": "ready",
        }

    def get_session(self, session_id: str) -> Optional[Dict]:
        if session_id not in SESSIONS:
            return None
        s = SESSIONS[session_id]
        return {
            "id": s["id"],
            "url": s["url"],
            "plan_id": s["plan_id"],
            "status": s["status"],
            "events_count": len(s.get("events", [])),
            "created_at": s["created_at"],
            "stopped_at": s["stopped_at"],
            "error": s.get("error"),
        }

    # ── Event → Scenario conversion ───────────────────────────────────────────

    def _events_to_scenarios(self, events: List[Dict], base_url: str) -> Dict:
        """Convert recorded event stream → grouped test scenarios."""
        if self.llm and getattr(self.llm, "provider", "mock") != "mock":
            try:
                return self._llm_convert(events, base_url)
            except Exception as e:
                print(f"[SessionRecorder] LLM conversion failed ({e}), using rule-based")

        return self._rule_convert(events, base_url)

    # Known SSO/OAuth provider domains — navigate steps to these are replaced
    _SSO_DOMAINS = (
        "b2clogin.com", "login.microsoftonline.com", "accounts.microsoft.com",
        "login.microsoft.com", "okta.com", "auth0.com", "onelogin.com",
        "ping.com", "pingidentity.com", "accounts.google.com", "appleid.apple.com",
        "facebook.com/login", "github.com/login",
    )

    def _is_sso_url(self, url: str) -> bool:
        return any(d in url for d in self._SSO_DOMAINS)

    def _llm_convert(self, events: List[Dict], base_url: str) -> Dict:
        """
        AI-powered conversion: analyse the recorded session to produce FULL
        module coverage — positive paths, negative paths, edge cases, and
        security checks — not just a replay of what was recorded.
        """
        from langchain_core.output_parsers import StrOutputParser

        # ── Build page-type map from navigation events ────────────────────────
        pages_visited = []
        sso_detected = False
        for ev in events:
            if ev.get("type") == "navigate":
                url = ev.get("url", "")
                if self._is_sso_url(url):
                    sso_detected = True
                else:
                    clean = self._sanitise_url(url)
                    if clean and clean not in pages_visited:
                        pages_visited.append(clean)

        # ── Compact event summary (strip noise, cap size) ─────────────────────
        meaningful = [
            e for e in events
            if e.get("type") in ("navigate", "fill", "click", "submit")
            and not self._is_sso_url(e.get("url", "") or e.get("_url", ""))
        ][:60]

        # Sanitise navigate URLs in events before sending to LLM
        for ev in meaningful:
            if ev.get("type") == "navigate" and ev.get("url"):
                ev["url"] = self._sanitise_url(ev["url"])

        # ── Load relevant skills context ──────────────────────────────────────
        try:
            from src.agents.skills_loader import get_skills_loader
            vocab = [e.get("text", "") for e in events if e.get("text")] + pages_visited
            skills_ctx = get_skills_loader().get_skills_for_context(
                domain="",
                vocabulary=vocab,
                app_description=f"App at {base_url}",
            )
        except Exception:
            skills_ctx = ""

        sso_note = (
            "\nNOTE: SSO/OAuth redirect detected (Azure B2C / Microsoft login). "
            "The test should navigate to the app URL and handle SSO as an auth prerequisite, "
            "not navigate directly to the SSO provider URL."
            if sso_detected else ""
        )

        prompt = f"""You are a senior QA engineer with deep application testing expertise.
A user recorded their session while using an application. Your job is NOT just to replay
what they did — you must use the recording as a CLUE to understand the application, then
generate COMPREHENSIVE test scenarios for each module/page visited.

BASE URL: {base_url}
PAGES VISITED: {json.dumps(pages_visited)}
{sso_note}

RECORDED INTERACTIONS (condensed):
{json.dumps(meaningful, indent=2)}

{skills_ctx}

=== YOUR TASK ===
For EACH page/module the user visited, generate a FULL set of test scenarios:
- At least 1 happy path (valid data, successful flow)
- At least 1 error path (invalid data, wrong credentials, missing fields)
- At least 1 edge case (boundary, empty state, special characters)
- Security test where relevant (auth bypass, SQL injection on login forms)

Rules:
1. Use the ACTUAL selectors from the recorded events for happy-path steps
2. For negative/edge cases, re-use the same page URL and selectors but change the values
3. Identify the module from the page URL/content:
   - /login, /signin → "auth" module
   - /home, /dashboard, / → "home" module
   - /asset, /tracking, /fleet, /device → "tracking" module
   - /report → "reports" module
   - /setting, /profile, /account → "settings" module
4. SSO flows: the happy path navigate step should go to the app base URL ({base_url}),
   NOT to the SSO provider URL
5. Each scenario must have a unique id like "rec_NNN" (increment from 001)

Return ONLY valid JSON in this exact structure:
{{
  "modules": {{
    "<module_name>": {{
      "name": "<Display Name>",
      "requires_auth": <true|false>,
      "scenarios": [
        {{
          "id": "rec_001",
          "name": "<descriptive name e.g. 'Valid Login - SSO'>",
          "description": "<what this tests and why it matters>",
          "module": "<module_name>",
          "type": "happy_path|error_path|edge_case|security",
          "priority": "high|medium|low",
          "depends_on": null,
          "steps": [
            {{"action": "navigate|fill|click|assert|wait", "target": "<url or CSS selector>", "value": "<string or null>", "description": "<plain English>"}}
          ],
          "status": "pending",
          "source": "session_recording"
        }}
      ]
    }}
  }},
  "total_scenarios": <number>
}}"""

        response = self.llm.model.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        content = content.replace("```json", "").replace("```", "").strip()

        result = json.loads(content)
        total = sum(len(m.get("scenarios", [])) for m in result.get("modules", {}).values())
        result["total_scenarios"] = total
        result["source"] = "session_recording"
        result["sso_detected"] = sso_detected
        return result

    def _rule_convert(self, events: List[Dict], base_url: str) -> Dict:
        """Group events by navigation into flows, build steps."""
        if not events:
            return {"modules": {}, "total_scenarios": 0, "source": "session_recording"}

        # Split events into flows by navigation
        flows: List[List[Dict]] = []
        current_flow: List[Dict] = []

        for ev in events:
            if ev.get("type") == "navigate":
                if current_flow:
                    flows.append(current_flow)
                current_flow = [ev]
            else:
                current_flow.append(ev)

        if current_flow:
            flows.append(current_flow)

        modules: Dict[str, Any] = {}

        for i, flow in enumerate(flows):
            if not flow:
                continue

            # Determine module from first navigation URL
            nav_url = flow[0].get("url", base_url)
            module = self._infer_module_from_url(nav_url)
            name = f"Recorded flow {i+1}: {self._url_to_label(nav_url)}"

            steps = self._flow_to_steps(flow)
            if not steps:
                continue

            scenario = {
                "id": f"rec_{i+1:03d}",
                "name": name,
                "description": f"Recorded user session — {len(flow)} interactions",
                "module": module,
                "type": "happy_path",
                "priority": "high",
                "depends_on": None,
                "steps": steps,
                "status": "pending",
                "source": "session_recording",
            }

            if module not in modules:
                modules[module] = {"name": module.replace("_", " ").title(), "requires_auth": False, "scenarios": []}
            modules[module]["scenarios"].append(scenario)

        total = sum(len(m["scenarios"]) for m in modules.values())
        return {"modules": modules, "total_scenarios": total, "source": "session_recording"}

    # Query params that are transient/session-specific and should be stripped
    _TRANSIENT_PARAMS = frozenset({
        "csrf_token", "csrftoken", "_token", "state", "nonce", "code",
        "session", "sessionid", "session_id", "sid",
        "rememberMe", "remember_me",
        "timestamp", "ts", "t", "_t",
        "sig", "signature", "hmac",
    })

    def _sanitise_url(self, url: str) -> str:
        """Strip transient/session query params that expire between record and replay."""
        try:
            from urllib.parse import urlparse, urlencode, parse_qsl
            parsed = urlparse(url)
            clean_params = [
                (k, v) for k, v in parse_qsl(parsed.query)
                if k.lower() not in self._TRANSIENT_PARAMS
            ]
            clean = parsed._replace(query=urlencode(clean_params))
            return clean.geturl()
        except Exception:
            return url

    def _flow_to_steps(self, flow: List[Dict]) -> List[Dict]:
        steps = []
        for ev in flow:
            t = ev.get("type")
            if t == "navigate":
                raw_url = ev.get("url", "/")
                clean_url = self._sanitise_url(raw_url)
                steps.append({"action": "navigate", "target": clean_url, "value": None, "description": f"Navigate to {clean_url}"})
            elif t == "fill":
                sel = ev.get("selector", "input")
                val = ev.get("value", "")
                if val == "[PASSWORD]":
                    val = "TestPassword123!"
                steps.append({"action": "fill", "target": sel, "value": val, "description": f"Fill {sel}"})
            elif t == "click":
                sel = ev.get("selector", "button")
                text = ev.get("text", "")
                desc = f"Click {text}" if text else f"Click {sel}"
                steps.append({"action": "click", "target": sel, "value": None, "description": desc})
            elif t == "submit":
                steps.append({"action": "click", "target": ev.get("selector", "button[type='submit']"), "value": None, "description": "Submit form"})

        # Add a final assert step
        if steps:
            steps.append({"action": "assert", "target": "element_visible", "value": None, "description": "Verify page loaded"})

        return steps

    def _infer_module_from_url(self, url: str) -> str:
        lower = url.lower()
        if any(w in lower for w in ["/login", "/signin", "/auth", "/logout", "/register", "/signup"]):
            return "auth"
        if any(w in lower for w in ["/cart", "/checkout", "/order", "/payment", "/basket"]):
            return "checkout"
        if any(w in lower for w in ["/search", "/find", "/browse"]):
            return "search"
        if any(w in lower for w in ["/profile", "/account", "/settings", "/preferences"]):
            return "profile"
        if any(w in lower for w in ["/product", "/item", "/catalog", "/listing"]):
            return "products"
        if any(w in lower for w in ["/admin", "/manage", "/dashboard/admin"]):
            return "admin"
        if any(w in lower for w in ["/dashboard", "/home", "/overview"]):
            return "dashboard"
        return "general"

    def _url_to_label(self, url: str) -> str:
        path = re.sub(r"https?://[^/]+", "", url).strip("/")
        if not path:
            return "Home"
        parts = path.split("/")
        return parts[0].replace("-", " ").replace("_", " ").title()


# ── Module-level helpers ──────────────────────────────────────────────────────

_agent: Optional[SessionRecorderAgent] = None


def get_recorder(llm_service=None) -> SessionRecorderAgent:
    global _agent
    if _agent is None:
        _agent = SessionRecorderAgent(llm_service=llm_service)
    return _agent
