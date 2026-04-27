"""
AutonomousSession — The "Team Lead" AI that explores any web application.

Architecture:
  OrchestratorAgent  → crawls every page, groups them into features
  LandingPageAgent   → validates UI, headings, links, spelling, accessibility
  FeatureAgents      → one per discovered feature (auth, dashboard, etc.)

All agents stream events via a broadcast callback → WebSocket → frontend.
When an agent needs user input it emits a "question" event and PAUSES until
the user answers via the frontend (WebSocket reply).
"""
from __future__ import annotations

import asyncio
import base64
import platform
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse
from uuid import uuid4

# ── Feature pattern routing ────────────────────────────────────────────────────
_FEATURE_PATTERNS: Dict[str, List[str]] = {
    "authentication": ["/login", "/signin", "/sign-in", "/auth", "/logout",
                       "/register", "/signup", "/forgot", "/password", "/logon"],
    "dashboard":      ["/dashboard", "/home", "/overview", "/summary"],
    "user_profile":   ["/profile", "/account", "/settings", "/preferences", "/user"],
    "products":       ["/product", "/catalog", "/items", "/inventory", "/shop", "/store"],
    "orders":         ["/order", "/cart", "/checkout", "/purchase", "/payment", "/invoice"],
    "reports":        ["/report", "/analytics", "/statistics", "/chart", "/export", "/history"],
    "alerts":         ["/alert", "/notification", "/alarm", "/warning", "/event"],
    "admin":          ["/admin", "/manage", "/management", "/configuration"],
    "tracking":       ["/track", "/map", "/location", "/gps", "/fleet", "/asset", "/vehicle"],
    "support":        ["/help", "/support", "/faq", "/contact", "/ticket"],
}

# ── Feature agent "personalities" (questions they ask) ────────────────────────
_AGENT_QUESTIONS: Dict[str, List[Dict]] = {
    "authentication": [
        {"q": "I found a login page. What authentication method does this app primarily use?",
         "opts": ["Email + Password", "SSO / OAuth", "MFA / OTP", "Both Email and SSO"]},
    ],
    "products": [
        {"q": "I can see product listings. Are there any restricted categories or regions to test?",
         "opts": ["No restrictions", "Age-restricted items", "Region-locked", "Skip"]},
    ],
    "orders": [
        {"q": "I found a checkout flow. Should I test with real payment methods or sandbox?",
         "opts": ["Sandbox / Test cards", "Skip payment tests", "Real payment (be careful!)"]},
    ],
    "reports": [
        {"q": "I found a reports section. Which export formats need to be validated?",
         "opts": ["PDF", "CSV / Excel", "Both PDF and CSV", "Skip"]},
    ],
    "admin": [
        {"q": "I found admin pages. Do you want me to test admin-only functionality?",
         "opts": ["Yes, I have admin credentials", "No, skip admin tests", "Read-only admin tests only"]},
    ],
}

# ── Common typos ────────────────────────────────────────────────────────────────
_COMMON_TYPOS = {
    "teh": "the", "hte": "the", "thier": "their", "taht": "that",
    "recieve": "receive", "occured": "occurred", "seperate": "separate",
    "definately": "definitely", "accomodate": "accommodate", "untill": "until",
    "succesful": "successful", "sucess": "success", "adress": "address",
    "wierd": "weird", "calender": "calendar", "recomend": "recommend",
    "enviroment": "environment", "occurance": "occurrence",
}

_AGENT_ICONS = {
    "orchestrator": "👑",
    "landing_page": "🏠",
    "authentication": "🔐",
    "dashboard": "📊",
    "user_profile": "👤",
    "products": "📦",
    "orders": "🛒",
    "reports": "📈",
    "alerts": "🔔",
    "admin": "⚙️",
    "tracking": "📍",
    "support": "💬",
    "general": "🔍",
}


