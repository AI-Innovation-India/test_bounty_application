"""
Page Intelligence - Autonomous element finding and overlay dismissal.

Instead of relying on pre-stored selectors, these utilities scan the live DOM
and match elements by semantic intent (what the step is trying to do).
"""
from __future__ import annotations
import re
from typing import Optional

# ── Consent / cookie banner patterns ──────────────────────────────────────────
_CONSENT_SELECTORS = [
    # Text-based (most reliable)
    "button:has-text('Accept All')",
    "button:has-text('Accept all cookies')",
    "button:has-text('Accept Cookies')",
    "button:has-text('Accept')",
    "button:has-text('I Accept')",
    "button:has-text('Agree')",
    "button:has-text('Allow All')",
    "button:has-text('Allow all')",
    "button:has-text('OK')",
    "button:has-text('Got it')",
    "a:has-text('Accept All')",
    "a:has-text('Accept')",
    # ID/class based (common consent libraries)
    "#onetrust-accept-btn-handler",
    "#accept-cookies",
    "#cookie-accept",
    "#cookieAccept",
    ".cc-btn.cc-allow",
    ".cc-accept",
    "[id*='cookie-accept']",
    "[id*='accept-cookies']",
    "[id*='cookieConsent'] button",
    "[class*='cookie-accept']",
    "[class*='consent-accept']",
    "[class*='CookieConsent'] button",
    # Generic accept/continue on overlay modals
    "[role='dialog'] button:has-text('Accept')",
    "[role='dialog'] button:has-text('Continue')",
    "[role='alertdialog'] button:has-text('Accept')",
]

# ── Semantic keyword banks per intent ─────────────────────────────────────────
_INTENT_KEYWORDS = {
    "username": ["email", "user", "username", "login", "loginfmt", "i0116", "userid", "accountname"],
    "email":    ["email", "mail", "i0116", "loginfmt", "user"],
    "password": ["password", "passwd", "pass", "pwd", "i0118", "secret"],
    "submit":   ["submit", "signin", "sign-in", "login", "logon", "next", "continue", "proceed", "idsibutton9"],
    "search":   ["search", "query", "q", "find", "keyword"],
    "first_name": ["firstname", "first", "fname", "givenname"],
    "last_name":  ["lastname", "last", "lname", "surname", "familyname"],
    "phone":    ["phone", "mobile", "tel", "telephone", "cell"],
    "confirm_password": ["confirmpassword", "confirm", "repassword", "passwordconfirm", "verifypassword"],
}


def _score_element_attrs(attrs_text: str, keywords: list[str]) -> int:
    """Score how well an element's attributes match the given keywords."""
    score = 0
    a = attrs_text.lower()
    for kw in keywords:
        if kw in a:
            score += 10
    return score


_CLICK_SUBMIT_SIGNALS = [
    "login", "sign in", "signin", "log in", "logon", "submit", "continue",
    "next", "proceed", "send", "confirm", "authenticate", "enter",
]


def _infer_keywords(intent: str, action: str) -> list[str]:
    """Given a step description/intent, return the best keyword bank to use."""
    low = intent.lower()

    # For click actions: if description implies a primary/submit button, use submit bank
    if action == "click":
        if any(sig in low for sig in _CLICK_SUBMIT_SIGNALS):
            return _INTENT_KEYWORDS["submit"]

    # Check known intent keyword banks
    for intent_key, kws in _INTENT_KEYWORDS.items():
        if intent_key in low:
            return kws

    # Fallback: split the description into words and use them directly
    words = re.findall(r"[a-z]+", low)
    return words


def dismiss_overlays_sync(page, timeout_ms: int = 2500) -> bool:
    """
    Try to dismiss cookie consent banners and modal overlays.
    Returns True if something was dismissed, False if nothing found.
    Non-fatal — safe to call even when no overlay is present.
    """
    for selector in _CONSENT_SELECTORS:
        try:
            elem = page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            if elem:
                elem.click()
                page.wait_for_timeout(800)
                print(f"[PageIntel] Dismissed overlay via: {selector}")
                return True
        except Exception:
            continue
    return False


async def dismiss_overlays_async(page, timeout_ms: int = 2500) -> bool:
    """Async version of dismiss_overlays_sync."""
    for selector in _CONSENT_SELECTORS:
        try:
            elem = await page.wait_for_selector(selector, state="visible", timeout=timeout_ms)
            if elem:
                await elem.click()
                await page.wait_for_timeout(800)
                print(f"[PageIntel] Dismissed overlay via: {selector}")
                return True
        except Exception:
            continue
    return False


