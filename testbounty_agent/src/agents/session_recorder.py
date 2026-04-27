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


# SSO domains treated as part of the app during recording
_RECORDER_SSO_DOMAINS = (
    "b2clogin.com", "login.microsoftonline.com", "accounts.microsoft.com",
    "login.microsoft.com", "okta.com", "auth0.com", "onelogin.com",
    "accounts.google.com", "pingidentity.com",
)


def _is_app_or_sso_domain(current_url: str, app_domain: str) -> bool:
    """Return True if URL belongs to the app or a known SSO provider."""
    from urllib.parse import urlparse
    netloc = urlparse(current_url).netloc
    if netloc == app_domain:
        return True
    return any(sso in netloc for sso in _RECORDER_SSO_DOMAINS)


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

  // Track input changes — password values are NEVER stored, replaced with placeholder
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
    from urllib.parse import urlparse
    import time

    session = SESSIONS[session_id]
    session["status"] = "recording"

    app_domain = urlparse(url).netloc  # e.g. "www.tracking.thermoking.com"

    # JS overlay shown when recording is active (green bar) or paused (grey bar)
    _INDICATOR_JS = """
    (function() {
      if (document.getElementById('__tb_indicator')) return;
      const bar = document.createElement('div');
      bar.id = '__tb_indicator';
      bar.style.cssText = [
        'position:fixed', 'top:0', 'left:0', 'right:0', 'z-index:2147483647',
        'height:4px', 'background:#22c55e', 'transition:background 0.3s',
        'pointer-events:none'
      ].join(';');
      const label = document.createElement('div');
      label.id = '__tb_indicator_label';
      label.style.cssText = [
        'position:fixed', 'top:4px', 'right:12px', 'z-index:2147483647',
        'background:rgba(0,0,0,0.7)', 'color:#22c55e', 'font:bold 11px monospace',
        'padding:2px 8px', 'border-radius:0 0 4px 4px', 'pointer-events:none'
      ].join(';');
      label.textContent = '● REC';
      document.body.appendChild(bar);
      document.body.appendChild(label);
    })();
    """

    _PAUSED_JS = """
    const b = document.getElementById('__tb_indicator');
    const l = document.getElementById('__tb_indicator_label');
    if (b) b.style.background = '#6b7280';
    if (l) { l.style.color = '#9ca3af'; l.textContent = '⏸ PAUSED (off-domain)'; }
    """

    _ACTIVE_JS = """
    const b = document.getElementById('__tb_indicator');
    const l = document.getElementById('__tb_indicator_label');
    if (b) b.style.background = '#22c55e';
    if (l) { l.style.color = '#22c55e'; l.textContent = '● REC'; }
    """

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--start-maximized"])
            context = browser.new_context(no_viewport=True)
            page = context.new_page()

            session["_browser"] = browser
            session["_context"] = context
            session["_page"] = page
            session["app_domain"] = app_domain

            # Inject recorder + visual indicator on every navigation
            page.add_init_script(_RECORDER_JS)
            page.add_init_script(_INDICATOR_JS)

            def on_framenavigated(frame):
                if frame != page.main_frame:
                    return
                nav_url = frame.url
                # Only record navigation events for app domain or SSO
                if _is_app_or_sso_domain(nav_url, app_domain):
                    session["events"].append({
                        "type": "navigate",
                        "url": nav_url,
                        "title": "",
                        "ts": int(datetime.now().timestamp() * 1000),
                    })
                    session["recording_paused"] = False
                else:
                    # Off-domain — pause recording, show indicator
                    session["recording_paused"] = True

            page.on("framenavigated", on_framenavigated)
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

            while session["status"] == "recording":
                try:
                    current_url = page.url
                    on_domain = _is_app_or_sso_domain(current_url, app_domain)

                    if on_domain:
                        # Harvest JS events — only on app / SSO pages
                        js_events = page.evaluate("window.__tbEvents || []")
                        if js_events:
                            page.evaluate("window.__tbEvents = []")
                            for ev in js_events:
                                ev["_url"] = current_url
                                session["events"].append(ev)
                        # Show green REC indicator
                        try:
                            page.evaluate(_ACTIVE_JS)
                        except Exception:
                            pass
                    else:
                        # Off-domain: discard any captured events, show paused indicator
                        try:
                            page.evaluate("window.__tbEvents = []")
                            page.evaluate(_PAUSED_JS)
                        except Exception:
                            pass

                except Exception:
                    pass

                time.sleep(0.5)

            # Final harvest (only if still on app domain)
            try:
                if _is_app_or_sso_domain(page.url, app_domain):
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
            "recording_paused": s.get("recording_paused", False),
            "app_domain": s.get("app_domain", ""),
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

    # ── Stable Azure B2C selectors (these don't change between sessions) ─────────
    # Only the URL query params change — the element IDs are fixed by the B2C policy
    _B2C_SELECTORS = {
        "username": "#signInName, input[name='signInName'], input[type='email']",
        "password": "#password, input[name='password'], input[type='password']",
        "next":     "#next, input[id='next'], button[type='submit'], input[type='submit']",
    }

    def _extract_sso_interactions(self, events: List[Dict]) -> Dict:
        """
        Extract fill/click events that happened on SSO pages.
        Returns selectors actually used during recording — these are stable.
        """
        sso = {"username_selector": None, "password_selector": None, "submit_selector": None,
               "username_value": None, "detected": False}
        for ev in events:
            url = ev.get("_url", "") or ev.get("url", "")
            if not self._is_sso_url(url):
                continue
            sso["detected"] = True
            t = ev.get("type")
            if t == "fill":
                inp_type = ev.get("inputType", "")
                val = ev.get("value", "")
                sel = ev.get("selector", "")
                if inp_type == "password" or "password" in sel.lower():
                    sso["password_selector"] = sel or self._B2C_SELECTORS["password"]
                elif inp_type in ("email", "text") or any(w in sel.lower() for w in ["email", "user", "name"]):
                    sso["username_selector"] = sel or self._B2C_SELECTORS["username"]
                    if val and val != "[PASSWORD]":
                        sso["username_value"] = val
            elif t == "click":
                sel = ev.get("selector", "")
                if sel:
                    sso["submit_selector"] = sel
        # Fill defaults for any missing selectors
        sso["username_selector"] = sso["username_selector"] or self._B2C_SELECTORS["username"]
        sso["password_selector"] = sso["password_selector"] or self._B2C_SELECTORS["password"]
        sso["submit_selector"]   = sso["submit_selector"]   or self._B2C_SELECTORS["next"]
        return sso

    def _build_login_scenario(self, base_url: str, sso: Dict, scenario_id: str = "rec_001") -> Dict:
        """
        Build a stable login scenario.
        - Navigates to APP URL (not B2C URL — URL params change every session)
        - Uses stable B2C element selectors (these never change)
        - Password stored as [PASSWORD] placeholder, replaced at runtime
        """
        return {
            "id": scenario_id,
            "name": "Valid Login",
            "description": "Login with valid credentials through SSO. Prerequisite for all other tests.",
            "module": "auth",
            "type": "happy_path",
            "priority": "high",
            "depends_on": None,
            "steps": [
                {"action": "navigate",  "target": base_url,
                 "value": None,         "description": "Navigate to application login page"},
                {"action": "fill",      "target": sso["username_selector"],
                 "value": "{{username}}", "description": "Enter username / email"},
                {"action": "click",     "target": sso["submit_selector"],
                 "value": None,         "description": "Click Next button"},
                {"action": "fill",      "target": sso["password_selector"],
                 "value": "[PASSWORD]", "description": "Enter password"},
                {"action": "click",     "target": sso["submit_selector"],
                 "value": None,         "description": "Click Sign In button"},
                {"action": "wait",      "target": "navigation",
                 "value": None,         "description": "Wait for redirect to application"},
                {"action": "assert",    "target": "url_changed",
                 "value": None,         "description": "Verify login succeeded — redirected to app"},
            ],
            "status": "pending",
            "source": "session_recording",
        }

    def _llm_convert(self, events: List[Dict], base_url: str) -> Dict:
        """
        AI-powered conversion.
        Architecture mirrors POM:
        - Auth module = @BeforeClass (always runs first, no depends_on)
        - All other modules = test classes with depends_on auth
        - B2C URLs are NEVER stored in steps (they change every session)
        - Stable selectors only
        """
        # ── Step 1: Extract SSO interactions ─────────────────────────────────
        sso = self._extract_sso_interactions(events)
        sso_detected = sso["detected"]

        # ── Step 2: Build auth module with stable login scenario ──────────────
        auth_scenario = self._build_login_scenario(base_url, sso, "rec_001")
        auth_module = {
            "name": "Authentication",
            "requires_auth": False,
            "scenarios": [auth_scenario],
        }

        # ── Step 3: Collect app-domain interactions for other modules ─────────
        app_events = [
            e for e in events
            if e.get("type") in ("navigate", "fill", "click", "submit")
            and not self._is_sso_url(e.get("_url", "") or e.get("url", ""))
        ][:80]

        # Sanitise navigate URLs — strip transient query params
        for ev in app_events:
            if ev.get("type") == "navigate" and ev.get("url"):
                ev["url"] = self._sanitise_url(ev["url"])

        # Pages the user visited on the app (not SSO)
        pages_visited = []
        for ev in app_events:
            if ev.get("type") == "navigate":
                u = ev.get("url", "")
                if u and u not in pages_visited:
                    pages_visited.append(u)

        # ── Step 4: Skills context ────────────────────────────────────────────
        try:
            from src.agents.skills_loader import get_skills_loader
            vocab = [e.get("text", "") for e in events if e.get("text")] + pages_visited
            skills_ctx = get_skills_loader().get_skills_for_context(
                domain="", vocabulary=vocab, app_description=f"App at {base_url}")
        except Exception:
            skills_ctx = ""

        # ── Step 5: LLM generates non-auth scenarios ──────────────────────────
        prompt = f"""You are a senior QA engineer building test scenarios for a production application.

APPLICATION: {base_url}
APP PAGES VISITED (after login): {json.dumps(pages_visited)}
SSO AUTH: {'Yes — Azure B2C (login already handled in auth module)' if sso_detected else 'No'}

APP INTERACTIONS RECORDED (post-login events only):
{json.dumps(app_events, indent=2, ensure_ascii=True)}

{skills_ctx}

=== ARCHITECTURE RULES (follow strictly) ===
1. The AUTH module is ALREADY handled — do NOT generate login scenarios.
   Auth scenario id is "rec_001". All non-auth scenarios MUST set "depends_on": "rec_001".

2. NEVER use SSO/B2C provider URLs (b2clogin.com, microsoftonline.com) in navigate steps.
   For navigate steps, only use paths relative to: {base_url}

3. Module detection — name by APP FUNCTION, not URL hostname:
   URL path contains /logon, /login, /signin  → skip (handled by auth)
   URL path contains /dashboard, /home, /      → module: "dashboard"
   URL path contains /asset, /device, /unit    → module: "assets"
   URL path contains /track, /map, /location   → module: "tracking"
   URL path contains /report, /history         → module: "reports"
   URL path contains /alert, /notification     → module: "alerts"
   URL path contains /setting, /profile        → module: "settings"
   Everything else                             → module: "general"

4. For each module, generate:
   - 1 happy path (valid actions, expected success)
   - 1 error/negative path (missing field, invalid value, boundary)
   - 1 edge case (empty state, special chars, timeout)

5. Use ACTUAL selectors from the recorded events in happy path steps.
   For negative/edge, reuse same selectors with different values.

6. IDs start from rec_002 (rec_001 is login). Increment sequentially.

7. Steps use this structure exactly:
   {{"action": "navigate|fill|click|assert|wait", "target": "<url-path or CSS selector>",
     "value": "<string or null>", "description": "<plain English what this step does>"}}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "modules": {{
    "<module_key>": {{
      "name": "<Display Name>",
      "requires_auth": true,
      "scenarios": [
        {{
          "id": "rec_002",
          "name": "<action + outcome e.g. 'View Asset List'>",
          "description": "<one sentence what this tests>",
          "module": "<module_key>",
          "type": "happy_path|error_path|edge_case",
          "priority": "high|medium|low",
          "depends_on": "rec_001",
          "steps": [...],
          "status": "pending",
          "source": "session_recording"
        }}
      ]
    }}
  }},
  "total_scenarios": <number not counting auth>
}}"""

        response = self.llm.model.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        # Strip markdown fences and non-ASCII (fixes charmap errors on Windows)
        content = content.replace("```json", "").replace("```", "").strip()
        content = content.encode("ascii", errors="replace").decode("ascii")

        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {"modules": {}, "total_scenarios": 0}

        # Inject auth module as FIRST module (it must run before everything)
        final_modules = {"auth": auth_module}
        final_modules.update(result.get("modules", {}))

        total = sum(len(m.get("scenarios", [])) for m in final_modules.values())
        return {
            "modules": final_modules,
            "total_scenarios": total,
            "source": "session_recording",
            "sso_detected": sso_detected,
        }

    def _rule_convert(self, events: List[Dict], base_url: str) -> Dict:
        """
        Fallback (no LLM): same POM architecture.
        - Auth module built from SSO interactions with stable selectors
        - App flows grouped by URL path into named modules
        - All non-auth scenarios depend on rec_001
        """
        if not events:
            return {"modules": {}, "total_scenarios": 0, "source": "session_recording"}

        # Build auth module from SSO interactions
        sso = self._extract_sso_interactions(events)
        auth_scenario = self._build_login_scenario(base_url, sso, "rec_001")
        modules: Dict[str, Any] = {
            "auth": {
                "name": "Authentication",
                "requires_auth": False,
                "scenarios": [auth_scenario],
            }
        }

        # Group non-SSO app events by page
        app_events = [
            e for e in events
            if not self._is_sso_url(e.get("_url", "") or e.get("url", ""))
        ]

        flows: List[List[Dict]] = []
        current_flow: List[Dict] = []
        for ev in app_events:
            if ev.get("type") == "navigate":
                if current_flow:
                    flows.append(current_flow)
                current_flow = [ev]
            else:
                current_flow.append(ev)
        if current_flow:
            flows.append(current_flow)

        scenario_counter = 2  # rec_001 is login
        for flow in flows:
            if not flow:
                continue
            nav_url = flow[0].get("url", base_url)
            if self._is_sso_url(nav_url):
                continue  # skip SSO flows entirely
            module = self._infer_module_from_url(nav_url)
            if module == "auth":
                continue  # already handled
            steps = self._flow_to_steps(flow)
            if not steps:
                continue

            sc_id = f"rec_{scenario_counter:03d}"
            scenario_counter += 1
            name = self._module_display_name(module)
            scenario = {
                "id": sc_id,
                "name": f"Recorded {name} flow",
                "description": f"Recorded user session — {len(flow)} interactions",
                "module": module,
                "type": "happy_path",
                "priority": "high",
                "depends_on": "rec_001",  # always depends on login
                "steps": steps,
                "status": "pending",
                "source": "session_recording",
            }
            if module not in modules:
                modules[module] = {
                    "name": name,
                    "requires_auth": True,
                    "scenarios": [],
                }
            modules[module]["scenarios"].append(scenario)

        total = sum(len(m["scenarios"]) for m in modules.values())
        return {
            "modules": modules,
            "total_scenarios": total,
            "source": "session_recording",
            "sso_detected": sso["detected"],
        }

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
            # Skip SSO navigate events — they contain expiring URLs
            if t == "navigate":
                raw_url = ev.get("url", "/")
                if self._is_sso_url(raw_url):
                    continue
                clean_url = self._sanitise_url(raw_url)
                steps.append({
                    "action": "navigate", "target": clean_url,
                    "value": None, "description": f"Navigate to {clean_url}",
                })
            elif t == "fill":
                sel = ev.get("selector", "input")
                val = ev.get("value", "")
                # Keep [PASSWORD] as placeholder — replaced at runtime
                if val == "[PASSWORD]":
                    val = "[PASSWORD]"
                steps.append({
                    "action": "fill", "target": sel,
                    "value": val, "description": f"Fill {ev.get('text') or sel}",
                })
            elif t == "click":
                sel = ev.get("selector", "button")
                text = ev.get("text", "")
                steps.append({
                    "action": "click", "target": sel,
                    "value": None, "description": f"Click {text}" if text else f"Click {sel}",
                })
            elif t == "submit":
                steps.append({
                    "action": "click",
                    "target": ev.get("selector", "button[type='submit']"),
                    "value": None, "description": "Submit form",
                })

        if steps:
            steps.append({"action": "assert", "target": "page_loaded", "value": None, "description": "Verify page loaded"})

        return steps

    def _infer_module_from_url(self, url: str) -> str:
        lower = url.lower()
        if any(w in lower for w in ["/login", "/signin", "/auth", "/logon", "/register", "/signup"]):
            return "auth"
        if any(w in lower for w in ["/asset", "/device", "/unit", "/equipment"]):
            return "assets"
        if any(w in lower for w in ["/track", "/map", "/location", "/fleet", "/geo"]):
            return "tracking"
        if any(w in lower for w in ["/report", "/history", "/export", "/analytics"]):
            return "reports"
        if any(w in lower for w in ["/alert", "/notification", "/alarm"]):
            return "alerts"
        if any(w in lower for w in ["/setting", "/profile", "/account", "/preferences", "/config"]):
            return "settings"
        if any(w in lower for w in ["/admin", "/manage"]):
            return "admin"
        if any(w in lower for w in ["/dashboard", "/home", "/overview", "/summary"]):
            return "dashboard"
        if any(w in lower for w in ["/cart", "/checkout", "/order", "/payment"]):
            return "checkout"
        if any(w in lower for w in ["/search", "/find", "/browse"]):
            return "search"
        return "general"

    def _module_display_name(self, key: str) -> str:
        names = {
            "auth": "Authentication", "assets": "Assets", "tracking": "Tracking",
            "reports": "Reports", "alerts": "Alerts", "settings": "Settings",
            "admin": "Admin", "dashboard": "Dashboard", "checkout": "Checkout",
            "search": "Search", "general": "General",
        }
        return names.get(key, key.replace("_", " ").title())

    def _url_to_label(self, url: str) -> str:
        path = re.sub(r"https?://[^/]+", "", url).strip("/")
        if not path:
            return "Home"
        return path.split("/")[0].replace("-", " ").replace("_", " ").title()


# ── Module-level helpers ──────────────────────────────────────────────────────

_agent: Optional[SessionRecorderAgent] = None


def get_recorder(llm_service=None) -> SessionRecorderAgent:
    global _agent
    if _agent is None:
        _agent = SessionRecorderAgent(llm_service=llm_service)
    return _agent