class AutonomousSession:
    """
    Manages one full autonomous exploration and test generation session.
    Created by the API endpoint, runs in background, pushes events to WebSocket.
    """

    def __init__(self, session_id: str, url: str):
        self.session_id = session_id
        self.url = url.rstrip("/")
        self.domain = urlparse(url).netloc
        self.status = "starting"   # starting | running | waiting_answer | done | error
        self.agents: List[Dict] = []
        self.events: List[Dict] = []
        self.page_map: Dict[str, Any] = {}
        self.findings_summary: Dict[str, Any] = {}

        # Answer synchronization (threading.Event for sync Playwright thread)
        self._answer_event = threading.Event()
        self._pending_answer: Optional[str] = None
        self._pending_question: Optional[Dict] = None

        # WebSocket subscribers (list of async send callbacks)
        self._subscribers: List[Callable] = []
        # Main event loop — captured in run() so sync thread can schedule coroutines
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        # Stop signal — set by stop() so _run_sync can exit its keep-alive loop
        self._stop = threading.Event()

    # ── Subscriber management ──────────────────────────────────────────────────

    def subscribe(self, send_fn: Callable) -> None:
        self._subscribers.append(send_fn)

    def unsubscribe(self, send_fn: Callable) -> None:
        self._subscribers = [s for s in self._subscribers if s != send_fn]

    # ── Event emission ─────────────────────────────────────────────────────────

    def _emit_event(self, event: Dict) -> None:
        """
        Store event and push to all WebSocket subscribers.
        Safe to call from any thread — uses the captured main event loop.
        """
        self.events.append(event)
        if not self._subscribers or not self._loop:
            return
        for send_fn in list(self._subscribers):
            try:
                # Schedule the async send on the main FastAPI event loop
                asyncio.run_coroutine_threadsafe(send_fn(event), self._loop)
            except Exception:
                pass

    def _make_event(self, etype: str, agent: str, message: str,
                    data: dict = None, screenshot: str = None) -> Dict:
        return {
            "id": str(uuid4())[:8],
            "type": etype,
            "agent": agent,
            "icon": _AGENT_ICONS.get(agent, "🤖"),
            "message": message,
            "data": data or {},
            "screenshot": screenshot,
            "timestamp": datetime.now().isoformat(),
            "agents_snapshot": [dict(a) for a in self.agents],
        }

    def emit(self, etype: str, agent: str, message: str,
             data: dict = None, screenshot: str = None) -> None:
        """Emit an event from the sync Playwright thread."""
        # Update agent status in snapshot
        self._update_agent(agent, current_task=message)
        event = self._make_event(etype, agent, message, data=data, screenshot=screenshot)
        self._emit_event(event)

    # ── Agent registry ─────────────────────────────────────────────────────────

    def _register_agent(self, name: str, display: str, role: str) -> None:
        # Avoid duplicates
        if any(a["name"] == name for a in self.agents):
            return
        self.agents.append({
            "name": name,
            "display": display,
            "icon": _AGENT_ICONS.get(name, "🤖"),
            "role": role,
            "status": "idle",
            "findings_count": 0,
            "findings": [],
            "current_task": "Waiting...",
        })

    def _update_agent(self, name: str, **kwargs) -> None:
        for a in self.agents:
            if a["name"] == name:
                a.update(kwargs)
                break

    # ── Question / answer ──────────────────────────────────────────────────────

    def ask_user_sync(self, agent: str, question: str,
                      options: List[str] = None) -> str:
        """
        Block the sync Playwright thread until the user answers via WebSocket.
        Emits a 'question' event and waits up to 5 minutes.
        """
        self.status = "waiting_answer"
        self._pending_question = {"agent": agent, "question": question,
                                   "options": options or []}
        self._answer_event.clear()
        self._pending_answer = None
        self._update_agent(agent, status="waiting_answer",
                           current_task=f"Waiting for answer: {question[:50]}")
        self.emit("question", agent, question, data={"options": options or []})

        answered = self._answer_event.wait(timeout=300)
        self.status = "running"
        self._update_agent(agent, status="running")
        if not answered:
            return options[0] if options else "skip"
        return self._pending_answer or (options[0] if options else "skip")

    def receive_answer(self, answer: str) -> None:
        """Called by WebSocket handler when user submits an answer."""
        self._pending_answer = answer
        self._answer_event.set()

    def stop(self) -> None:
        """Signal the session to shut down — browser will close gracefully."""
        self._stop.set()
        self._answer_event.set()   # unblock any waiting ask_user_sync

    # ── Main entry point ───────────────────────────────────────────────────────

    async def run(self, max_pages: int = 25) -> None:
        """Start the full autonomous session in a background thread."""
        self.status = "running"
        # Capture the running event loop NOW (we're in async context).
        # The sync thread uses this to schedule WebSocket sends correctly.
        self._loop = asyncio.get_event_loop()
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                await self._loop.run_in_executor(ex, self._run_sync, max_pages)
        except Exception as e:
            self.status = "error"
            self.emit("error", "orchestrator", f"Session failed: {e}")
        finally:
            if self.status not in ("error", "waiting_answer"):
                self.status = "done"
            self._update_agent("orchestrator", status="done")
            self.emit("done", "orchestrator",
                      f"Session complete — {len(self.page_map)} pages explored",
                      data={
                          "page_count": len(self.page_map),
                          "agent_count": len(self.agents),
                          "summary": self.findings_summary,
                      })

    # ── Sync Playwright run (Windows compatible) ───────────────────────────────

    def _run_sync(self, max_pages: int) -> None:
        from playwright.sync_api import sync_playwright
        from src.utils.page_intelligence import dismiss_overlays_sync

        self._register_agent("orchestrator", "Orchestrator", "Team Lead — maps the entire application")
        self.emit("agent_start", "orchestrator", f"Launched — exploring {self.url}")
        self._update_agent("orchestrator", status="running")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=200,
                args=["--window-size=1280,800", "--window-position=50,50"],
            )
            context = browser.new_context(viewport={"width": 1280, "height": 768})
            page = context.new_page()

            # ── 1. Load the URL ────────────────────────────────────────────────
            self.emit("progress", "orchestrator", f"Navigating to {self.url}…")
            if not _safe_goto(page, self.url, self.emit):
                browser.close()
                return

            # ── 2. Dismiss overlays ────────────────────────────────────────────
            dismissed = dismiss_overlays_sync(page, timeout_ms=3000)
            if dismissed:
                self.emit("progress", "orchestrator", "Dismissed consent / cookie banner")
            _wait_for_stable(page, max_ms=3000)

            # Detect SSO redirect — note it but keep going
            current_host = urlparse(page.url).netloc
            _SSO_HOSTS = ("b2clogin.com", "microsoftonline.com", "okta.com",
                          "auth0.com", "onelogin.com", "accounts.google.com")
            if any(h in current_host for h in _SSO_HOSTS):
                self.emit("warning", "orchestrator",
                          f"Redirected to SSO login ({current_host}). "
                          "Landing page analysis will run on the auth page. "
                          "Provide credentials in the browser to continue crawling.")
                # Don't abort — analyse the SSO login page as-is

            # ── 3. Landing page screenshot ─────────────────────────────────────
            ss = _capture_screenshot(page)
            self.emit("screenshot", "orchestrator",
                      f"Home page loaded: {page.title() or self.url}",
                      screenshot=ss)

            # ── 4. Landing Page Agent ──────────────────────────────────────────
            self._register_agent("landing_page", "Landing Page Agent",
                                  "Validates UI, headings, links and accessibility")
            self._update_agent("landing_page", status="running")
            self.emit("agent_start", "landing_page",
                      "Activated — scanning UI elements")
            landing = self._analyze_landing_page(page)
            total_issues = len(landing["issues"])
            self._update_agent("landing_page", status="done",
                                findings=landing["issues"],
                                findings_count=total_issues,
                                current_task=f"{landing['element_count']} elements · {total_issues} issues")
            self.emit("finding", "landing_page",
                      f"Scan complete: {landing['element_count']} elements, "
                      f"{len(landing['links'])} links, {total_issues} issues found",
                      data=landing)

            # ── 5. Crawl all pages ─────────────────────────────────────────────
            self._update_agent("orchestrator", current_task="Crawling all pages…")
            self.emit("progress", "orchestrator", "Starting site crawl…")
            all_pages = self._crawl(page, dismiss_overlays_sync, max_pages)
            self.page_map = {p["url"]: p for p in all_pages}
            self.emit("progress", "orchestrator",
                      f"Crawl complete — {len(all_pages)} pages discovered",
                      data={"pages": [p["url"] for p in all_pages]})

            # ── 6. Identify features ───────────────────────────────────────────
            features = _identify_features(all_pages, self.url)
            self.emit("finding", "orchestrator",
                      f"Identified {len(features)} features: {', '.join(f.replace('_', ' ').title() for f in features)}",
                      data={"features": {k: len(v) for k, v in features.items()}})

            # ── 7. Spawn feature agents ────────────────────────────────────────
            for fname in features:
                display = fname.replace("_", " ").title()
                self._register_agent(fname, f"{display} Agent",
                                      f"Tests all {display} functionality")
                self.emit("agent_start", fname,
                          f"Assigned — {len(features[fname])} page(s) to analyse")

            # ── 8. Run each feature agent ──────────────────────────────────────
            issue_total = 0
            for fname, fpages in features.items():
                self._update_agent(fname, status="running",
                                   current_task="Analysing pages…")
                findings = self._run_feature_agent(page, fname, fpages)
                issue_total += len(findings)
                self._update_agent(fname, status="done",
                                   findings=findings,
                                   findings_count=len(findings),
                                   current_task=f"Done — {len(findings)} findings")

            # ── 9. Back home + final screenshot ───────────────────────────────
            try:
                _safe_goto(page, self.url, self.emit, timeout=15000)
                ss2 = _capture_screenshot(page)
                self.emit("screenshot", "orchestrator",
                          "Exploration complete — home page",
                          screenshot=ss2)
            except Exception:
                pass

            self.findings_summary = {
                "pages_explored": len(all_pages),
                "features_found": len(features),
                "agents_deployed": len(self.agents),
                "total_issues": issue_total + total_issues,
                "landing_issues": total_issues,
                "feature_list": list(features.keys()),
            }
            self._update_agent("orchestrator", status="done",
                                findings_count=len(all_pages),
                                current_task=f"Done — {len(all_pages)} pages, {len(features)} features")

            # ── Post-analysis: offer to explore authenticated pages ─────────────
            # If we only found 1 page (likely blocked by auth), ask user to log in
            if len(all_pages) <= 2:
                ans = self.ask_user_sync(
                    "orchestrator",
                    "I could only explore the login/landing page — the rest of the app "
                    "is behind authentication. Please log in manually in the browser "
                    "window, then click 'Continue exploring' to map the authenticated pages.",
                    ["Continue exploring", "Finish — analysis complete"],
                )
                if ans == "Continue exploring" and not self._stop.is_set():
                    self.emit("progress", "orchestrator",
                              "Resuming crawl in authenticated session…")
                    self._update_agent("orchestrator", status="running",
                                       current_task="Crawling authenticated pages…")
                    _wait_for_stable(page, max_ms=5000)
                    auth_pages = self._crawl(page, dismiss_overlays_sync, max_pages)
                    if auth_pages:
                        self.page_map.update({p["url"]: p for p in auth_pages})
                        auth_features = _identify_features(auth_pages, self.url)
                        self.emit("finding", "orchestrator",
                                  f"Authenticated crawl: {len(auth_pages)} pages, "
                                  f"{len(auth_features)} features",
                                  data={"features": {k: len(v) for k, v in auth_features.items()}})
                        for fname, fpages in auth_features.items():
                            if fname not in [a["name"] for a in self.agents]:
                                display = fname.replace("_", " ").title()
                                self._register_agent(fname, f"{display} Agent",
                                                      f"Tests {display} functionality")
                                self.emit("agent_start", fname,
                                          f"Spawned for authenticated {display} pages")
                            self._update_agent(fname, status="running",
                                               current_task="Analysing…")
                            findings = self._run_feature_agent(page, fname, fpages)
                            self._update_agent(fname, status="done",
                                               findings=findings,
                                               findings_count=len(findings),
                                               current_task=f"Done — {len(findings)} findings")
                        self.findings_summary["pages_explored"] = len(self.page_map)
                        self.findings_summary["features_found"] = len(auth_features)
                        self._update_agent("orchestrator", status="done",
                                           findings_count=len(self.page_map),
                                           current_task=f"Done — {len(self.page_map)} pages total")

            # ── Keep browser open until user clicks Stop ────────────────────────
            self.emit("progress", "orchestrator",
                      "Browser staying open for inspection — click Stop to close it")
            self._stop.wait()   # blocks until stop() is called (user clicks Stop)
            browser.close()

    # ── Landing page deep analysis ─────────────────────────────────────────────

    def _analyze_landing_page(self, page) -> Dict:
        result: Dict = {
            "element_count": 0, "links": [], "headings": [],
            "images": [], "forms": [], "nav_items": [],
            "cta_buttons": [], "issues": [],
        }
        try:
            # Full-page screenshot
            try:
                ss_full = page.screenshot(type="png", full_page=True)
                # Limit size to ~500KB base64
                if len(ss_full) > 375000:
                    ss_full = page.screenshot(type="png", full_page=False)
                self.emit("screenshot", "landing_page", "Full page captured",
                          screenshot=base64.b64encode(ss_full).decode())
            except Exception:
                pass

            # Links
            try:
                result["links"] = page.eval_on_selector_all("a[href]", """
                    els => els.map(e => ({
                        text: e.innerText.trim().slice(0,80),
                        href: e.href,
                        visible: e.offsetParent !== null
                    })).filter(l => l.visible && l.text)
                """)
            except Exception:
                pass

            # Headings
            try:
                result["headings"] = page.eval_on_selector_all("h1,h2,h3,h4", """
                    els => els.map(e => ({tag: e.tagName.toLowerCase(),
                                          text: e.innerText.trim().slice(0,200)}))
                    .filter(h => h.text)
                """)
            except Exception:
                pass

            # Images
            try:
                result["images"] = page.eval_on_selector_all("img", """
                    els => els.slice(0,30).map(e => ({
                        src: e.src.slice(0,80), alt: e.alt,
                        width: e.naturalWidth
                    }))
                """)
            except Exception:
                pass

            # Nav items
            try:
                result["nav_items"] = page.eval_on_selector_all(
                    "nav a, header a, [role='navigation'] a", """
                    els => els.map(e => ({text: e.innerText.trim().slice(0,60), href: e.href}))
                    .filter(n => n.text)
                """)
            except Exception:
                pass

            # CTA buttons
            try:
                result["cta_buttons"] = page.eval_on_selector_all(
                    "button, [role='button'], a.btn, a.button", """
                    els => els.slice(0,15).map(e => ({
                        text: e.innerText.trim().slice(0,60),
                        tag: e.tagName.toLowerCase()
                    })).filter(c => c.text)
                """)
            except Exception:
                pass

            # Forms
            try:
                result["forms"] = page.eval_on_selector_all("form", """
                    forms => forms.map(f => ({
                        action: f.action,
                        method: f.method,
                        inputs: Array.from(f.querySelectorAll('input')).map(i =>
                            ({type: i.type, name: i.name, placeholder: i.placeholder}))
                    }))
                """)
            except Exception:
                pass

            result["element_count"] = (len(result["links"]) + len(result["headings"])
                                        + len(result["cta_buttons"]))
            self.emit("progress", "landing_page",
                      f"{len(result['links'])} links, {len(result['headings'])} headings, "
                      f"{len(result['cta_buttons'])} CTA buttons found")

            # ── Issue checks ───────────────────────────────────────────────────

            # Missing alt text
            bad_imgs = [i for i in result["images"] if not i["alt"] and i.get("width", 0) > 50]
            if bad_imgs:
                result["issues"].append({
                    "type": "accessibility", "severity": "warning",
                    "message": f"{len(bad_imgs)} image(s) missing alt text",
                    "details": [i["src"][:60] for i in bad_imgs[:3]],
                })

            # No H1
            if not any(h["tag"] == "h1" for h in result["headings"]):
                result["issues"].append({
                    "type": "seo", "severity": "warning",
                    "message": "No H1 heading found — bad for SEO and accessibility",
                    "details": [],
                })
                self.emit("warning", "landing_page", "No H1 heading found")

            # Spell check headings
            for issue in _check_spelling(result["headings"]):
                result["issues"].append(issue)
                self.emit("warning", "landing_page", issue["message"])

            # Doubled words in headings
            for h in result["headings"]:
                words = h["text"].lower().split()
                for i in range(len(words) - 1):
                    if words[i] == words[i + 1] and len(words[i]) > 1:
                        result["issues"].append({
                            "type": "spelling", "severity": "warning",
                            "message": f"Doubled word '{words[i]}' in heading: \"{h['text'][:50]}\"",
                            "details": [],
                        })

            # Broken link sampling (up to 5 external/internal links)
            self.emit("progress", "landing_page", "Checking links for errors…")
            _check_broken_links(result["links"][:8], result["issues"], self.emit)

            # Console errors
            try:
                console_errors = page.evaluate("""
                    () => window.__testbounty_errors || []
                """) or []
                if console_errors:
                    result["issues"].append({
                        "type": "console", "severity": "error",
                        "message": f"{len(console_errors)} console error(s) detected",
                        "details": console_errors[:3],
                    })
            except Exception:
                pass

        except Exception as e:
            self.emit("error", "landing_page", f"Analysis error: {e}")
        return result

    # ── BFS page crawl ─────────────────────────────────────────────────────────

    def _crawl(self, page, dismiss_fn, max_pages: int) -> List[Dict]:
        visited: set = set()
        queue = [self.url]
        pages = []
        skip_exts = (".pdf", ".zip", ".png", ".jpg", ".jpeg", ".svg", ".ico",
                     ".gif", ".webp", ".woff", ".woff2", ".css", ".js")

        while queue and len(pages) < max_pages:
            url = queue.pop(0)
            # Normalise
            parsed = urlparse(url)
            clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if clean in visited:
                continue
            if parsed.netloc and parsed.netloc != self.domain:
                continue
            if any(clean.lower().endswith(e) for e in skip_exts):
                continue

            visited.add(clean)
            self.emit("progress", "orchestrator",
                      f"[{len(pages)+1}/{max_pages}] Visiting: {clean[:70]}…")
            try:
                _safe_goto(page, url, self.emit, timeout=20000)
                dismiss_fn(page, timeout_ms=1500)

                current_url = page.url
                title = page.title() or current_url

                # Extract interactive elements
                elements = []
                try:
                    elements = page.eval_on_selector_all(
                        "button,input,select,textarea,[role='button'],[role='link']",
                        """els => els.slice(0,60).map(e => ({
                            tag: e.tagName.toLowerCase(),
                            type: e.type || '',
                            id: e.id || '',
                            name: e.name || '',
                            text: (e.innerText||e.value||e.placeholder||'').trim().slice(0,60),
                            aria: e.getAttribute('aria-label')||'',
                            visible: e.offsetParent !== null
                        })).filter(e => e.visible)""",
                    )
                except Exception:
                    pass

                # Extract all links
                links = []
                try:
                    links = page.eval_on_selector_all(
                        "a[href]",
                        "els => els.map(e => e.href).filter(h => h.startsWith('http'))",
                    )
                except Exception:
                    pass

                # Screenshot only for meaningful pages (limit bandwidth)
                ss = None
                if len(pages) < 5 or len(pages) % 5 == 0:
                    ss = _capture_screenshot(page)
                    self.emit("screenshot", "orchestrator",
                              f"Page: {title[:50]}", screenshot=ss)

                pages.append({
                    "url": current_url,
                    "title": title,
                    "elements": elements,
                    "links": list(set(links)),
                    "element_count": len(elements),
                    "screenshot": ss,
                })

                # Queue new internal links
                for link in links:
                    lp = urlparse(link)
                    lc = f"{lp.scheme}://{lp.netloc}{lp.path}".rstrip("/")
                    if lp.netloc == self.domain and lc not in visited:
                        queue.append(link)

            except Exception as e:
                self.emit("warning", "orchestrator", f"Skipped {clean[:50]}: {e}")
        return pages

    # ── Feature agent ──────────────────────────────────────────────────────────

    def _run_feature_agent(self, page, fname: str,
                            fpages: List[Dict]) -> List[str]:
        display = fname.replace("_", " ").title()
        self.emit("progress", fname,
                  f"Reviewing {len(fpages)} page(s) for {display}…")
        findings: List[str] = []

        # Ask a smart question if we have one configured
        questions = _AGENT_QUESTIONS.get(fname, [])
        if questions:
            q = questions[0]
            answer = self.ask_user_sync(fname, q["q"], q["opts"])
            findings.append(f"User context: {answer}")
            self.emit("progress", fname, f"Got answer: {answer}")

        for fp in fpages[:3]:
            try:
                _safe_goto(page, fp["url"], self.emit, timeout=20000)

                ss = _capture_screenshot(page)
                self.emit("screenshot", fname,
                          f"Reviewing: {fp['title'][:40]}", screenshot=ss)

                elements = fp.get("elements", [])
                buttons = [e for e in elements
                           if e["tag"] == "button" or e.get("type") in ("submit", "button")]
                inputs = [e for e in elements
                          if e["tag"] in ("input", "textarea", "select")]

                # Check for existing error indicators
                try:
                    error_count = page.eval_on_selector_all(
                        ".error,.alert-danger,[role='alert'],.validation-error",
                        "els => els.filter(e => e.offsetParent !== null).length",
                    )
                    if error_count:
                        findings.append(
                            f"{fp['title'][:30]}: {error_count} error indicator(s) visible on load"
                        )
                        self.emit("warning", fname,
                                  f"Error indicators on {fp['title'][:30]}")
                except Exception:
                    pass

                if inputs:
                    finding = (f"{fp['title'][:30]}: {len(inputs)} input(s) — "
                               f"{', '.join(i['name'] or i['type'] for i in inputs[:3])}")
                    findings.append(finding)
                if buttons:
                    btn_labels = [b["text"] for b in buttons[:3] if b["text"]]
                    finding = (f"{fp['title'][:30]}: {len(buttons)} button(s) — "
                               f"{', '.join(btn_labels)}")
                    findings.append(finding)

                self.emit("finding", fname,
                          f"{fp['title'][:40]}: {len(elements)} elements",
                          data={"url": fp["url"], "inputs": len(inputs),
                                "buttons": len(buttons)})

            except Exception as e:
                self.emit("warning", fname,
                          f"Could not analyse {fp['url'][:40]}: {e}")

        self.emit("progress", fname, f"{display} Agent done — {len(findings)} finding(s)")
        return findings