def smart_find_sync(page, intent: str, action: str) -> Optional[str]:
    """
    Scan the live DOM to find the best matching element for the given intent.

    intent  — the step description, e.g. "Enter email address" or "Click sign in button"
    action  — "fill" | "click"

    Returns a CSS selector string, or None if nothing confident found.
    """
    keywords = _infer_keywords(intent, action)
    if not keywords:
        return None

    try:
        if action == "fill":
            candidates = page.query_selector_all("input:not([type='hidden']):not([type='submit']):not([type='button']), textarea")
        else:
            candidates = page.query_selector_all("button, input[type='submit'], input[type='button'], a[href]")
    except Exception:
        return None

    best_selector = None
    best_score = 0

    for elem in candidates:
        try:
            if not elem.is_visible():
                continue

            e_id    = elem.get_attribute("id") or ""
            e_name  = elem.get_attribute("name") or ""
            e_type  = elem.get_attribute("type") or ""
            e_ph    = elem.get_attribute("placeholder") or ""
            e_aria  = elem.get_attribute("aria-label") or ""
            e_cls   = elem.get_attribute("class") or ""
            e_text  = (elem.inner_text() or "")[:80]
            e_val   = elem.get_attribute("value") or ""

            attrs = " ".join([e_id, e_name, e_type, e_ph, e_aria, e_cls, e_text, e_val])
            score = _score_element_attrs(attrs, keywords)

            # Type-specific bonuses
            if action == "fill":
                if e_type == "password" and any(k in ["password", "passwd", "pass", "pwd"] for k in keywords):
                    score += 15
                if e_type in ("email", "text") and any(k in ["email", "user", "username", "loginfmt"] for k in keywords):
                    score += 8
            else:  # click
                if e_type == "submit":
                    score += 5

            if score > best_score:
                best_score = score
                # Prefer stable selectors: id > name > type+placeholder
                if e_id:
                    best_selector = f"#{e_id}"
                elif e_name:
                    best_selector = f"[name='{e_name}']"
                elif e_type and e_type not in ("text", "button"):
                    best_selector = f"input[type='{e_type}']"
                elif e_ph:
                    best_selector = f"[placeholder='{e_ph}']"
                elif e_aria:
                    best_selector = f"[aria-label='{e_aria}']"
                else:
                    best_selector = None
        except Exception:
            continue

    if best_score >= 8 and best_selector:
        print(f"[PageIntel] smart_find: intent='{intent}' → {best_selector} (score={best_score})")
        return best_selector

    return None


async def smart_find_async(page, intent: str, action: str) -> Optional[str]:
    """Async version of smart_find_sync."""
    keywords = _infer_keywords(intent, action)
    if not keywords:
        return None

    try:
        if action == "fill":
            candidates = await page.query_selector_all("input:not([type='hidden']):not([type='submit']):not([type='button']), textarea")
        else:
            candidates = await page.query_selector_all("button, input[type='submit'], input[type='button'], a[href]")
    except Exception:
        return None

    best_selector = None
    best_score = 0

    for elem in candidates:
        try:
            if not await elem.is_visible():
                continue

            e_id    = await elem.get_attribute("id") or ""
            e_name  = await elem.get_attribute("name") or ""
            e_type  = await elem.get_attribute("type") or ""
            e_ph    = await elem.get_attribute("placeholder") or ""
            e_aria  = await elem.get_attribute("aria-label") or ""
            e_cls   = await elem.get_attribute("class") or ""
            e_text  = (await elem.inner_text() or "")[:80]
            e_val   = await elem.get_attribute("value") or ""

            attrs = " ".join([e_id, e_name, e_type, e_ph, e_aria, e_cls, e_text, e_val])
            score = _score_element_attrs(attrs, keywords)

            if action == "fill":
                if e_type == "password" and any(k in ["password", "passwd", "pass", "pwd"] for k in keywords):
                    score += 15
                if e_type in ("email", "text") and any(k in ["email", "user", "username", "loginfmt"] for k in keywords):
                    score += 8
            else:
                if e_type == "submit":
                    score += 5

            if score > best_score:
                best_score = score
                if e_id:
                    best_selector = f"#{e_id}"
                elif e_name:
                    best_selector = f"[name='{e_name}']"
                elif e_type and e_type not in ("text", "button"):
                    best_selector = f"input[type='{e_type}']"
                elif e_ph:
                    best_selector = f"[placeholder='{e_ph}']"
                elif e_aria:
                    best_selector = f"[aria-label='{e_aria}']"
                else:
                    best_selector = None
        except Exception:
            continue

    if best_score >= 8 and best_selector:
        print(f"[PageIntel] smart_find_async: intent='{intent}' → {best_selector} (score={best_score})")
        return best_selector

    return None


