"""
KTChatAgent — AI-guided conversational Knowledge Transfer.

Flow:
  1. AI analyses the explored app_map
  2. AI asks smart, targeted questions to fill knowledge gaps
  3. User answers → AI builds richer AppKnowledge
  4. After enough turns, AI generates enhanced test scenarios

The agent maintains a conversation history per plan_id stored in PLANS.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional


# ── Smart question bank ───────────────────────────────────────────────────────

STARTER_QUESTIONS = {
    "auth": [
        "I can see a login page. What types of users can log in — are there roles like admin, regular user, or others?",
        "Are there any special login rules? (e.g., 2FA, SSO, account lockout after failed attempts)",
    ],
    "ecommerce": [
        "I can see product listings and a cart. What are the main checkout steps?",
        "Are there any discount codes, loyalty points, or promotional rules I should test?",
        "What payment methods do you support?",
    ],
    "general": [
        "What is the primary goal users come to this application to accomplish?",
        "Who are the main types of users? (e.g., admin vs. regular user, free vs. paid tier)",
        "What are the most critical flows that must never break?",
        "Are there any business rules or validations that are not obvious from the UI?",
    ],
}


# ── KT Chat Agent ─────────────────────────────────────────────────────────────

class KTChatAgent:
    """
    Maintains a conversational KT session for a plan.

    Usage:
        agent = KTChatAgent(llm_service=llm)
        reply = agent.chat(plan_id, user_message, plan_data)
        # Returns: { reply, suggestions, knowledge_updated, next_question }
    """

    def __init__(self, llm_service=None):
        self.llm = llm_service

    # ── Main chat method ──────────────────────────────────────────────────────

    def chat(self, plan_id: str, user_message: str, plan: Dict) -> Dict:
        """
        Process one user message and return AI reply + optional next question.
        Mutates plan["chat_history"] and plan["app_knowledge"] in-place.
        """
        history: List[Dict] = plan.setdefault("chat_history", [])
        app_map = plan.get("app_map") or {}
        app_knowledge: Dict = plan.get("app_knowledge") or {}

        # Append user message
        history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat(),
        })

        # Generate AI reply
        if self.llm and getattr(self.llm, "provider", "mock") != "mock":
            reply_data = self._llm_reply(user_message, history, app_map, app_knowledge, plan["url"])
        else:
            reply_data = self._rule_reply(user_message, history, app_map, app_knowledge)

        # Append assistant reply to history
        history.append({
            "role": "assistant",
            "content": reply_data["reply"],
            "timestamp": datetime.now().isoformat(),
        })

        # Merge any extracted knowledge back into app_knowledge
        if reply_data.get("extracted_knowledge"):
            app_knowledge = self._merge_knowledge(app_knowledge, reply_data["extracted_knowledge"])
            plan["app_knowledge"] = app_knowledge

        plan["chat_history"] = history

        return {
            "reply": reply_data["reply"],
            "next_question": reply_data.get("next_question"),
            "knowledge_updated": bool(reply_data.get("extracted_knowledge")),
            "suggestions": reply_data.get("suggestions", []),
            "turn": len([h for h in history if h["role"] == "user"]),
        }

    def get_opening_message(self, plan: Dict) -> Dict:
        """Generate the first AI message when user opens the chat."""
        app_map = plan.get("app_map") or {}
        app_knowledge = plan.get("app_knowledge") or {}
        url = plan.get("url", "the application")

        pages = app_map.get("total_pages", 0)
        auth_pages = app_map.get("auth_pages", [])
        modules = list(app_map.get("modules", {}).keys())
        domain = app_knowledge.get("domain", "unknown")

        lines = [
            f"I've explored **{url}** and found {pages} pages across {len(modules)} modules: {', '.join(modules[:5]) or 'none yet'}.",
        ]

        if auth_pages:
            lines.append(f"I detected a login/auth area. To generate better tests, I need a few details.")
        else:
            lines.append("To generate smarter tests, I need to understand your application better.")

        # Pick a starter question based on domain
        questions = STARTER_QUESTIONS.get("auth" if auth_pages else "general", STARTER_QUESTIONS["general"])
        opening_q = questions[0]

        lines.append(f"\n**{opening_q}**")

        return {
            "reply": "\n".join(lines),
            "next_question": opening_q,
            "is_opening": True,
            "turn": 0,
        }

    # ── LLM reply ─────────────────────────────────────────────────────────────

    def _llm_reply(self, user_message: str, history: List[Dict], app_map: Dict, app_knowledge: Dict, url: str) -> Dict:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        history_text = "\n".join(
            f"{h['role'].upper()}: {h['content']}"
            for h in history[-10:]  # last 10 turns
        )

        pages_summary = f"{app_map.get('total_pages', 0)} pages, modules: {list(app_map.get('modules', {}).keys())}"
        current_knowledge = json.dumps({k: v for k, v in app_knowledge.items() if k in ("domain", "user_roles", "business_rules", "core_workflows", "confidence")}, indent=2)

        prompt = ChatPromptTemplate.from_template("""