# ── Utility functions ──────────────────────────────────────────────────────────

def _safe_goto(page, url: str, emit_fn, timeout: int = 60000) -> bool:
    """
    Navigate to a URL with a fully dynamic wait — no hardcoded sleeps.

    Strategy:
      1. Try wait_until="commit" (just needs first HTTP byte, handles redirects)
      2. If that times out, check page.url — browser may have landed somewhere
         useful mid-redirect (e.g. SSO page) → treat as success
      3. Dynamically poll document.readyState until interactive/complete
    """
    # ── Step 1: navigate ───────────────────────────────────────────────────────
    try:
        page.goto(url, wait_until="commit", timeout=min(timeout, 20000))
    except Exception as nav_err:
        # Even on timeout the browser may have navigated (SSO redirect chain)
        try:
            landed = page.url
            if landed and landed not in ("about:blank", "", url):
                emit_fn("warning", "orchestrator",
                        f"Slow redirect → landed on {urlparse(landed).netloc} — continuing")
            elif not landed or landed == "about:blank":
                emit_fn("error", "orchestrator",
                        f"Unreachable: {url[:60]} — {str(nav_err)[:80]}")
                return False
        except Exception:
            return False

    # ── Step 2: dynamic readiness poll ────────────────────────────────────────
    _wait_for_stable(page, max_ms=15000)
    return True


