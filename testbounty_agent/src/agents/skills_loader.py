"""
Skills Loader — Reads domain skill files and injects relevant expertise
into LLM prompts so the AI understands domain-specific testing patterns
without the user having to explain them.

Skill files live in:  <project_root>/skills/*.md

Each skill file contains:
  ## Trigger Keywords  — words that activate this skill
  ## Critical Test Areas — what to prioritise
  ## Business Rules    — domain-specific rules
  ## Common Selector Patterns — CSS selectors for this domain's UI

Usage:
    loader = get_skills_loader()
    context = loader.get_skills_for_context(
        domain="e-commerce",
        vocabulary=["cart", "checkout", "order", "payment"],
        app_description="Online shopping platform"
    )
    # context is a string to inject into the LLM prompt
"""

from __future__ import annotations

import os
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Locate the skills directory (two levels up from this file: src/agents → src → project)
_AGENT_DIR = Path(__file__).parent          # src/agents/
_SRC_DIR   = _AGENT_DIR.parent             # src/
_PROJECT_DIR = _SRC_DIR.parent             # testbounty_agent/
SKILLS_DIR = _PROJECT_DIR / "skills"


class SkillFile:
    """Represents a parsed skill markdown file."""

    def __init__(self, path: Path):
        self.path = path
        self.name: str = ""
        self.domain_line: str = ""
        self.trigger_keywords: List[str] = []
        self.raw_content: str = ""
        self._parse()

    def _parse(self):
        """Parses skill metadata from the markdown file."""
        try:
            self.raw_content = self.path.read_text(encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not read skill file {self.path}: {e}")
            return

        lines = self.raw_content.splitlines()

        # Extract name from H1
        for line in lines:
            if line.startswith("# Skill:"):
                self.name = line.replace("# Skill:", "").strip()
                break
            elif line.startswith("# "):
                self.name = line[2:].strip()
                break

        # Extract domain description (first line after ## Domain)
        in_domain = False
        for line in lines:
            if line.strip() == "## Domain":
                in_domain = True
                continue
            if in_domain:
                text = line.strip()
                if text and not text.startswith("#"):
                    self.domain_line = text
                    break
                if text.startswith("#"):
                    break

        # Extract trigger keywords
        in_keywords = False
        for line in lines:
            if line.strip() == "## Trigger Keywords":
                in_keywords = True
                continue
            if in_keywords:
                text = line.strip()
                if text.startswith("#"):
                    break  # next section
                if text:
                    # Split by comma and clean
                    words = [w.strip().lower() for w in text.split(",") if w.strip()]
                    self.trigger_keywords.extend(words)

    def score(self, domain: str, vocabulary: List[str], description: str) -> int:
        """
        Returns a relevance score (0 = no match, higher = more relevant).
        Checks domain name, vocabulary terms, and description against trigger keywords.
        """
        if not self.trigger_keywords:
            return 0

        score = 0
        text_corpus = (
            domain.lower() + " " +
            " ".join(v.lower() for v in vocabulary) + " " +
            description.lower()
        )

        # Exact keyword matches
        for kw in self.trigger_keywords:
            if kw and kw in text_corpus:
                score += 2

        # Domain name partial match (e.g., "e-commerce" matches ecommerce skill)
        domain_norm = domain.lower().replace("-", "").replace("_", "").replace(" ", "")
        skill_name_norm = self.name.lower().replace("-", "").replace("_", "").replace(" ", "")
        if domain_norm and domain_norm in skill_name_norm:
            score += 10
        if skill_name_norm and skill_name_norm in domain_norm:
            score += 10

        return score


class SkillsLoader:
    """
    Loads all skill files from the skills directory, matches them to the
    current plan context, and returns condensed skill context for LLM injection.
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or SKILLS_DIR
        self._skills: List[SkillFile] = []
        self._loaded = False

    def _load_all(self):
        if self._loaded:
            return
        self._loaded = True

        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return

        for md_file in sorted(self.skills_dir.glob("*.md")):
            skill = SkillFile(md_file)
            if skill.trigger_keywords:
                self._skills.append(skill)
                logger.debug(f"Loaded skill: {skill.name} ({len(skill.trigger_keywords)} keywords)")

        logger.info(f"SkillsLoader: loaded {len(self._skills)} skill files from {self.skills_dir}")

    def list_skills(self) -> List[Dict]:
        """Returns metadata for all available skills (for UI display)."""
        self._load_all()
        return [
            {
                "file": s.path.name,
                "name": s.name,
                "domain": s.domain_line,
                "keyword_count": len(s.trigger_keywords),
            }
            for s in self._skills
        ]

    def select_skills(
        self,
        domain: str = "",
        vocabulary: Optional[List[str]] = None,
        app_description: str = "",
        top_n: int = 2,
        min_score: int = 2,
    ) -> List[SkillFile]:
        """
        Returns the top N most relevant skill files for the given context.

        Args:
            domain:          Domain string from AppKnowledge (e.g. "e-commerce")
            vocabulary:      Domain vocabulary extracted from UI text
            app_description: Plain-text description of the app
            top_n:           Maximum skills to return
            min_score:       Minimum relevance score to include a skill
        """
        self._load_all()
        if not self._skills:
            return []

        vocab = vocabulary or []
        scored: List[Tuple[int, SkillFile]] = []

        for skill in self._skills:
            s = skill.score(domain, vocab, app_description)
            if s >= min_score:
                scored.append((s, skill))

        # Sort descending by score, then alphabetically for stable output
        scored.sort(key=lambda x: (-x[0], x[1].name))
        return [sf for _, sf in scored[:top_n]]

    def get_skills_for_context(
        self,
        domain: str = "",
        vocabulary: Optional[List[str]] = None,
        app_description: str = "",
        top_n: int = 2,
    ) -> str:
        """
        Returns a formatted string containing the most relevant skill content
        ready to inject directly into an LLM prompt.

        Returns empty string if no skills match (safe to concatenate).
        """
        skills = self.select_skills(domain, vocabulary, app_description, top_n=top_n)
        if not skills:
            return ""

        sections: List[str] = ["=== DOMAIN EXPERTISE (Testing Skills) ==="]
        sections.append(
            "The following domain knowledge was automatically matched to this application. "
            "Use it to generate more precise, domain-aware test scenarios:\n"
        )

        for skill in skills:
            sections.append(f"--- {skill.name} ---")
            # Include everything except trigger keywords section (not useful for LLM)
            content = _strip_trigger_keywords_section(skill.raw_content)
            sections.append(content.strip())
            sections.append("")  # blank line separator

        sections.append("=== END DOMAIN EXPERTISE ===")
        return "\n".join(sections)

    def get_active_skill_names(
        self,
        domain: str = "",
        vocabulary: Optional[List[str]] = None,
        app_description: str = "",
    ) -> List[str]:
        """Returns names of skills that would be activated for display in the UI."""
        skills = self.select_skills(domain, vocabulary, app_description)
        return [s.name for s in skills]


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _strip_trigger_keywords_section(markdown: str) -> str:
    """Removes the ## Trigger Keywords section from skill content."""
    lines = markdown.splitlines()
    result = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## Trigger Keywords":
            skip = True
            continue
        if skip and stripped.startswith("## "):
            skip = False
        if not skip:
            result.append(line)
    return "\n".join(result)


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

_loader_instance: Optional[SkillsLoader] = None


def get_skills_loader() -> SkillsLoader:
    """Returns the shared SkillsLoader singleton."""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = SkillsLoader()
    return _loader_instance