You are an expert QA consultant doing a Knowledge Transfer (KT) session to understand a web application at {url}.
Your goal: ask targeted questions to fill knowledge gaps so you can generate comprehensive, realistic test scenarios.

APP EXPLORATION SUMMARY: {pages_summary}
CURRENT KNOWN KNOWLEDGE: {current_knowledge}

CONVERSATION SO FAR:
{history}

LATEST USER MESSAGE: {user_message}

YOUR TASK:
1. Acknowledge what the user shared and extract key facts
2. Ask ONE specific follow-up question about an important gap
3. After 4-5 turns, summarize the knowledge you've gathered

Return ONLY valid JSON:
{{
  "reply": "Your conversational reply with acknowledgment + one clear follow-up question",
  "next_question": "The single question you're asking (extracted from reply for UI highlighting)",
  "extracted_knowledge": {{
    "user_roles": ["role1", "role2"],
    "business_rules": ["rule 1", "rule 2"],
    "core_workflows": ["workflow 1"],
    "test_credentials": {{"email": "...", "password": "..."}}
  }},
  "suggestions": ["Quick suggestion 1", "Quick suggestion 2"]
}}

The extracted_knowledge should only include fields you actually learned from this message. Leave fields empty/null if not mentioned.
""")

        chain = prompt | self.llm.model | StrOutputParser()
        response = chain.invoke({
            "url": url,
            "pages_summary": pages_summary,
            "current_knowledge": current_knowledge,
            "history": history_text,
            "user_message": user_message,
        })
        response = response.replace("```json", "").replace("```", "").strip()
        return json.loads(response)

    # ── Rule-based reply ──────────────────────────────────────────────────────

    def _rule_reply(self, user_message: str, history: List[Dict], app_map: Dict, app_knowledge: Dict) -> Dict:
        """Simple turn-based question flow when no LLM is available."""
        turn = len([h for h in history if h["role"] == "user"])
        questions = STARTER_QUESTIONS["general"]
        auth_pages = app_map.get("auth_pages", [])
        if auth_pages:
            questions = STARTER_QUESTIONS["auth"] + questions

        ack = f"Thanks! I've noted that: \"{user_message[:100]}\""
        extracted = self._extract_from_message(user_message)

        if turn < len(questions):
            next_q = questions[turn]
            reply = f"{ack}\n\n**{next_q}**"
        else:
            reply = (
                f"{ack}\n\nThat's very helpful! I now have enough context to generate "
                f"more targeted test scenarios. Click **Apply to Plan** to regenerate tests with this knowledge."
            )
            next_q = None

        return {"reply": reply, "next_question": next_q, "extracted_knowledge": extracted, "suggestions": []}

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _extract_from_message(self, message: str) -> Dict:
        """Simple regex-based extraction from user message."""
        extracted: Dict[str, Any] = {}
        lower = message.lower()

        # Extract roles
        role_matches = re.findall(r'\b(admin|user|manager|guest|customer|vendor|moderator|editor|viewer|owner)\b', lower)
        if role_matches:
            extracted["user_roles"] = list(set(role_matches))

        # Extract email/password
        email_match = re.search(r'[\w.+-]+@[\w-]+\.\w+', message)
        if email_match:
            extracted.setdefault("test_credentials", {})["email"] = email_match.group(0)

        # Extract URLs mentioned
        url_match = re.search(r'https?://\S+', message)
        if url_match:
            extracted["base_url"] = url_match.group(0)

        return extracted if extracted else None

    def _merge_knowledge(self, existing: Dict, new_knowledge: Dict) -> Dict:
        """Merge new knowledge into existing app_knowledge."""
        if not new_knowledge:
            return existing

        result = dict(existing)

        for key, value in new_knowledge.items():
            if not value:
                continue
            if isinstance(value, list):
                existing_list = result.get(key, [])
                if isinstance(existing_list, list):
                    merged = list(set(existing_list + value))
                    result[key] = merged
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = {**result.get(key, {}), **value}
            else:
                result[key] = value

        # Bump confidence if we got roles or workflows
        if new_knowledge.get("user_roles") or new_knowledge.get("core_workflows"):
            result["confidence"] = "high"
            result["knowledge_source"] = "kt_chat"

        return result


# ── Module-level helper ───────────────────────────────────────────────────────

def process_chat_message(plan_id: str, message: str, plan: Dict, llm_service=None) -> Dict:
    agent = KTChatAgent(llm_service=llm_service)
    return agent.chat(plan_id, message, plan)


def get_chat_opening(plan: Dict, llm_service=None) -> Dict:
    agent = KTChatAgent(llm_service=llm_service)
    return agent.get_opening_message(plan)