def _wait_for_stable(page, max_ms: int = 20000) -> None:
    """
    Poll document.readyState every 400 ms until the page is interactive or
    complete, or until max_ms is reached. Fully dynamic — adapts to page speed.
    """
    import time as _time
    deadline = _time.monotonic() + max_ms / 1000
    while _time.monotonic() < deadline:
        try:
            state = page.evaluate("document.readyState")
            if state in ("interactive", "complete"):
                # Give JS frameworks ~600 ms to mount after DOM is ready
                page.wait_for_timeout(600)
                return
        except Exception:
            pass
        page.wait_for_timeout(400)
    # Deadline reached — use whatever state the page is in


def _capture_screenshot(page) -> str:
    """Capture a compressed screenshot and return as base64 string."""
    try:
        raw = page.screenshot(type="jpeg", quality=55, full_page=False)
        return base64.b64encode(raw).decode()
    except Exception:
        try:
            raw = page.screenshot(type="png", full_page=False)
            return base64.b64encode(raw[:300000]).decode()
        except Exception:
            return ""


def _identify_features(pages: List[Dict], base_url: str) -> Dict[str, List[Dict]]:
    """Group pages into logical features based on URL patterns."""
    assigned: set = set()
    features: Dict[str, List[Dict]] = {}

    for fname, patterns in _FEATURE_PATTERNS.items():
        matched = [
            p for p in pages
            if any(pat in p["url"].lower() for pat in patterns)
            and p["url"] not in assigned
        ]
        if matched:
            features[fname] = matched
            for p in matched:
                assigned.add(p["url"])

    unassigned = [p for p in pages if p["url"] not in assigned]
    if unassigned:
        features["general"] = unassigned

    return features


