"""
Planner Agent - Creates test scenarios based on Explorer results + AppKnowledge.

Two modes:
  - LLM mode  : uses AppKnowledge + LLM to generate domain-aware, role-specific
                scenarios that reflect real business logic.
  - Template mode: deterministic fallback when no LLM is available; generates
                   scenarios from page-type heuristics (original behaviour).
"""

from __future__ import annotations

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class ScenarioType(str, Enum):
    HAPPY_PATH = "happy_path"
    ERROR_PATH = "error_path"
    EDGE_CASE = "edge_case"
    SECURITY = "security"


class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class TestStep:
    action: str  # click, fill, navigate, assert, wait
    target: str  # selector or URL
    value: Optional[str] = None  # value for fill actions
    description: str = ""


@dataclass
class TestScenario:
    id: str
    name: str
    description: str
    module: str
    type: ScenarioType
    priority: Priority
    depends_on: Optional[str]  # ID of scenario this depends on (e.g., login)
    steps: List[TestStep]
    status: str = "pending"  # pending, passed, failed, skipped

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "module": self.module,
            "type": self.type.value,
            "priority": self.priority.value,
            "depends_on": self.depends_on,
            "steps": [asdict(s) for s in self.steps],
            "status": self.status
        }


class PlannerAgent:
    """
    Agent that creates test scenarios from explorer results
    """

    def __init__(self, app_map: Dict[str, Any]):
        self.app_map = app_map
        self.base_url = app_map.get('base_url', '')
        self.modules = app_map.get('modules', {})
        self.pages = app_map.get('pages', [])
        self.scenarios: List[TestScenario] = []
        self.scenario_counter = 0

    def generate_scenarios_with_knowledge(
        self,
        app_knowledge: Dict[str, Any],
        llm_service,
    ) -> Dict[str, Any]:
        """LLM-powered generation using AppKnowledge context."""
        agent = KnowledgePlannerAgent(self.app_map, app_knowledge, llm_service)
        return agent.generate()

    def generate_scenarios(self) -> Dict[str, Any]:
        """
        Generate all test scenarios for the application (template-based fallback).
        """
        # Generate scenarios for each module
        for module_name, module_data in self.modules.items():
            if module_name == 'auth':
                self._generate_auth_scenarios(module_data)
            elif module_name == 'dashboard':
                self._generate_dashboard_scenarios(module_data)
            elif module_name == 'profile':
                self._generate_profile_scenarios(module_data)
            elif module_name == 'crud':
                self._generate_crud_scenarios(module_data)
            else:
                self._generate_general_scenarios(module_name, module_data)

        # Group scenarios by module
        modules_with_scenarios = {}
        for scenario in self.scenarios:
            if scenario.module not in modules_with_scenarios:
                modules_with_scenarios[scenario.module] = {
                    "name": scenario.module.title(),
                    "requires_auth": self.modules.get(scenario.module, {}).get('requires_auth', False),
                    "scenarios": []
                }
            modules_with_scenarios[scenario.module]["scenarios"].append(scenario.to_dict())

        return {
            "base_url": self.base_url,
            "total_scenarios": len(self.scenarios),
            "modules": modules_with_scenarios
        }

    def _next_id(self, prefix: str) -> str:
        """Generate unique scenario ID"""
        self.scenario_counter += 1
        return f"{prefix}_{self.scenario_counter:03d}"

    def _get_form_selectors(self, page: Dict) -> Dict:
        """Extract actual selectors from page forms"""
        selectors = {
            "email": None,
            "username": None,
            "password": None,
            "name": None,
            "confirm_password": None,
            "submit": None
        }

        for form in page.get('forms', []):
            for field in form.get('fields', []):
                field_name = (field.get('name', '') or '').lower()
                field_type = (field.get('type', '') or '').lower()
                selector = field.get('selector', '')

                if not selector:
                    continue

                # Map field to our known types
                if 'email' in field_name or field_type == 'email':
                    selectors['email'] = selector
                elif 'user' in field_name or 'login' in field_name:
                    selectors['username'] = selector
                elif 'pass' in field_name or field_type == 'password':
                    if 'confirm' in field_name or 'repeat' in field_name:
                        selectors['confirm_password'] = selector
                    elif not selectors['password']:
                        selectors['password'] = selector
                elif 'name' in field_name and 'user' not in field_name:
                    selectors['name'] = selector

            # Get submit button
            if form.get('submit_selector'):
                selectors['submit'] = form['submit_selector']

        return selectors

    def _generate_auth_scenarios(self, module_data: Dict):
        """Generate authentication test scenarios"""
        pages = module_data.get('pages', [])

        for page in pages:
            # Get actual selectors from the page
            sel = self._get_form_selectors(page)

            # Build email/username selector - use captured or fallback
            email_selector = sel['email'] or sel['username'] or "input[type='email'], input[name='email'], input[name='username'], #Email"
            password_selector = sel['password'] or "input[type='password'], input[name='password'], #Password"
            submit_selector = sel['submit'] or "button[type='submit'], input[type='submit'], .login-button, .btn-login"

            if page['type'] == 'login':
                # Happy path - valid login
                self.scenarios.append(TestScenario(
                    id=self._next_id("auth"),
                    name="Valid Login",
                    description="Test login with valid credentials",
                    module="auth",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=None,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to login page"),
                        TestStep("fill", email_selector, "testuser@example.com", "Enter email/username"),
                        TestStep("fill", password_selector, "TestPassword123!", "Enter password"),
                        TestStep("click", submit_selector, description="Click login button"),
                        TestStep("wait", "navigation", description="Wait for redirect"),
                        TestStep("assert", "url_changed", description="Verify redirected to dashboard")
                    ]
                ))

                # Error path - invalid password
                self.scenarios.append(TestScenario(
                    id=self._next_id("auth"),
                    name="Invalid Password",
                    description="Test login with wrong password shows error",
                    module="auth",
                    type=ScenarioType.ERROR_PATH,
                    priority=Priority.HIGH,
                    depends_on=None,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to login page"),
                        TestStep("fill", email_selector, "testuser@example.com", "Enter email"),
                        TestStep("fill", password_selector, "wrongpassword", "Enter wrong password"),
                        TestStep("click", submit_selector, description="Click login"),
                        TestStep("assert", "error_message_visible", description="Verify error message shown")
                    ]
                ))

                # Edge case - empty form
                self.scenarios.append(TestScenario(
                    id=self._next_id("auth"),
                    name="Empty Form Submission",
                    description="Test submitting empty login form",
                    module="auth",
                    type=ScenarioType.EDGE_CASE,
                    priority=Priority.MEDIUM,
                    depends_on=None,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to login page"),
                        TestStep("click", submit_selector, description="Click login without filling form"),
                        TestStep("assert", "validation_error", description="Verify validation error shown")
                    ]
                ))

                # Security - SQL injection attempt
                self.scenarios.append(TestScenario(
                    id=self._next_id("auth"),
                    name="SQL Injection Test",
                    description="Test login form against SQL injection",
                    module="auth",
                    type=ScenarioType.SECURITY,
                    priority=Priority.HIGH,
                    depends_on=None,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to login page"),
                        TestStep("fill", email_selector, "' OR '1'='1", "Enter SQL injection payload"),
                        TestStep("fill", password_selector, "' OR '1'='1", "Enter SQL injection in password"),
                        TestStep("click", submit_selector, description="Submit"),
                        TestStep("assert", "no_unauthorized_access", description="Verify no unauthorized access")
                    ]
                ))

            elif page['type'] == 'register':
                name_selector = sel['name'] or "input[name='name'], input[name='fullname'], input[name='FirstName'], #FirstName"
                confirm_pass_selector = sel['confirm_password'] or "input[name='ConfirmPassword'], input[name='confirm_password'], #ConfirmPassword"

                # Happy path - valid registration
                self.scenarios.append(TestScenario(
                    id=self._next_id("auth"),
                    name="Valid Registration",
                    description="Test registration with valid data",
                    module="auth",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=None,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to register page"),
                        TestStep("fill", name_selector, "Test User", "Enter name"),
                        TestStep("fill", email_selector, "newuser@example.com", "Enter email"),
                        TestStep("fill", password_selector, "SecurePass123!", "Enter password"),
                        TestStep("fill", confirm_pass_selector, "SecurePass123!", "Confirm password"),
                        TestStep("click", submit_selector, description="Submit registration"),
                        TestStep("assert", "success_or_redirect", description="Verify registration success")
                    ]
                ))

    def _generate_dashboard_scenarios(self, module_data: Dict):
        """Generate dashboard test scenarios"""
        pages = module_data.get('pages', [])
        requires_auth = module_data.get('requires_auth', True)
        depends_on = "auth_001" if requires_auth else None

        for page in pages:
            if page['type'] == 'dashboard':
                # View dashboard
                self.scenarios.append(TestScenario(
                    id=self._next_id("dash"),
                    name="View Dashboard",
                    description="Verify dashboard loads with correct elements",
                    module="dashboard",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to dashboard"),
                        TestStep("assert", "page_loaded", description="Verify page loads"),
                        TestStep("assert", "key_elements_visible", description="Verify dashboard elements visible")
                    ]
                ))

                # Test each button on dashboard
                for btn in page.get('buttons', []):
                    if btn['action'] not in ['cancel', 'close']:
                        self.scenarios.append(TestScenario(
                            id=self._next_id("dash"),
                            name=f"Click {btn['text']}",
                            description=f"Test clicking '{btn['text']}' button on dashboard",
                            module="dashboard",
                            type=ScenarioType.HAPPY_PATH,
                            priority=Priority.MEDIUM,
                            depends_on=depends_on,
                            steps=[
                                TestStep("navigate", page['url'], description="Go to dashboard"),
                                TestStep("click", f"button:has-text('{btn['text']}')", description=f"Click {btn['text']}"),
                                TestStep("assert", "action_result", description="Verify action completed")
                            ]
                        ))

            elif page['type'] == 'landing':
                # Landing page tests (no auth needed)
                self.scenarios.append(TestScenario(
                    id=self._next_id("dash"),
                    name="View Landing Page",
                    description="Verify landing page loads correctly",
                    module="dashboard",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=None,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to landing page"),
                        TestStep("assert", "page_loaded", description="Verify page loads"),
                        TestStep("assert", "cta_buttons_visible", description="Verify CTA buttons visible")
                    ]
                ))

                # Test navigation links
                for link in page.get('nav_links', []):
                    if link['text']:
                        self.scenarios.append(TestScenario(
                            id=self._next_id("dash"),
                            name=f"Navigate to {link['text']}",
                            description=f"Test navigation link '{link['text']}'",
                            module="dashboard",
                            type=ScenarioType.HAPPY_PATH,
                            priority=Priority.LOW,
                            depends_on=None,
                            steps=[
                                TestStep("navigate", page['url'], description="Go to landing page"),
                                TestStep("click", f"a:has-text('{link['text']}')", description=f"Click {link['text']} link"),
                                TestStep("assert", "navigation_success", description="Verify navigation works")
                            ]
                        ))

    def _generate_profile_scenarios(self, module_data: Dict):
        """Generate profile/settings test scenarios"""
        pages = module_data.get('pages', [])

        for page in pages:
            depends_on = "auth_001" if page.get('requires_auth', True) else None

            if page['type'] == 'settings':
                self.scenarios.append(TestScenario(
                    id=self._next_id("profile"),
                    name="View Settings",
                    description="Verify settings page loads",
                    module="profile",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.MEDIUM,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to settings"),
                        TestStep("assert", "page_loaded", description="Verify page loads")
                    ]
                ))

                # Test forms on settings page
                for form in page.get('forms', []):
                    self.scenarios.append(TestScenario(
                        id=self._next_id("profile"),
                        name=f"Update {form['id']}",
                        description=f"Test updating settings via {form['id']}",
                        module="profile",
                        type=ScenarioType.HAPPY_PATH,
                        priority=Priority.MEDIUM,
                        depends_on=depends_on,
                        steps=[
                            TestStep("navigate", page['url'], description="Go to settings"),
                            *[TestStep("fill", f"[name='{f['name']}']", "test_value", f"Fill {f['name']}")
                              for f in form.get('fields', []) if f['name']],
                            TestStep("click", f"#{form['id']} button[type='submit'], button:has-text('{form.get('submit_text', 'Save')}')",
                                   description="Submit form"),
                            TestStep("assert", "save_success", description="Verify save successful")
                        ]
                    ))

            elif page['type'] == 'profile':
                self.scenarios.append(TestScenario(
                    id=self._next_id("profile"),
                    name="View Profile",
                    description="Verify profile page loads",
                    module="profile",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.MEDIUM,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to profile"),
                        TestStep("assert", "page_loaded", description="Verify page loads"),
                        TestStep("assert", "user_info_visible", description="Verify user info displayed")
                    ]
                ))

    def _generate_crud_scenarios(self, module_data: Dict):
        """Generate CRUD operation test scenarios"""
        pages = module_data.get('pages', [])

        for page in pages:
            depends_on = "auth_001" if page.get('requires_auth', True) else None

            if page['type'] == 'create':
                # Happy path - create item
                self.scenarios.append(TestScenario(
                    id=self._next_id("crud"),
                    name="Create New Item",
                    description="Test creating a new item",
                    module="crud",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to create page"),
                        *[TestStep("fill", f"[name='{f['name']}']", f"Test {f['name']}", f"Fill {f['name']}")
                          for form in page.get('forms', []) for f in form.get('fields', []) if f['name']],
                        TestStep("click", "button[type='submit']", description="Submit form"),
                        TestStep("assert", "create_success", description="Verify item created")
                    ]
                ))

                # Edge case - empty form
                self.scenarios.append(TestScenario(
                    id=self._next_id("crud"),
                    name="Create with Empty Form",
                    description="Test submitting empty create form",
                    module="crud",
                    type=ScenarioType.EDGE_CASE,
                    priority=Priority.MEDIUM,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to create page"),
                        TestStep("click", "button[type='submit']", description="Submit empty form"),
                        TestStep("assert", "validation_error", description="Verify validation errors shown")
                    ]
                ))

            elif page['type'] == 'list':
                self.scenarios.append(TestScenario(
                    id=self._next_id("crud"),
                    name="View List",
                    description="Test viewing list of items",
                    module="crud",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to list page"),
                        TestStep("assert", "list_visible", description="Verify list is displayed")
                    ]
                ))

            elif page['type'] == 'edit':
                self.scenarios.append(TestScenario(
                    id=self._next_id("crud"),
                    name="Edit Item",
                    description="Test editing an existing item",
                    module="crud",
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.HIGH,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to edit page"),
                        TestStep("assert", "form_prefilled", description="Verify form has existing data"),
                        TestStep("fill", "input:first-of-type", "Updated Value", "Modify a field"),
                        TestStep("click", "button[type='submit']", description="Submit changes"),
                        TestStep("assert", "update_success", description="Verify update successful")
                    ]
                ))

    def _generate_general_scenarios(self, module_name: str, module_data: Dict):
        """Generate scenarios for general/unknown pages"""
        pages = module_data.get('pages', [])

        for page in pages:
            depends_on = "auth_001" if page.get('requires_auth', True) else None

            # Basic page load test
            self.scenarios.append(TestScenario(
                id=self._next_id("gen"),
                name=f"View {page['title'] or page['path']}",
                description=f"Test loading {page['url']}",
                module=module_name,
                type=ScenarioType.HAPPY_PATH,
                priority=Priority.LOW,
                depends_on=depends_on,
                steps=[
                    TestStep("navigate", page['url'], description="Navigate to page"),
                    TestStep("assert", "page_loaded", description="Verify page loads without errors")
                ]
            ))

            # Test any forms on the page
            for form in page.get('forms', []):
                self.scenarios.append(TestScenario(
                    id=self._next_id("gen"),
                    name=f"Submit {form['id']}",
                    description=f"Test form submission on {page['path']}",
                    module=module_name,
                    type=ScenarioType.HAPPY_PATH,
                    priority=Priority.MEDIUM,
                    depends_on=depends_on,
                    steps=[
                        TestStep("navigate", page['url'], description="Go to page"),
                        *[TestStep("fill", f"[name='{f['name']}']", "test", f"Fill {f['name']}")
                          for f in form.get('fields', []) if f['name']],
                        TestStep("click", "button[type='submit']", description="Submit form"),
                        TestStep("assert", "form_submitted", description="Verify form processes")
                    ]
                ))


