"""
StoryParserAgent — converts raw user stories / acceptance criteria into test scenarios.

Supports:
  - Plain text (each line / paragraph = one story)
  - Gherkin (Given/When/Then)
  - Jira-style "As a <role> I want to <action> so that <benefit>"
  - Bullet lists of features/requirements
"""

from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional


# ── Helpers ───────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def _extract_gherkin_scenarios(text: str) -> List[Dict]:
    """Parse Gherkin feature files into raw scenario dicts."""
    scenarios = []
    current: Optional[Dict] = None

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("scenario"):
            if current:
                scenarios.append(current)
            name = re.sub(r"^scenario[^:]*:\s*", "", stripped, flags=re.IGNORECASE)
            current = {"name": name, "steps": [], "raw": stripped}
        elif current and stripped.lower().startswith(("given", "when", "then", "and", "but")):
            current["steps"].append(stripped)

    if current:
        scenarios.append(current)

    return scenarios


def _steps_from_gherkin(raw_steps: List[str]) -> List[Dict]:
    """Convert Gherkin step list to TestStep-like dicts."""
    steps = []
    for s in raw_steps:
        lower = s.lower()
        if lower.startswith("given") or lower.startswith("when"):
            if "navigate" in lower or "go to" in lower or "visit" in lower or "open" in lower:
                url_match = re.search(r'https?://\S+|"([^"]+)"', s)
                target = url_match.group(0).strip('"') if url_match else "navigate to page"
                steps.append({"action": "navigate", "target": target, "value": None, "description": s})
            elif "login" in lower or "sign in" in lower:
                steps.append({"action": "navigate", "target": "/login", "value": None, "description": s})
            elif "fill" in lower or "enter" in lower or "type" in lower:
                steps.append({"action": "fill", "target": "input", "value": "", "description": s})
            elif "click" in lower or "press" in lower or "tap" in lower:
                steps.append({"action": "click", "target": "button", "value": None, "description": s})
            else:
                steps.append({"action": "navigate", "target": "/", "value": None, "description": s})
        elif lower.startswith("then") or lower.startswith("and") or lower.startswith("but"):
            if "see" in lower or "visible" in lower or "display" in lower or "show" in lower:
                steps.append({"action": "assert", "target": "element_visible", "value": None, "description": s})
            elif "redirect" in lower or "url" in lower or "navigate" in lower:
                steps.append({"action": "assert", "target": "url_changed", "value": None, "description": s})
            elif "error" in lower or "invalid" in lower or "fail" in lower:
                steps.append({"action": "assert", "target": "error_message_visible", "value": None, "description": s})
            else:
                steps.append({"action": "assert", "target": "element_visible", "value": None, "description": s})

    return steps


# ── Main Agent ────────────────────────────────────────────────────────────────

