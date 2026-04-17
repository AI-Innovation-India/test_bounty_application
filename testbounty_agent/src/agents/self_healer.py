"""
Self-Healing Agent — Automatically repairs broken test selectors.

When a Playwright step fails because a selector no longer exists or
has changed, this agent attempts to find a working replacement:

  1. Rule-based healing  (fast, zero LLM cost)  — tries common
     fallback patterns based on the step's semantic description.
  2. LLM-based healing   (accurate, uses LLM)   — sends the page
     HTML + broken selector to the LLM for intelligent analysis.

Healed steps carry meta-fields so the audit trail is clear:
  _healed            = True
  _original_selector = <what was broken>
  _heal_method       = "rule_based" | "llm"
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Patterns used for rule-based healing
# ---------------------------------------------------------------------------

_EMAIL_SELECTORS = [
    "input[type='email']",
    "input[name='email']",
    "input[name='Email']",
    "input[name='username']",
    "input[name='UserName']",
    "#Email",
    "#email",
    "#UserName",
    "input[placeholder*='email' i]",
    "input[placeholder*='username' i]",
]

_PASSWORD_SELECTORS = [
    "input[type='password']",
    "input[name='password']",
    "input[name='Password']",
    "#Password",
    "#password",
    "input[placeholder*='password' i]",
]

_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Login')",
    "button:has-text('Sign In')",
    "button:has-text('Submit')",
    "button:has-text('Register')",
    "button:has-text('Create')",
    ".btn-login",
    ".btn-submit",
    "#loginButton",
    "#submitBtn",
    "form button",
]

_NAME_SELECTORS = [
    "input[name='name']",
    "input[name='fullname']",
    "input[name='full_name']",
    "input[name='FirstName']",
    "input[name='lastName']",
    "#FirstName",
    "#fullName",
    "input[placeholder*='name' i]",
]


class SelfHealerAgent:
    """
    Detects and repairs broken test-step selectors at run-time.
    """

    def __init__(self, llm_service=None):
        self.llm = llm_service
        self._heal_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def heal_selector(
        self,
        failed_step: Dict[str, Any],
        page_html: str,
        page_url: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Try to fix a failed step's selector.

        Returns an updated step dict on success, or None if healing failed.
        """
        broken = failed_step.get("target", "")
        action = failed_step.get("action", "")
        description = (failed_step.get("description") or "").lower()

        if not broken or action not in ("click", "fill", "assert"):
            return None

        # 1 — Rule-based (fast)
        healed, method = self._rule_based_heal(broken, page_html, description)

        # 2 — LLM-based (fallback)
        if not healed and self.llm and getattr(self.llm, "provider", "mock") != "mock":
            healed = self._llm_heal(broken, page_html, description, action)
            method = "llm" if healed else None

        if healed:
            step = dict(failed_step)
            step["target"] = healed
            step["_healed"] = True
            step["_original_selector"] = broken
            step["_heal_method"] = method
            self._heal_log.append({
                "url": page_url,
                "original_selector": broken,
                "healed_selector": healed,
                "method": method,
                "description": description,
            })
            return step

        return None

    def get_heal_summary(self) -> Dict[str, Any]:
        """Return a summary of all heals performed in this session."""
        return {
            "total_healed": len(self._heal_log),
            "heals": self._heal_log,
        }

    # ------------------------------------------------------------------
    # Rule-based healing
    # ------------------------------------------------------------------

    def _rule_based_heal(
        self, broken: str, html: str, description: str
    ) -> tuple[Optional[str], str]:
        """
        Fast, zero-cost healing using pattern matching on the description
        and a quick membership check against the raw page HTML.
        """
        candidates: List[str] = []

        # Derive candidates from semantic description
        if any(k in description for k in ("email", "username", "user name")):
            candidates.extend(_EMAIL_SELECTORS)
        if "password" in description:
            candidates.extend(_PASSWORD_SELECTORS)
        if any(k in description for k in ("submit", "login", "sign in", "register")):
            candidates.extend(_SUBMIT_SELECTORS)
        if any(k in description for k in ("name", "full name", "first name")):
            candidates.extend(_NAME_SELECTORS)

        # If broken selector is an #id, also try [name=...] variant
        if broken.startswith("#"):
            field_id = broken[1:]
            candidates = [
                f"[name='{field_id}']",
                f"input[id*='{field_id}']",
                f"[placeholder*='{field_id}' i]",
            ] + candidates

        # Pick the first candidate that literally appears in the HTML
        for sel in candidates:
            # Quick membership test — not perfect but fast
            probe = sel.strip("[]").replace("=", "=\"").rstrip("\"") + "\""
            if any(token in html for token in [
                sel,
                probe,
                sel.replace("'", '"'),
            ]):
                return sel, "rule_based"

        # No HTML match — return best semantic guess anyway
        if candidates:
            return candidates[0], "rule_based_guess"

        return None, ""

    # ------------------------------------------------------------------
    # LLM-based healing
    # ------------------------------------------------------------------

    def _llm_heal(
        self,
        broken: str,
        html: str,
        description: str,
        action: str,
    ) -> Optional[str]:
        """
        Ask the LLM to find the best working selector given the page HTML.
        """
        # Truncate HTML to keep token cost low
        snippet = html[:4000] if len(html) > 4000 else html

        prompt = (
            "You are a Playwright test-automation expert.\n"
            "A test step has a broken CSS selector. Find the best replacement.\n\n"
            f"BROKEN SELECTOR : {broken}\n"
            f"STEP ACTION     : {action}\n"
            f"STEP DESCRIPTION: {description}\n\n"
            "PAGE HTML (truncated):\n"
            f"{snippet}\n\n"
            "Rules:\n"
            "- Prefer #id over [name=...] over class selectors\n"
            "- Selector must be valid Playwright/CSS\n"
            "- Return ONLY the selector string — no explanation, no quotes"
        )

        try:
            response = self.llm.model.invoke(prompt)
            raw = getattr(response, "content", str(response)).strip().strip('"').strip("'")
            return raw if raw else None
        except Exception:
            return None


# ------------------------------------------------------------------
# Convenience constructor
# ------------------------------------------------------------------

def create_self_healer(llm_service=None) -> SelfHealerAgent:
    """Create and return a SelfHealerAgent instance."""
    return SelfHealerAgent(llm_service)
