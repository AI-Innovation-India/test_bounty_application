"""
ModuleAgent — An autonomous agent that owns a single application module.

Each agent:
  1. Explores its module visually (screenshot + DOM analysis)
  2. Builds deep knowledge of the module's purpose, elements, and business rules
  3. Asks the user/owner questions when it encounters unknowns
  4. Generates comprehensive test scenarios from its knowledge
  5. Executes and validates those scenarios
  6. Shares its authenticated session with dependent agents

Architecture mirrors how a senior QA engineer thinks:
  - LoginAgent = auth specialist who knows every login edge case
  - DashboardAgent = product analyst who validates KPIs and widgets
  - TrackingAgent = domain expert who understands fleet/asset data
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class AgentQuestion:
    """A question the agent raises when it encounters something it can't determine alone."""
    id: str
    agent_id: str
    module: str
    question: str
    context: str          # what the agent observed that triggered the question
    options: List[str]    # suggested answers (agent's best guesses)
    answer: Optional[str] = None
    asked_at: str = ""
    answered_at: str = ""
    status: str = "pending"   # pending | answered | skipped

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ModuleKnowledge:
    """Everything the agent has learned about its module."""
    module: str
    base_url: str
    entry_url: str = ""           # URL to navigate to this module
    page_title: str = ""
    purpose: str = ""             # what this module does (AI-inferred)
    key_elements: List[Dict] = field(default_factory=list)   # [{selector, label, type, purpose}]
    business_rules: List[str] = field(default_factory=list)  # inferred rules
    valid_data: Dict[str, str] = field(default_factory=dict) # field → example valid value
    invalid_data: Dict[str, str] = field(default_factory=dict)
    edge_cases: List[str] = field(default_factory=list)
    security_concerns: List[str] = field(default_factory=list)
    qa_pairs: Dict[str, str] = field(default_factory=dict)   # question → answer from user
    screenshots: List[str] = field(default_factory=list)     # base64 or paths

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Module Agent ──────────────────────────────────────────────────────────────