def extract_real_form_fields_sync(page) -> list[dict]:
    """
    Extract actual form fields from the current page DOM.
    Returns list of {name, type, selector, placeholder, required}.
    Used by the explorer to record REAL selectors, not guesses.
    """
    fields = []
    try:
        inputs = page.query_selector_all("input:not([type='hidden']):not([type='submit']):not([type='button'])")
        for inp in inputs:
            try:
                if not inp.is_visible():
                    continue
                e_id   = inp.get_attribute("id") or ""
                e_name = inp.get_attribute("name") or ""
                e_type = inp.get_attribute("type") or "text"
                e_ph   = inp.get_attribute("placeholder") or ""
                e_req  = inp.get_attribute("required") is not None
                e_aria = inp.get_attribute("aria-label") or ""

                selector = f"#{e_id}" if e_id else (f"[name='{e_name}']" if e_name else f"input[type='{e_type}']")
                fields.append({
                    "name": e_name or e_id or e_type,
                    "type": e_type,
                    "selector": selector,
                    "placeholder": e_ph or e_aria,
                    "required": e_req,
                })
            except Exception:
                continue
    except Exception:
        pass
    return fields


def extract_submit_selector_sync(page) -> str:
    """Find the submit/primary-action button on the current page."""
    candidates = [
        "input[type='submit']",
        "button[type='submit']",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
        "button:has-text('Login')",
        "button:has-text('Next')",
        "button:has-text('Continue')",
        "#idSIButton9",
        "[id*='submit']",
        "[id*='login']",
        "[id*='signin']",
    ]
    for sel in candidates:
        try:
            elem = page.wait_for_selector(sel, state="visible", timeout=2000)
            if elem:
                e_id = elem.get_attribute("id") or ""
                e_name = elem.get_attribute("name") or ""
                return f"#{e_id}" if e_id else sel
        except Exception:
            continue
    return "button[type='submit'], input[type='submit']"


# ══════════════════════════════════════════════════════════════════════════════
# LAYER 4 — VISION-BASED ELEMENT FINDING
# Takes a screenshot → sends to vision LLM → gets pixel coordinates back.
# Works on ANY page without knowing the DOM structure.
# Used as last resort when layers 1-3 all fail.
# ══════════════════════════════════════════════════════════════════════════════

_VISION_PROMPT = """You are analyzing a browser screenshot to locate a UI element.

Viewport: {width} x {height} pixels.

Find the element that best matches this description: "{description}"

Rules:
- Return the EXACT pixel coordinates of the CENTER of the element
- x must be between 0 and {width}
- y must be between 0 and {height}
- Confidence: high (clearly visible), medium (likely correct), low (best guess)

Return ONLY valid JSON — no markdown, no explanation:
{{"found": true, "x": <int>, "y": <int>, "confidence": "high|medium|low", "what_i_found": "<brief description>"}}

If you cannot find the element:
{{"found": false, "x": null, "y": null, "confidence": "none", "what_i_found": "not found"}}"""


def _call_vision_gemini(screenshot_bytes: bytes, prompt: str) -> Optional[dict]:
    """Call Google Gemini vision API."""
    import os
    import json as _json
    import io
    try:
        import google.generativeai as genai
        import PIL.Image
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        # Try models in order of preference
        for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro-vision", "gemini-1.5-pro"]:
            try:
                model = genai.GenerativeModel(model_name)
                img = PIL.Image.open(io.BytesIO(screenshot_bytes))
                response = model.generate_content([prompt, img])
                content = response.text.strip().replace("```json", "").replace("```", "").strip()
                return _json.loads(content)
            except Exception as e:
                if "quota" in str(e).lower() or "429" in str(e):
                    continue  # try next model
                raise
    except Exception as e:
        print(f"[Vision/Gemini] {e}")
    return None


def _call_vision_anthropic(screenshot_bytes: bytes, prompt: str) -> Optional[dict]:
    """Call Anthropic Claude vision API."""
    import os
    import json as _json
    import base64
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        b64 = base64.standard_b64encode(screenshot_bytes).decode("utf-8")
        msg = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        content = msg.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        return _json.loads(content)
    except Exception as e:
        print(f"[Vision/Claude] {e}")
    return None


def _call_vision_openai(screenshot_bytes: bytes, prompt: str) -> Optional[dict]:
    """Call OpenAI GPT-4 Vision API."""
    import os
    import json as _json
    import base64
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        b64 = base64.standard_b64encode(screenshot_bytes).decode("utf-8")
        resp = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=256,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        content = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        return _json.loads(content)
    except Exception as e:
        print(f"[Vision/OpenAI] {e}")
    return None