class StoryParserAgent:
    """
    Converts user stories / acceptance criteria into TestBounty scenarios.

    Usage:
        agent = StoryParserAgent(llm_service=llm)
        scenarios = agent.parse(stories_text, base_url="https://myapp.com")
    """

    def __init__(self, llm_service=None):
        self.llm = llm_service

    # ── Public API ────────────────────────────────────────────────────────────

    def parse(self, stories_text: str, base_url: str = "/", existing_modules: List[str] = None) -> Dict:
        """
        Parse stories text → { modules: { module_name: { scenarios: [...] } }, total_scenarios: N }
        """
        if not stories_text or not stories_text.strip():
            return {"modules": {}, "total_scenarios": 0}

        # Detect format
        is_gherkin = bool(re.search(r"^\s*(scenario|feature|given|when|then)\b", stories_text, re.IGNORECASE | re.MULTILINE))

        if self.llm and getattr(self.llm, "provider", "mock") != "mock":
            try:
                return self._llm_parse(stories_text, base_url, is_gherkin)
            except Exception as e:
                print(f"[StoryParser] LLM parse failed ({e}), falling back to rule-based")

        if is_gherkin:
            return self._gherkin_parse(stories_text, base_url)
        else:
            return self._rule_based_parse(stories_text, base_url)

    # ── LLM parse ─────────────────────────────────────────────────────────────

    def _llm_parse(self, text: str, base_url: str, is_gherkin: bool) -> Dict:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        prompt = ChatPromptTemplate.from_template("""
You are a senior QA engineer. Convert the following user stories / acceptance criteria into structured test scenarios for a web application at {base_url}.

INPUT STORIES:
{stories}

OUTPUT RULES:
- Group scenarios by module (auth, dashboard, checkout, etc.)
- Each scenario must have: id, name, description, module, type (happy_path/error_path/edge_case), priority (high/medium/low), steps
- Each step must have: action (navigate/click/fill/assert/wait), target (CSS selector or URL), value (optional), description
- Use realistic CSS selectors based on story context
- Include both happy path and error cases
- Return ONLY valid JSON, no markdown

JSON FORMAT:
{{
  "modules": {{
    "module_name": {{
      "name": "Module Name",
      "requires_auth": false,
      "scenarios": [
        {{
          "id": "mod_001",
          "name": "...",
          "description": "...",
          "module": "module_name",
          "type": "happy_path",
          "priority": "high",
          "depends_on": null,
          "steps": [
            {{"action": "navigate", "target": "{base_url}/page", "value": null, "description": "..."}}
          ],
          "status": "pending"
        }}
      ]
    }}
  }},
  "total_scenarios": 0
}}
""")

        chain = prompt | self.llm.model | StrOutputParser()
        response = chain.invoke({"stories": text[:4000], "base_url": base_url})
        response = response.replace("```json", "").replace("```", "").strip()
        result = json.loads(response)

        # Count scenarios
        total = sum(
            len(m.get("scenarios", []))
            for m in result.get("modules", {}).values()
        )
        result["total_scenarios"] = total
        result["source"] = "user_stories"
        return result

    # ── Gherkin parse ─────────────────────────────────────────────────────────

    def _gherkin_parse(self, text: str, base_url: str) -> Dict:
        raw_scenarios = _extract_gherkin_scenarios(text)
        modules: Dict[str, Any] = {}

        for i, raw in enumerate(raw_scenarios):
            name = raw["name"]
            module = self._infer_module(name)

            steps = _steps_from_gherkin(raw["steps"])
            if not steps:
                steps = [{"action": "navigate", "target": base_url, "value": None, "description": "Open application"}]

            scenario_id = f"{_slugify(module)}_{i+1:03d}"
            scenario = {
                "id": scenario_id,
                "name": name,
                "description": f"Gherkin scenario: {name}",
                "module": module,
                "type": "happy_path" if "invalid" not in name.lower() and "error" not in name.lower() else "error_path",
                "priority": "high",
                "depends_on": None,
                "steps": steps,
                "status": "pending",
                "source": "gherkin",
            }

            if module not in modules:
                modules[module] = {"name": module.title(), "requires_auth": False, "scenarios": []}
            modules[module]["scenarios"].append(scenario)

        total = sum(len(m["scenarios"]) for m in modules.values())
        return {"modules": modules, "total_scenarios": total, "source": "user_stories"}

    # ── Rule-based parse ──────────────────────────────────────────────────────

    def _rule_based_parse(self, text: str, base_url: str) -> Dict:
        """Parse plain English stories line by line."""
        modules: Dict[str, Any] = {}
        stories = self._split_stories(text)

        for i, story in enumerate(stories):
            story = story.strip()
            if not story or len(story) < 10:
                continue

            module = self._infer_module(story)
            steps = self._steps_from_story(story, base_url)

            scenario_id = f"{_slugify(module)}_{i+1:03d}"
            is_error = any(w in story.lower() for w in ["invalid", "wrong", "error", "fail", "reject", "deny", "empty", "missing"])

            scenario = {
                "id": scenario_id,
                "name": self._story_to_name(story),
                "description": story,
                "module": module,
                "type": "error_path" if is_error else "happy_path",
                "priority": "high" if any(w in story.lower() for w in ["login", "register", "checkout", "payment", "auth"]) else "medium",
                "depends_on": None,
                "steps": steps,
                "status": "pending",
                "source": "user_stories",
            }

            if module not in modules:
                modules[module] = {"name": module.replace("_", " ").title(), "requires_auth": False, "scenarios": []}
            modules[module]["scenarios"].append(scenario)

        total = sum(len(m["scenarios"]) for m in modules.values())
        return {"modules": modules, "total_scenarios": total, "source": "user_stories"}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _split_stories(self, text: str) -> List[str]:
        """Split text into individual story units."""
        # Split on numbered lists, bullet points, or double newlines
        parts = re.split(r"\n(?:\d+[\.\)]\s+|\-\s+|\*\s+|•\s+)|(?:\n\n)+", text)
        return [p.strip() for p in parts if p.strip()]

    def _story_to_name(self, story: str) -> str:
        """Extract a short test name from a story sentence."""
        # Remove "As a X I want to" prefix
        story = re.sub(r"as an?\s+\w+[,\s]+i\s+(?:want|should|can)\s+(?:to\s+)?", "", story, flags=re.IGNORECASE)
        # Remove "so that..." suffix
        story = re.sub(r"\s+so that.*$", "", story, flags=re.IGNORECASE)
        # Capitalize first word
        story = story.strip().capitalize()
        # Truncate
        return story[:80] if len(story) > 80 else story

    def _infer_module(self, text: str) -> str:
        lower = text.lower()
        if any(w in lower for w in ["login", "logout", "sign in", "sign out", "password", "auth", "register", "forgot"]):
            return "auth"
        if any(w in lower for w in ["cart", "basket", "checkout", "order", "payment", "purchase", "buy"]):
            return "checkout"
        if any(w in lower for w in ["search", "filter", "sort", "find", "browse"]):
            return "search"
        if any(w in lower for w in ["profile", "account", "settings", "preferences", "update user"]):
            return "profile"
        if any(w in lower for w in ["product", "item", "catalog", "listing", "detail"]):
            return "products"
        if any(w in lower for w in ["dashboard", "home", "landing", "overview"]):
            return "dashboard"
        if any(w in lower for w in ["admin", "manage", "user management", "role"]):
            return "admin"
        if any(w in lower for w in ["notification", "alert", "email", "message"]):
            return "notifications"
        return "general"

    def _steps_from_story(self, story: str, base_url: str) -> List[Dict]:
        """Generate minimal Playwright steps from a plain story."""
        lower = story.lower()
        steps = []

        # Navigate step
        if "login" in lower or "sign in" in lower:
            steps.append({"action": "navigate", "target": f"{base_url}/login", "value": None, "description": "Go to login page"})
            steps.append({"action": "fill", "target": "input[type='email'], #email, input[name='email']", "value": "testuser@example.com", "description": "Enter email"})
            steps.append({"action": "fill", "target": "input[type='password'], #password", "value": "TestPassword123!", "description": "Enter password"})
            steps.append({"action": "click", "target": "button[type='submit'], .login-button, button:has-text('Login')", "value": None, "description": "Click login"})
        elif "register" in lower or "sign up" in lower:
            steps.append({"action": "navigate", "target": f"{base_url}/register", "value": None, "description": "Go to registration"})
            steps.append({"action": "fill", "target": "input[name='email'], #email", "value": "newuser@example.com", "description": "Enter email"})
            steps.append({"action": "fill", "target": "input[name='password'], #password", "value": "NewPass123!", "description": "Enter password"})
            steps.append({"action": "click", "target": "button[type='submit']", "value": None, "description": "Submit registration"})
        elif "search" in lower:
            steps.append({"action": "navigate", "target": base_url, "value": None, "description": "Go to home page"})
            steps.append({"action": "fill", "target": "input[type='search'], .search-input, #search", "value": "test query", "description": "Enter search query"})
            steps.append({"action": "click", "target": ".search-button, button[type='submit']", "value": None, "description": "Submit search"})
        elif "checkout" in lower or "cart" in lower:
            steps.append({"action": "navigate", "target": f"{base_url}/cart", "value": None, "description": "Go to cart"})
            steps.append({"action": "click", "target": ".checkout-button, button:has-text('Checkout')", "value": None, "description": "Proceed to checkout"})
        else:
            steps.append({"action": "navigate", "target": base_url, "value": None, "description": "Navigate to application"})

        # Assert step based on story type
        is_error = any(w in lower for w in ["invalid", "wrong", "error", "fail", "empty", "missing"])
        if is_error:
            steps.append({"action": "assert", "target": "error_message_visible", "value": None, "description": "Verify error message is shown"})
        elif "redirect" in lower or "dashboard" in lower or "success" in lower:
            steps.append({"action": "assert", "target": "url_changed", "value": None, "description": "Verify redirect after action"})
        else:
            steps.append({"action": "assert", "target": "element_visible", "value": None, "description": "Verify expected result"})

        return steps


# ── Module-level helper ───────────────────────────────────────────────────────

def parse_user_stories(stories_text: str, base_url: str = "/", llm_service=None) -> Dict:
    agent = StoryParserAgent(llm_service=llm_service)
    return agent.parse(stories_text, base_url=base_url)