class ModuleAgent:
    """
    Autonomous agent that owns one module of the application.
    Lifecycle: idle → exploring → questioning → generating → ready → running → done
    """

    # Known module types and what questions to ask for each
    _MODULE_QUESTIONS = {
        "auth": [
            ("What is the format of valid usernames? (email, username, employee ID)", ["Email address", "Username/alias", "Employee ID number"]),
            ("Are there locked account scenarios we should test?", ["Yes, accounts lock after 3 failed attempts", "Yes, admin can lock accounts manually", "No locking mechanism"]),
            ("Is there MFA / two-factor authentication?", ["Yes - SMS OTP", "Yes - Authenticator app", "No MFA"]),
            ("What should the user see after successful login?", ["Dashboard/home page", "Asset list", "Map view", "Redirect to last page"]),
        ],
        "dashboard": [
            ("What key metrics or KPIs should be visible on the dashboard?", ["Asset count, alerts, status summary", "Temperature/condition readings", "Trip history and mileage"]),
            ("Are there any widgets that load from an external data source?", ["Yes - real-time temperature data", "Yes - GPS location", "No - all static"]),
            ("What is the expected load time for the dashboard?", ["Under 3 seconds", "Under 5 seconds", "Depends on data volume"]),
        ],
        "assets": [
            ("What is a valid Asset ID or unit number for testing?", ["I'll provide a test asset ID", "Any ID in the format TK-XXXX", "Use search to find one"]),
            ("What asset statuses exist?", ["Active, Inactive, Maintenance", "Online, Offline, Alert", "Running, Stopped, Error"]),
            ("Can assets be filtered or searched?", ["Yes - by status, location, type", "Yes - by ID or name only", "No filtering"]),
        ],
        "tracking": [
            ("What does a 'live' tracking view show?", ["Real-time GPS position on map", "Temperature history graph", "Both map and sensor data"]),
            ("Are there any geofence or zone features?", ["Yes - alert when asset leaves zone", "Yes - pre-defined zones", "No geofencing"]),
            ("What triggers a tracking alert?", ["Temperature threshold exceeded", "Asset stopped unexpectedly", "Left geofence boundary"]),
        ],
        "reports": [
            ("What report types are available?", ["Trip summary, temperature log, alerts", "Utilization and efficiency reports", "Custom date range exports"]),
            ("What date range should we use for test reports?", ["Last 7 days", "Last 30 days", "Custom range"]),
            ("Can reports be exported?", ["Yes - PDF and Excel", "Yes - CSV only", "No export"]),
        ],
        "alerts": [
            ("What alert types exist?", ["Temperature alerts, GPS alerts, connectivity alerts", "Maintenance due alerts", "Custom threshold alerts"]),
            ("How are alerts acknowledged?", ["Click to acknowledge in app", "Auto-acknowledge after time", "Requires action/resolution"]),
        ],
        "settings": [
            ("What can be configured in settings?", ["User profile, notifications, thresholds", "Alert preferences and contacts", "API integrations"]),
            ("Are there admin-only settings?", ["Yes - user management, org settings", "Yes - billing and subscription", "No, all users see everything"]),
        ],
    }

    def __init__(
        self,
        module: str,
        base_url: str,
        plan_id: str,
        llm_service=None,
        depends_on: Optional[str] = None,  # module name this agent depends on
    ):
        self.agent_id = f"agent_{module}_{uuid.uuid4().hex[:6]}"
        self.module = module
        self.base_url = base_url
        self.plan_id = plan_id
        self.llm = llm_service
        self.depends_on = depends_on  # e.g. "auth"

        self.status = "idle"
        self.knowledge = ModuleKnowledge(module=module, base_url=base_url)
        self.scenarios: List[Dict] = []
        self.questions: List[AgentQuestion] = []
        self.results: Dict[str, Any] = {}
        self.created_at = datetime.now().isoformat()
        self.error: Optional[str] = None

        # Display label
        self.display_name = self._module_label(module)

    # ── Question management ───────────────────────────────────────────────────

    def raise_question(self, question: str, context: str, options: List[str] = None) -> AgentQuestion:
        """Agent raises a question — status changes to 'questioning' until answered."""
        q = AgentQuestion(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            module=self.module,
            question=question,
            context=context,
            options=options or [],
            asked_at=datetime.now().isoformat(),
        )
        self.questions.append(q)
        if self.status not in ("done", "failed"):
            self.status = "questioning"
        return q

    def answer_question(self, question_id: str, answer: str) -> bool:
        """User/owner provides an answer. Agent incorporates it into its knowledge."""
        for q in self.questions:
            if q.id == question_id and q.status == "pending":
                q.answer = answer
                q.answered_at = datetime.now().isoformat()
                q.status = "answered"
                # Store in knowledge base
                self.knowledge.qa_pairs[q.question] = answer
                # Resume if all questions answered
                pending = [x for x in self.questions if x.status == "pending"]
                if not pending and self.status == "questioning":
                    self.status = "generating"
                return True
        return False

    def skip_question(self, question_id: str) -> bool:
        """User skips a question — agent proceeds without the answer."""
        for q in self.questions:
            if q.id == question_id and q.status == "pending":
                q.status = "skipped"
                pending = [x for x in self.questions if x.status == "pending"]
                if not pending and self.status == "questioning":
                    self.status = "generating"
                return True
        return False

    @property
    def pending_questions(self) -> List[AgentQuestion]:
        return [q for q in self.questions if q.status == "pending"]

    # ── Knowledge building via LLM ────────────────────────────────────────────

    def build_knowledge_from_page(self, page_info: Dict, screenshot_b64: str = None):
        """
        Agent analyses a page (DOM info + screenshot) to build module knowledge.
        Uses LLM to infer purpose, elements, and business rules.
        """
        self.status = "exploring"
        self.knowledge.entry_url = page_info.get("url", self.base_url)
        self.knowledge.page_title = page_info.get("title", "")

        if not self.llm or getattr(self.llm, "provider", "mock") == "mock":
            self._build_knowledge_heuristic(page_info)
            return

        forms = page_info.get("forms", [])
        buttons = page_info.get("buttons", [])
        inputs = page_info.get("inputs", [])
        nav = page_info.get("nav_links", [])

        prompt = f"""You are an expert QA engineer analysing a web application page.

Module: {self.module} ({self.display_name})
Page URL: {page_info.get('url', '')}
Page Title: {page_info.get('title', '')}
Forms: {json.dumps(forms, ensure_ascii=True)[:800]}
Buttons: {json.dumps(buttons, ensure_ascii=True)[:400]}
Inputs: {json.dumps(inputs, ensure_ascii=True)[:400]}
Navigation: {json.dumps(nav, ensure_ascii=True)[:300]}
User answers to previous questions: {json.dumps(self.knowledge.qa_pairs, ensure_ascii=True)[:400]}

Analyse this page and return JSON:
{{
  "purpose": "<one sentence: what this page/module does>",
  "key_elements": [
    {{"selector": "<css>", "label": "<human label>", "type": "input|button|link|display", "purpose": "<what it does>"}}
  ],
  "business_rules": ["<rule 1>", "<rule 2>"],
  "valid_test_data": {{"field_name": "example_value"}},
  "invalid_test_data": {{"field_name": "bad_value_and_why"}},
  "edge_cases": ["<edge case 1>"],
  "security_concerns": ["<security test idea>"],
  "unknown_aspects": ["<what you could not determine from the DOM alone>"]
}}"""

        try:
            response = self.llm.model.invoke(prompt)
            content = getattr(response, "content", str(response)).strip()
            content = content.replace("```json", "").replace("```", "").strip()
            content = content.encode("ascii", errors="replace").decode("ascii")
            data = json.loads(content)

            self.knowledge.purpose = data.get("purpose", "")
            self.knowledge.key_elements = data.get("key_elements", [])
            self.knowledge.business_rules = data.get("business_rules", [])
            self.knowledge.valid_data = data.get("valid_test_data", {})
            self.knowledge.invalid_data = data.get("invalid_test_data", {})
            self.knowledge.edge_cases = data.get("edge_cases", [])
            self.knowledge.security_concerns = data.get("security_concerns", [])

            # Auto-raise questions for unknown aspects
            for unknown in data.get("unknown_aspects", [])[:3]:
                self.raise_question(
                    question=f"The agent couldn't determine: {unknown}",
                    context=f"While analysing {page_info.get('url', '')}",
                    options=["I'll provide the details", "Skip this — not important", "Use best guess"],
                )

        except Exception as e:
            print(f"[{self.agent_id}] Knowledge build failed: {e}")
            self._build_knowledge_heuristic(page_info)

        # Raise module-specific standard questions
        self._raise_module_questions()

    def _build_knowledge_heuristic(self, page_info: Dict):
        """Fallback knowledge building without LLM."""
        self.knowledge.purpose = f"{self.display_name} module"
        forms = page_info.get("forms", [])
        for form in forms:
            for field in form.get("fields", []):
                self.knowledge.key_elements.append({
                    "selector": field.get("selector", ""),
                    "label": field.get("name", ""),
                    "type": "input",
                    "purpose": f"Input for {field.get('name', '')}",
                })

    def _raise_module_questions(self):
        """Raise standard questions for this module type if not already answered."""
        questions_for_module = self._MODULE_QUESTIONS.get(self.module, [])
        existing_questions = {q.question for q in self.questions}

        for question, options in questions_for_module[:3]:  # max 3 auto questions
            if question not in existing_questions and question not in self.knowledge.qa_pairs:
                self.raise_question(
                    question=question,
                    context=f"Standard question for {self.display_name} module",
                    options=options,
                )

    # ── Scenario generation ───────────────────────────────────────────────────

    def generate_scenarios(self, auth_scenario_id: str = "rec_001") -> List[Dict]:
        """
        Generate comprehensive test scenarios from accumulated knowledge.
        Auth module generates standalone scenarios.
        All other modules depend on auth.
        """
        self.status = "generating"

        if not self.llm or getattr(self.llm, "provider", "mock") == "mock":
            scenarios = self._generate_scenarios_heuristic(auth_scenario_id)
            self.scenarios = scenarios
            self.status = "ready"
            return scenarios

        qa_context = "\n".join(
            f"Q: {q}\nA: {a}" for q, a in self.knowledge.qa_pairs.items()
        ) if self.knowledge.qa_pairs else "No user answers yet."

        is_auth = self.module == "auth"
        depends_on_val = "null" if is_auth else f'"{auth_scenario_id}"'

        prompt = f"""You are a senior QA engineer generating test scenarios for a specific module.

MODULE: {self.display_name} ({self.module})
APP URL: {self.base_url}
ENTRY URL: {self.knowledge.entry_url or self.base_url}
PURPOSE: {self.knowledge.purpose}

KEY ELEMENTS (real selectors from the page):
{json.dumps(self.knowledge.key_elements, ensure_ascii=True)[:600]}

BUSINESS RULES:
{json.dumps(self.knowledge.business_rules, ensure_ascii=True)[:400]}

VALID TEST DATA:
{json.dumps(self.knowledge.valid_data, ensure_ascii=True)[:300]}

INVALID TEST DATA:
{json.dumps(self.knowledge.invalid_data, ensure_ascii=True)[:300]}

EDGE CASES TO COVER:
{json.dumps(self.knowledge.edge_cases, ensure_ascii=True)[:300]}

SECURITY CONCERNS:
{json.dumps(self.knowledge.security_concerns, ensure_ascii=True)[:300]}

USER/OWNER ANSWERS:
{qa_context}

=== GENERATE SCENARIOS ===
Create COMPLETE test scenarios covering:
1. Happy path (valid data, expected success)
2. Invalid input (wrong data, boundary values)
3. Empty/missing required fields
4. Edge cases (special chars, long strings, concurrent actions)
5. Security (if relevant: injection, auth bypass, privilege escalation)
6. Business rule validation (each rule = at least 1 test)

Rules:
- Use ACTUAL selectors from key_elements where available
- For auth module: depends_on = null
- For all other modules: depends_on = {depends_on_val}
- Steps must start from ENTRY URL (navigate step first)
- IDs: use format "{self.module}_001", "{self.module}_002", etc.
- Password values: always use "[PASSWORD]" placeholder

Return ONLY valid JSON array of scenarios:
[
  {{
    "id": "{self.module}_001",
    "name": "<action + expected outcome>",
    "description": "<one sentence what this tests and why it matters>",
    "module": "{self.module}",
    "type": "happy_path|error_path|edge_case|security",
    "priority": "high|medium|low",
    "depends_on": {depends_on_val},
    "steps": [
      {{"action": "navigate|fill|click|assert|wait", "target": "<url or selector>", "value": "<string or null>", "description": "<plain English>"}}
    ],
    "status": "pending"
  }}
]"""

        try:
            response = self.llm.model.invoke(prompt)
            content = getattr(response, "content", str(response)).strip()
            content = content.replace("```json", "").replace("```", "").strip()
            content = content.encode("ascii", errors="replace").decode("ascii")
            scenarios = json.loads(content)
            if not isinstance(scenarios, list):
                scenarios = scenarios.get("scenarios", [])
            self.scenarios = scenarios
            self.status = "ready"
            return scenarios
        except Exception as e:
            print(f"[{self.agent_id}] Scenario generation failed: {e}")
            self.error = str(e)
            scenarios = self._generate_scenarios_heuristic(auth_scenario_id)
            self.scenarios = scenarios
            self.status = "ready"
            return scenarios

    def _generate_scenarios_heuristic(self, auth_scenario_id: str) -> List[Dict]:
        """Generate basic scenarios without LLM — guaranteed coverage minimum."""
        depends_on = None if self.module == "auth" else auth_scenario_id
        entry = self.knowledge.entry_url or self.base_url
        scenarios = []

        if self.module == "auth":
            scenarios = [
                {
                    "id": "auth_001", "name": "Valid Login",
                    "description": "Login with valid credentials",
                    "module": "auth", "type": "happy_path", "priority": "high",
                    "depends_on": None,
                    "steps": [
                        {"action": "navigate", "target": self.base_url, "value": None, "description": "Navigate to login page"},
                        {"action": "fill", "target": "#signInName, input[name='signInName'], input[type='email']", "value": "{{username}}", "description": "Enter username"},
                        {"action": "click", "target": "#next, input[type='submit'], button[type='submit']", "value": None, "description": "Click Next"},
                        {"action": "fill", "target": "#password, input[name='password'], input[type='password']", "value": "[PASSWORD]", "description": "Enter password"},
                        {"action": "click", "target": "#next, input[type='submit'], button[type='submit']", "value": None, "description": "Click Sign In"},
                        {"action": "wait",  "target": "navigation", "value": None, "description": "Wait for redirect"},
                        {"action": "assert", "target": "url_changed", "value": None, "description": "Verify login succeeded"},
                    ],
                    "status": "pending",
                },
                {
                    "id": "auth_002", "name": "Invalid Password",
                    "description": "Login with wrong password shows error",
                    "module": "auth", "type": "error_path", "priority": "high",
                    "depends_on": None,
                    "steps": [
                        {"action": "navigate", "target": self.base_url, "value": None, "description": "Navigate to login page"},
                        {"action": "fill", "target": "#signInName, input[type='email']", "value": "{{username}}", "description": "Enter username"},
                        {"action": "click", "target": "#next, input[type='submit']", "value": None, "description": "Click Next"},
                        {"action": "fill", "target": "#password, input[type='password']", "value": "WrongPassword999!", "description": "Enter wrong password"},
                        {"action": "click", "target": "#next, input[type='submit']", "value": None, "description": "Click Sign In"},
                        {"action": "assert", "target": "error_message_visible", "value": None, "description": "Verify error message shown"},
                    ],
                    "status": "pending",
                },
                {
                    "id": "auth_003", "name": "Empty Credentials",
                    "description": "Submit login form with no credentials",
                    "module": "auth", "type": "edge_case", "priority": "medium",
                    "depends_on": None,
                    "steps": [
                        {"action": "navigate", "target": self.base_url, "value": None, "description": "Navigate to login page"},
                        {"action": "click", "target": "#next, input[type='submit'], button[type='submit']", "value": None, "description": "Submit empty form"},
                        {"action": "assert", "target": "error_message_visible", "value": None, "description": "Verify validation error shown"},
                    ],
                    "status": "pending",
                },
            ]
        else:
            scenarios = [
                {
                    "id": f"{self.module}_001",
                    "name": f"View {self.display_name}",
                    "description": f"Navigate to {self.display_name} and verify it loads",
                    "module": self.module, "type": "happy_path", "priority": "high",
                    "depends_on": depends_on,
                    "steps": [
                        {"action": "navigate", "target": entry, "value": None, "description": f"Navigate to {self.display_name}"},
                        {"action": "assert", "target": "page_loaded", "value": None, "description": "Verify page loaded"},
                    ],
                    "status": "pending",
                },
            ]

        return scenarios

    # ── Knowledge feeding from external text ─────────────────────────────────

    def feed_knowledge_from_text(self, text: str, source: str = "manual") -> Dict:
        """
        Accept raw text (user stories, requirements, notes) and extract QA knowledge.
        Uses LLM when available; falls back to heuristic keyword extraction.
        Returns a summary of what was extracted.
        """
        extracted: Dict = {"business_rules": [], "edge_cases": [], "qa_pairs": {}, "valid_data": {}, "security": []}

        if self.llm and getattr(self.llm, "provider", "mock") != "mock":
            prompt = f"""You are a QA knowledge extractor for the {self.display_name} module.

Source text (user stories / requirements):
{text[:2000]}

Extract ONLY what is explicitly mentioned. Return JSON:
{{
  "business_rules": ["<explicit rule that must be tested>"],
  "edge_cases": ["<edge case or boundary condition>"],
  "valid_test_data": {{"<field>": "<valid value from text>"}},
  "invalid_test_data": {{"<field>": "<invalid value / why invalid>"}},
  "security_concerns": ["<security test idea>"],
  "qa_pairs": {{"<question this text answers>": "<answer>"}}
}}"""
            try:
                response = self.llm.model.invoke(prompt)
                content = getattr(response, "content", str(response)).strip()
                content = content.replace("```json", "").replace("```", "").strip()
                data = json.loads(content)

                for rule in data.get("business_rules", []):
                    if rule not in self.knowledge.business_rules:
                        self.knowledge.business_rules.append(rule)
                        extracted["business_rules"].append(rule)
                for edge in data.get("edge_cases", []):
                    if edge not in self.knowledge.edge_cases:
                        self.knowledge.edge_cases.append(edge)
                        extracted["edge_cases"].append(edge)
                for sec in data.get("security_concerns", []):
                    if sec not in self.knowledge.security_concerns:
                        self.knowledge.security_concerns.append(sec)
                        extracted["security"].append(sec)
                self.knowledge.valid_data.update(data.get("valid_test_data", {}))
                self.knowledge.invalid_data.update(data.get("invalid_test_data", {}))
                extracted["valid_data"] = data.get("valid_test_data", {})
                for q, a in data.get("qa_pairs", {}).items():
                    self.knowledge.qa_pairs[q] = a
                    extracted["qa_pairs"][q] = a

            except Exception as e:
                print(f"[{self.agent_id}] LLM knowledge extraction failed: {e}")
                self._feed_knowledge_heuristic(text, extracted)
        else:
            self._feed_knowledge_heuristic(text, extracted)

        # Record training source for UI display
        if not hasattr(self.knowledge, "training_sources"):
            self.knowledge.training_sources = []  # type: ignore[attr-defined]
        self.knowledge.training_sources.append(  # type: ignore[attr-defined]
            {"source": source, "chars": len(text), "added_at": datetime.now().isoformat()}
        )

        # If agent was idle/ready, mark it ready for regeneration
        if self.status in ("idle", "ready"):
            self.status = "questioning"

        return extracted

    def _feed_knowledge_heuristic(self, text: str, extracted: Dict):
        """Heuristic extraction without LLM — keyword-based rule/edge detection."""
        _RULE_MARKERS = ["must", "should", "cannot", "shall", "only when", "always", "never", "required", "mandatory"]
        _EDGE_MARKERS = ["when ", "if ", "edge case", "boundary", "invalid", "empty", "maximum", "minimum", "overflow"]

        for line in text.splitlines():
            line = line.strip()
            if not line or len(line) < 12:
                continue
            ll = line.lower()
            if any(m in ll for m in _RULE_MARKERS) and line not in self.knowledge.business_rules:
                rule = line[:200]
                self.knowledge.business_rules.append(rule)
                extracted["business_rules"].append(rule)
            elif any(m in ll for m in _EDGE_MARKERS) and line not in self.knowledge.edge_cases:
                edge = line[:200]
                self.knowledge.edge_cases.append(edge)
                extracted["edge_cases"].append(edge)

    # ── State export ──────────────────────────────────────────────────────────

    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "module": self.module,
            "display_name": self.display_name,
            "status": self.status,
            "plan_id": self.plan_id,
            "base_url": self.base_url,
            "depends_on": self.depends_on,
            "knowledge": self.knowledge.to_dict(),
            "scenarios_count": len(self.scenarios),
            "scenarios": self.scenarios,
            "questions": [q.to_dict() for q in self.questions],
            "pending_questions_count": len(self.pending_questions),
            "results": self.results,
            "created_at": self.created_at,
            "error": self.error,
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _module_label(module: str) -> str:
        labels = {
            "auth": "Authentication", "login": "Authentication",
            "dashboard": "Dashboard", "home": "Home",
            "assets": "Assets", "asset": "Assets",
            "tracking": "Tracking", "track": "Tracking",
            "reports": "Reports", "report": "Reports",
            "alerts": "Alerts", "alert": "Alerts",
            "settings": "Settings", "setting": "Settings",
            "admin": "Admin", "general": "General",
        }
        return labels.get(module, module.replace("_", " ").title())