def generate_test_plan(
    app_map: Dict[str, Any],
    app_knowledge: Optional[Dict[str, Any]] = None,
    llm_service=None,
) -> Dict[str, Any]:
    """
    Generate a test plan from an app map.

    When `app_knowledge` and `llm_service` are provided the planner uses the
    LLM to generate context-aware, domain-specific scenarios.  Otherwise it
    falls back to the deterministic template-based approach.
    """
    planner = PlannerAgent(app_map)

    # LLM-powered path
    if app_knowledge and llm_service and getattr(llm_service, "provider", "mock") != "mock":
        try:
            return planner.generate_scenarios_with_knowledge(app_knowledge, llm_service)
        except Exception as e:
            # If LLM fails for any reason, fall back silently
            import logging
            logging.getLogger(__name__).warning(
                f"LLM scenario generation failed, falling back to templates: {e}"
            )

    # Template-based path (original behaviour)
    return planner.generate_scenarios()


class KnowledgePlannerAgent:
    """
    LLM-driven scenario generator that understands *what* the app does,
    not just *what elements* are on the page.
    """

    def __init__(self, app_map: Dict[str, Any], app_knowledge: Dict[str, Any], llm_service):
        self.app_map = app_map
        self.knowledge = app_knowledge
        self.llm = llm_service
        self.base_url = app_map.get("base_url", "")

    def generate(self) -> Dict[str, Any]:
        """Main entry point — calls LLM to produce a rich scenario plan."""
        from src.agents.skills_loader import get_skills_loader

        pages_summary = [
            {
                "path": p.get("path", ""),
                "type": p.get("type", ""),
                "title": p.get("title", ""),
                "forms": [
                    {
                        "id": f.get("id", ""),
                        "fields": [{"name": fld.get("name"), "type": fld.get("type"), "selector": fld.get("selector")} for fld in f.get("fields", [])],
                        "submit_selector": f.get("submit_selector", ""),
                    }
                    for f in p.get("forms", [])
                ],
                "buttons": [b.get("text", "") for b in p.get("buttons", [])[:6]],
                "requires_auth": p.get("requires_auth", False),
            }
            for p in self.app_map.get("pages", [])
        ]

        k = self.knowledge

        # Load domain skills context — gives LLM expert testing knowledge for this domain
        skills_context = get_skills_loader().get_skills_for_context(
            domain=k.get("domain", ""),
            vocabulary=k.get("domain_vocabulary", []),
            app_description=k.get("app_description", ""),
        )

        prompt = f"""You are a senior QA engineer generating comprehensive Playwright test scenarios.

=== APPLICATION KNOWLEDGE ===
Domain        : {k.get('domain', 'web-application')}
Description   : {k.get('app_description', '')}
Key Features  : {json.dumps(k.get('key_features', []))}
User Roles    : {json.dumps(k.get('user_roles', []))}
Core Workflows: {json.dumps(k.get('core_workflows', []))}
Business Rules: {json.dumps(k.get('business_rules', []))}
Test Priorities: {json.dumps(k.get('test_priorities', []))}

=== DISCOVERED PAGES ===
{json.dumps(pages_summary, indent=2)}

=== BASE URL ===
{self.base_url}

{skills_context}

=== TASK ===
Generate a comprehensive set of test scenarios grouped by module.
For EACH core workflow and EACH user role, create at least one scenario.
Cover: happy paths, error paths, edge cases, security checks, role-based access.

Return ONLY valid JSON in this exact structure:
{{
  "base_url": "{self.base_url}",
  "total_scenarios": <number>,
  "modules": {{
    "<module_name>": {{
      "name": "<display name>",
      "requires_auth": <true|false>,
      "scenarios": [
        {{
          "id": "<module_prefix>_<NNN>",
          "name": "<scenario name>",
          "description": "<what is being tested and why>",
          "module": "<module_name>",
          "type": "happy_path|error_path|edge_case|security",
          "priority": "high|medium|low",
          "depends_on": null,
          "user_role": "<role name or null>",
          "business_rule": "<which rule this validates or null>",
          "steps": [
            {{
              "action": "navigate|fill|click|assert|wait",
              "target": "<CSS selector or URL or assertion type>",
              "value": "<fill value or null>",
              "description": "<plain English description of this step>"
            }}
          ],
          "status": "pending"
        }}
      ]
    }}
  }}
}}

IMPORTANT:
- Use real CSS selectors from the discovered forms where available
- For each user role, test what they CAN do and what they CANNOT do
- Include at least one security test per auth-related module
- Use actual page URLs from the discovered pages
- Be specific to this domain: {k.get('domain', 'web-application')}"""

        response = self.llm.model.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()

        # Strip markdown fences
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if content.rstrip().endswith("```"):
                content = content.rstrip()[:-3].strip()

        plan = json.loads(content)

        # Ensure total_scenarios is accurate
        total = sum(
            len(m.get("scenarios", []))
            for m in plan.get("modules", {}).values()
        )
        plan["total_scenarios"] = total
        return plan


if __name__ == "__main__":
    # Test with sample app map
    sample_map = {
        "base_url": "http://localhost:3000",
        "modules": {
            "auth": {
                "pages": [{"type": "login", "url": "http://localhost:3000/login", "forms": [], "buttons": []}]
            }
        }
    }
    result = generate_test_plan(sample_map)
    print(json.dumps(result, indent=2))
