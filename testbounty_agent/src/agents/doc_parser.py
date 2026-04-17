"""
DocParserAgent — extracts text from uploaded documents and converts to test scenarios.

Supported formats:
  - PDF (.pdf)   via pdfplumber
  - Word (.docx) via python-docx
  - Plain text (.txt, .md, .csv)
  - HTML/Confluence (raw HTML string)

Flow:
  extract_text(file_bytes, filename) → raw_text
  parse_to_scenarios(raw_text, base_url, llm) → same format as StoryParserAgent
"""

from __future__ import annotations

import io
import re
from typing import Dict, Optional


# ── Text extraction ────────────────────────────────────────────────────────────

def extract_text_from_bytes(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from file bytes based on extension."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

    if ext == "pdf":
        return _extract_pdf(file_bytes)
    elif ext in ("docx", "doc"):
        return _extract_docx(file_bytes)
    elif ext in ("html", "htm"):
        return _extract_html(file_bytes.decode("utf-8", errors="ignore"))
    else:
        # plain text, markdown, csv
        return file_bytes.decode("utf-8", errors="ignore")


def _extract_pdf(data: bytes) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
            return "\n\n".join(pages)
    except Exception as e:
        # Fallback to pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n\n".join(
                page.extract_text() or "" for page in reader.pages
            )
        except Exception as e2:
            return f"[PDF extraction failed: {e2}]"


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
    except Exception as e:
        return f"[DOCX extraction failed: {e}]"


def _extract_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    # Remove scripts and styles
    html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"\s{2,}", "\n", text)
    return text.strip()


# ── Doc Parser Agent ──────────────────────────────────────────────────────────

class DocParserAgent:
    """
    Parse uploaded documents into test scenarios.

    Two modes:
      1. LLM mode  — send extracted text to LLM for intelligent scenario extraction
      2. Rule mode — delegate to StoryParserAgent for rule-based parsing
    """

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def parse_document(self, file_bytes: bytes, filename: str, base_url: str = "/") -> Dict:
        """
        Main entry point.
        Returns same structure as StoryParserAgent.parse()
        """
        raw_text = extract_text_from_bytes(file_bytes, filename)

        if not raw_text or len(raw_text.strip()) < 20:
            return {"modules": {}, "total_scenarios": 0, "source": "document", "error": "Could not extract text from document"}

        # Truncate to reasonable size for LLM
        truncated = raw_text[:6000]

        if self.llm and getattr(self.llm, "provider", "mock") != "mock":
            try:
                result = self._llm_extract(truncated, base_url, filename)
                result["source"] = "document"
                result["document_name"] = filename
                result["extracted_chars"] = len(raw_text)
                return result
            except Exception as e:
                print(f"[DocParser] LLM extraction failed ({e}), falling back to story parser")

        # Fallback: treat extracted text as user stories
        from src.agents.story_parser import StoryParserAgent
        story_agent = StoryParserAgent(llm_service=self.llm)
        result = story_agent.parse(truncated, base_url=base_url)
        result["source"] = "document"
        result["document_name"] = filename
        result["extracted_chars"] = len(raw_text)
        return result

    def _llm_extract(self, text: str, base_url: str, filename: str) -> Dict:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        import json

        prompt = ChatPromptTemplate.from_template("""
You are a senior QA engineer. Analyze the following document and extract all testable requirements, features, and user stories. Convert them into structured test scenarios for a web application at {base_url}.

DOCUMENT: {filename}
CONTENT:
{content}

INSTRUCTIONS:
1. Identify all features, user stories, acceptance criteria, or requirements in the document
2. Group them by functional module (auth, dashboard, products, checkout, etc.)
3. For each item, create a test scenario with realistic Playwright steps
4. Include both happy path and error/edge case scenarios
5. Return ONLY valid JSON, no markdown or explanation

JSON FORMAT:
{{
  "modules": {{
    "module_name": {{
      "name": "Human Name",
      "requires_auth": false,
      "scenarios": [
        {{
          "id": "mod_001",
          "name": "Test scenario name",
          "description": "What this tests",
          "module": "module_name",
          "type": "happy_path",
          "priority": "high",
          "depends_on": null,
          "steps": [
            {{"action": "navigate", "target": "{base_url}/page", "value": null, "description": "Step description"}}
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
        response = chain.invoke({"content": text, "base_url": base_url, "filename": filename})
        response = response.replace("```json", "").replace("```", "").strip()
        result = json.loads(response)

        total = sum(len(m.get("scenarios", [])) for m in result.get("modules", {}).values())
        result["total_scenarios"] = total
        return result


# ── Module-level helpers ──────────────────────────────────────────────────────

def parse_document_file(file_bytes: bytes, filename: str, base_url: str = "/", llm_service=None) -> Dict:
    agent = DocParserAgent(llm_service=llm_service)
    return agent.parse_document(file_bytes, filename, base_url)