# ── Module keyword routing ────────────────────────────────────────────────────

_MODULE_KEYWORDS: Dict[str, List[str]] = {
    "auth":      ["login", "logout", "password", "credential", "sign in", "sign out",
                  "authentication", "mfa", "otp", "2fa", "account", "register", "forgot password"],
    "dashboard": ["dashboard", "overview", "summary", "kpi", "metric", "widget", "analytics", "home page"],
    "assets":    ["asset", "unit", "fleet", "vehicle", "equipment", "device", "truck", "trailer"],
    "tracking":  ["track", "location", "gps", "map", "geofence", "zone", "position", "coordinates"],
    "reports":   ["report", "export", "csv", "pdf", "history", "log", "chart", "graph", "download"],
    "alerts":    ["alert", "notification", "threshold", "warning", "alarm", "trigger", "notify"],
    "settings":  ["setting", "configuration", "preference", "profile", "admin", "permission", "role"],
}


def detect_relevant_modules(text: str, available_modules: List[str]) -> List[str]:
    """Return which modules a text chunk most likely relates to."""
    text_lower = text.lower()
    matched = [
        m for m in available_modules
        if any(kw in text_lower for kw in _MODULE_KEYWORDS.get(m, [m]))
    ]
    return matched or available_modules   # fall back: route to all