def _call_vision_azure(screenshot_bytes: bytes, prompt: str) -> Optional[dict]:
    """Call Azure OpenAI vision API."""
    import os, json as _json, base64
    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01"),
        )
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        b64 = base64.standard_b64encode(screenshot_bytes).decode("utf-8")
        resp = client.chat.completions.create(
            model=deployment,
            max_tokens=256,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}},
                {"type": "text", "text": prompt},
            ]}],
        )
        content = resp.choices[0].message.content.strip().replace("```json", "").replace("```", "").strip()
        return _json.loads(content)
    except Exception as e:
        print(f"[Vision/Azure] {e}")
    return None


def _vision_call(screenshot_bytes: bytes, prompt: str) -> Optional[dict]:
    """Try each available vision provider in order: Azure → Anthropic → Gemini → OpenAI."""
    import os
    if os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY"):
        result = _call_vision_azure(screenshot_bytes, prompt)
        if result:
            return result
    if os.getenv("ANTHROPIC_API_KEY"):
        result = _call_vision_anthropic(screenshot_bytes, prompt)
        if result:
            return result
    if os.getenv("GOOGLE_API_KEY"):
        result = _call_vision_gemini(screenshot_bytes, prompt)
        if result:
            return result
    if os.getenv("OPENAI_API_KEY"):
        result = _call_vision_openai(screenshot_bytes, prompt)
        if result:
            return result
    return None


def vision_find_sync(page, description: str, min_confidence: str = "medium") -> Optional[tuple]:
    """
    Layer 4: Screenshot → vision model → pixel coordinates.

    Returns (x, y) tuple for page.mouse.click(), or None if not found / low confidence.
    Works on any page, any framework, any language — pure visual understanding.
    """
    _CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "none": 0}
    min_rank = _CONFIDENCE_RANK.get(min_confidence, 2)

    try:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        screenshot_bytes = page.screenshot(type="png")

        prompt = _VISION_PROMPT.format(
            width=viewport["width"],
            height=viewport["height"],
            description=description,
        )

        result = _vision_call(screenshot_bytes, prompt)
        if not result:
            return None

        if not result.get("found"):
            print(f"[Vision] '{description}' not found on page")
            return None

        confidence = result.get("confidence", "none")
        if _CONFIDENCE_RANK.get(confidence, 0) < min_rank:
            print(f"[Vision] '{description}' found but confidence too low: {confidence}")
            return None

        x, y = int(result["x"]), int(result["y"])
        print(f"[Vision] '{description}' → ({x}, {y}) [{confidence}] — {result.get('what_i_found', '')}")
        return (x, y)

    except Exception as e:
        print(f"[Vision] Error: {e}")
        return None


async def vision_find_async(page, description: str, min_confidence: str = "medium") -> Optional[tuple]:
    """Async version — runs vision call in thread pool to avoid blocking the event loop."""
    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    def _sync_capture():
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        return page.screenshot(type="png"), viewport

    # Screenshots in playwright async don't need thread, but vision calls do
    try:
        viewport = page.viewport_size or {"width": 1280, "height": 720}
        screenshot_bytes = await page.screenshot(type="png")

        prompt = _VISION_PROMPT.format(
            width=viewport["width"],
            height=viewport["height"],
            description=description,
        )

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=1) as ex:
            result = await loop.run_in_executor(ex, _vision_call, screenshot_bytes, prompt)

        if not result or not result.get("found"):
            return None

        _CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1, "none": 0}
        if _CONFIDENCE_RANK.get(result.get("confidence", "none"), 0) < 2:
            return None

        x, y = int(result["x"]), int(result["y"])
        print(f"[Vision] async '{description}' → ({x}, {y}) [{result.get('confidence')}]")
        return (x, y)

    except Exception as e:
        print(f"[Vision] async error: {e}")
        return None


def vision_dismiss_overlays_sync(page) -> bool:
    """
    Vision-powered consent/overlay dismissal.
    Finds ANY Accept/Close/Continue button visually — works on custom dialogs
    that don't match standard CSS patterns.
    """
    coords = vision_find_sync(
        page,
        "cookie consent Accept button, privacy notice OK button, or modal close/continue button",
        min_confidence="medium",
    )
    if coords:
        page.mouse.click(*coords)
        page.wait_for_timeout(800)
        print(f"[Vision] Dismissed overlay at {coords}")
        return True
    return False


def take_debug_screenshot(page, label: str = "debug") -> str:
    """Save a debug screenshot and return the path. Useful for diagnosing vision failures."""
    import os, datetime
    path = os.path.join("temp_runs", "debug", f"{label}_{datetime.datetime.now().strftime('%H%M%S')}.png")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    page.screenshot(path=path, type="png")
    return path
