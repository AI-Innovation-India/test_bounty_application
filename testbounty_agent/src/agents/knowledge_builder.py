"""
Knowledge Builder Agent — Builds deep understanding of the application
before test generation begins.

This is the "KT" (Knowledge Transfer) layer that gives the AI context
about what the application does, its domain, user roles, and key
business workflows.

Sources of knowledge (in order of reliability):
  1. User-provided  — description, roles, key journeys
  2. OpenAPI/Swagger — machine-readable API contract
  3. Page vocabulary — domain terms extracted from UI text
  4. LLM inference  — classify domain, identify workflows & rules
"""

from __future__ import annotations

import json
import ssl
import urllib.request
from typing import Any, Dict, List, Optional


class KnowledgeBuilderAgent:
    """
    Builds AppKnowledge from all available sources before test planning.
    """

    SPEC_PATHS = [
        "/swagger.json",
        "/openapi.json",
        "/api/docs",
        "/api-docs",
        "/docs/openapi.json",
        "/v1/swagger.json",
        "/api/v1/openapi.json",
        "/swagger/v1/swagger.json",
        "/api/swagger.json",
    ]

    def __init__(self, base_url: str, llm_service=None):
        self.base_url = base_url.rstrip("/")
        self.llm = llm_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def build_knowledge(
        self,
        app_map: Dict[str, Any],
        user_description: str = "",
        user_roles: Optional[List[Dict]] = None,
        key_journeys: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Main entry point. Builds a full AppKnowledge dict from all sources.
        Checks cache first — skips LLM synthesis if a fresh entry exists.
        """
        from src.agents.knowledge_cache import get_cache
        cache = get_cache()

        # ── Cache check (skip if user provided custom roles/journeys/description)
        has_user_context = bool(user_description or user_roles or key_journeys)
        if not force_refresh and not has_user_context:
            cached = cache.get(self.base_url)
            if cached:
                return cached
        knowledge: Dict[str, Any] = {
            "domain": "web-application",
            "app_description": user_description,
            "key_features": [],
            "user_roles": user_roles or [],
            "core_workflows": [{"name": j, "steps": [], "priority": "high"} for j in (key_journeys or [])],
            "business_rules": [],
            "api_spec": None,
            "domain_vocabulary": [],
            "tech_stack": [],
            "test_priorities": [],
            "confidence": "low",
        }

        # Step 1 — Try to fetch an OpenAPI / Swagger spec
        api_spec = self._fetch_api_spec()
        if api_spec:
            knowledge["api_spec"] = api_spec
            knowledge["confidence"] = "medium"

        # Step 2 — Extract vocabulary from explorer's app map
        vocabulary = self._extract_vocabulary(app_map)
        knowledge["domain_vocabulary"] = vocabulary

        # Step 3 — LLM synthesis (if available) or rule-based fallback
        if self.llm and getattr(self.llm, "provider", "mock") != "mock" and self.llm.model:
            try:
                llm_knowledge = self._synthesize_with_llm(
                    app_map=app_map,
                    api_spec=api_spec,
                    user_description=user_description,
                    user_roles=user_roles or [],
                    key_journeys=key_journeys or [],
                    vocabulary=vocabulary,
                )
                # Merge LLM results — prefer LLM values unless user explicitly provided
                for key, value in llm_knowledge.items():
                    if key == "user_roles" and (user_roles or []):
                        continue  # Preserve user-provided roles
                    if key == "core_workflows" and (key_journeys or []):
                        # Merge: prepend user journeys then add LLM-discovered ones
                        existing = knowledge["core_workflows"]
                        new_wf = [w for w in value if w.get("name") not in [e.get("name") for e in existing]]
                        knowledge["core_workflows"] = existing + new_wf
                        continue
                    if key == "app_description" and user_description:
                        continue  # Keep user-provided description
                    knowledge[key] = value
                knowledge["confidence"] = "high"
            except Exception as e:
                # LLM failed — fall through to rule-based
                knowledge.update(self._rule_based_inference(app_map, user_description))
        else:
            knowledge.update(self._rule_based_inference(app_map, user_description))

        # ── Cache write (only when LLM synthesised high-confidence result)
        if knowledge.get("confidence") in ("high", "medium") and not has_user_context:
            from src.agents.knowledge_cache import get_cache
            get_cache().set(self.base_url, knowledge)

        return knowledge

    # ------------------------------------------------------------------
    # OpenAPI / Swagger discovery
    # ------------------------------------------------------------------

    def _fetch_api_spec(self) -> Optional[Dict[str, Any]]:
        """Tries to fetch an OpenAPI/Swagger spec at well-known paths."""
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        for path in self.SPEC_PATHS:
            url = self.base_url + path
            try:
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "TestBounty/1.0 (Knowledge Builder)"},
                )
                with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                    if resp.status == 200:
                        raw = resp.read().decode("utf-8")
                        try:
                            spec = json.loads(raw)
                            if any(k in spec for k in ("paths", "swagger", "openapi")):
                                return {
                                    "url": url,
                                    "version": spec.get("openapi") or spec.get("swagger", "unknown"),
                                    "title": spec.get("info", {}).get("title", ""),
                                    "description": spec.get("info", {}).get("description", ""),
                                    "endpoints": self._extract_endpoints(spec),
                                }
                        except (json.JSONDecodeError, ValueError):
                            continue
            except Exception:
                continue
        return None

    def _extract_endpoints(self, spec: Dict) -> List[Dict]:
        """Extracts a flat endpoint list from an OpenAPI spec."""
        endpoints = []
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.upper() not in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"):
                    continue
                if not isinstance(details, dict):
                    continue
                endpoints.append({
                    "path": path,
                    "method": method.upper(),
                    "summary": details.get("summary", ""),
                    "description": details.get("description", ""),
                    "tags": details.get("tags", []),
                    "parameters": [
                        {
                            "name": p.get("name"),
                            "in": p.get("in"),
                            "required": p.get("required", False),
                        }
                        for p in details.get("parameters", [])
                        if isinstance(p, dict)
                    ],
                    "requires_auth": bool(details.get("security")),
                })
        return endpoints

    # ------------------------------------------------------------------
    # Vocabulary extraction
    # ------------------------------------------------------------------

    def _extract_vocabulary(self, app_map: Dict[str, Any]) -> List[str]:
        """Extracts domain-specific terms from page titles, buttons, labels."""
        vocab: set[str] = set()
        stop_words = {
            "the", "and", "for", "are", "this", "with", "from",
            "your", "that", "have", "not", "click", "please", "enter",
        }

        for page in app_map.get("pages", []):
            # Page title
            for word in (page.get("title") or "").split():
                w = word.strip(".,!?:").lower()
                if len(w) > 3 and w not in stop_words:
                    vocab.add(w)

            # Button texts
            for btn in page.get("buttons", []):
                text = (btn.get("text") or "").strip()
                if 2 < len(text) < 40:
                    vocab.add(text.lower())

            # Form field names & placeholders
            for form in page.get("forms", []):
                for field in form.get("fields", []):
                    for key in ("name", "placeholder"):
                        for word in (field.get(key) or "").split():
                            w = word.strip(".,").lower()
                            if len(w) > 2 and w not in stop_words:
                                vocab.add(w)

            # Navigation link texts
            for link in page.get("nav_links", []):
                text = (link.get("text") or "").strip()
                if 2 < len(text) < 30:
                    vocab.add(text.lower())

        return sorted(vocab)

    # ------------------------------------------------------------------
    # LLM synthesis
    # ------------------------------------------------------------------

    def _synthesize_with_llm(
        self,
        app_map: Dict[str, Any],
        api_spec: Optional[Dict],
        user_description: str,
        user_roles: List[Dict],
        key_journeys: List[str],
        vocabulary: List[str],
    ) -> Dict[str, Any]:
        """Uses the LLM to build rich domain understanding."""
        from src.agents.skills_loader import get_skills_loader

        pages_summary = [
            {
                "path": p.get("path", ""),
                "type": p.get("type", ""),
                "title": p.get("title", ""),
                "buttons": [b.get("text", "") for b in p.get("buttons", [])[:6]],
                "forms": len(p.get("forms", [])),
            }
            for p in app_map.get("pages", [])
        ]

        endpoints_summary = (api_spec or {}).get("endpoints", [])[:20]

        # Load domain skill context (empty string if no match)
        skills_context = get_skills_loader().get_skills_for_context(
            domain="",  # domain not yet known at this stage
            vocabulary=vocabulary,
            app_description=user_description,
        )

        prompt = f"""You are a senior QA architect analyzing a web application to build comprehensive testing knowledge.

=== USER PROVIDED CONTEXT ===
Description: {user_description or "Not provided"}
User Roles: {json.dumps(user_roles) if user_roles else "Not provided"}
Key Journeys: {json.dumps(key_journeys) if key_journeys else "Not provided"}

=== DISCOVERED PAGES ===
{json.dumps(pages_summary, indent=2)}

=== DOMAIN VOCABULARY (from UI text) ===
{", ".join(vocabulary[:60])}

=== API ENDPOINTS (if found) ===
{json.dumps(endpoints_summary, indent=2) if endpoints_summary else "Not available — blackbox URL testing"}

{skills_context}

=== TASK ===
Return a JSON object with these exact keys:
{{
  "domain": "<one of: e-commerce | banking-fintech | healthcare | saas-dashboard | crm | social-platform | content-management | e-learning | project-management | booking-reservations | hr-payroll | web-application>",
  "app_description": "<2-3 sentence description of what this app does and who uses it>",
  "key_features": ["feature1", "feature2", ...],
  "user_roles": [
    {{"role": "roleName", "description": "what this role can do", "permissions": ["perm1", "perm2"]}}
  ],
  "core_workflows": [
    {{"name": "workflow name", "steps": ["step 1", "step 2", "..."], "priority": "high|medium|low"}}
  ],
  "business_rules": [
    "Rule 1: ...",
    "Rule 2: ..."
  ],
  "tech_stack": ["tech1", "tech2"],
  "test_priorities": ["highest priority area", "second priority", ...]
}}

Generate at least 4 user roles, 5 core workflows, and 8 business rules based on the app domain.
Return ONLY valid JSON — no markdown, no explanation."""

        response = self.llm.model.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:])
            if content.endswith("```"):
                content = content[:-3].strip()

        return json.loads(content)

    # ------------------------------------------------------------------
    # Rule-based fallback
    # ------------------------------------------------------------------

    def _rule_based_inference(
        self, app_map: Dict[str, Any], user_description: str
    ) -> Dict[str, Any]:
        """Infers basic knowledge when no LLM is available."""
        pages = app_map.get("pages", [])
        modules = list(app_map.get("modules", {}).keys())

        all_text = " ".join(
            (p.get("title") or "") + " " + " ".join(b.get("text", "") for b in p.get("buttons", []))
            for p in pages
        ).lower()

        # Domain detection from vocabulary
        domain = "web-application"
        domain_signals = {
            "e-commerce": ["cart", "checkout", "product", "shop", "order", "price", "buy"],
            "healthcare": ["patient", "doctor", "appointment", "medical", "health", "clinic"],
            "banking-fintech": ["invoice", "payment", "transaction", "balance", "bank", "wallet"],
            "project-management": ["ticket", "issue", "sprint", "board", "project", "task"],
            "e-learning": ["student", "course", "lesson", "quiz", "grade", "enrollment"],
            "social-platform": ["post", "feed", "follow", "like", "comment", "profile"],
            "saas-dashboard": ["dashboard", "analytics", "report", "metric", "subscription"],
            "crm": ["contact", "lead", "deal", "pipeline", "opportunity", "customer"],
            "booking-reservations": ["booking", "reservation", "availability", "schedule", "calendar"],
        }
        for d, signals in domain_signals.items():
            if sum(1 for s in signals if s in all_text) >= 2:
                domain = d
                break

        # Default roles
        has_admin = any("admin" in (p.get("path") or "") for p in pages)
        user_roles = [
            {"role": "guest", "description": "Unauthenticated user — can view public pages only", "permissions": ["view public pages"]},
            {"role": "user", "description": "Authenticated user — can use core features", "permissions": ["login", "use core features", "update own profile"]},
        ]
        if has_admin:
            user_roles.append({
                "role": "admin",
                "description": "Administrator — full system access",
                "permissions": ["manage users", "configure system", "view all data", "delete records"],
            })

        # Generic business rules
        business_rules = [
            "Unauthenticated users must be redirected to login when accessing protected pages",
            "Form fields with required validation must show errors on empty submission",
            "Invalid credentials must show an error message, not a generic page",
            "Session must expire after inactivity",
            "Sensitive data must not be visible in page source or URL",
        ]

        return {
            "domain": domain,
            "app_description": user_description or f"A {domain.replace('-', ' ')} web application",
            "key_features": modules,
            "user_roles": user_roles,
            "core_workflows": [],
            "business_rules": business_rules,
            "tech_stack": [],
            "test_priorities": ["Authentication & authorization", "Core feature flows", "Form validation", "Error handling", "Navigation"],
        }


# ------------------------------------------------------------------
# Convenience function
# ------------------------------------------------------------------

async def build_app_knowledge(
    base_url: str,
    app_map: Dict[str, Any],
    llm_service=None,
    user_description: str = "",
    user_roles: Optional[List[Dict]] = None,
    key_journeys: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build AppKnowledge for a given URL and app_map."""
    builder = KnowledgeBuilderAgent(base_url, llm_service)
    return await builder.build_knowledge(
        app_map=app_map,
        user_description=user_description,
        user_roles=user_roles,
        key_journeys=key_journeys,
    )