def _check_spelling(headings: List[Dict]) -> List[Dict]:
    issues = []
    for h in headings:
        words = re.findall(r"[a-zA-Z]+", h.get("text", ""))
        for word in words:
            if word.lower() in _COMMON_TYPOS:
                issues.append({
                    "type": "spelling", "severity": "warning",
                    "message": (f"Possible typo in heading: '{word}' "
                                f"→ did you mean '{_COMMON_TYPOS[word.lower()]}'?"),
                    "details": h["text"][:60],
                })
    return issues


def _check_broken_links(links: List[Dict], issues: List[Dict], emit_fn) -> None:
    import urllib.request, ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    checked = 0
    for link in links:
        href = link.get("href", "")
        if not href.startswith("http") or checked >= 5:
            break
        try:
            req = urllib.request.Request(
                href, method="HEAD",
                headers={"User-Agent": "TestBountyBot/1.0"},
            )
            with urllib.request.urlopen(req, context=ctx, timeout=5):
                pass
        except urllib.error.HTTPError as e:
            if e.code >= 400:
                issues.append({
                    "type": "broken_link", "severity": "error",
                    "message": f"Broken link: '{link.get('text','')[:40]}' → HTTP {e.code}",
                    "details": href[:80],
                })
                emit_fn("warning", "landing_page",
                        f"Broken link: '{link.get('text','')[:30]}' returns {e.code}")
        except Exception:
            pass
        checked += 1