# ── Agent Registry (in-memory, per plan) ─────────────────────────────────────

_AGENT_REGISTRY: Dict[str, Dict[str, ModuleAgent]] = {}
# { plan_id: { module: ModuleAgent } }


def get_agents_for_plan(plan_id: str) -> Dict[str, ModuleAgent]:
    return _AGENT_REGISTRY.get(plan_id, {})


def get_agent(plan_id: str, module: str) -> Optional[ModuleAgent]:
    return _AGENT_REGISTRY.get(plan_id, {}).get(module)


def register_agent(agent: ModuleAgent):
    if agent.plan_id not in _AGENT_REGISTRY:
        _AGENT_REGISTRY[agent.plan_id] = {}
    _AGENT_REGISTRY[agent.plan_id][agent.module] = agent


def create_agents_for_plan(
    plan_id: str,
    base_url: str,
    modules: List[str],
    llm_service=None,
) -> List[ModuleAgent]:
    """
    Create one agent per module.
    Auth agent has no dependency.
    All others depend on auth.
    """
    agents = []
    auth_module = "auth" if "auth" in modules else None

    for module in modules:
        depends_on = auth_module if (module != "auth" and auth_module) else None
        agent = ModuleAgent(
            module=module,
            base_url=base_url,
            plan_id=plan_id,
            llm_service=llm_service,
            depends_on=depends_on,
        )
        register_agent(agent)
        agents.append(agent)

    return agents
