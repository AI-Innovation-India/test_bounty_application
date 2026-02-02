from pathlib import Path
from typing import Dict, Any, Optional
import json
import re

from src.utils.logger import logger
from src.services.llm_service import LLMService

class PRDGeneratorService:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.llm = LLMService()

    def read_documentation(self) -> str:
        """
        Read README.md and other documentation files to gather context.
        """
        context = ""
        doc_files = ["README.md", "docs/README.md", "documentation.md"]
        
        for doc in doc_files:
            try:
                path = self.project_path / doc
                if path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        context += f"\n=== {doc} ===\n"
                        context += f.read()
            except Exception as e:
                logger.warning(f"Failed to read {doc}: {e}")
        
        return context

    def generate_prd(self, code_summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a standardized PRD based on documentation and code summary.
        """
        docs_content = self.read_documentation()
        
        # Combine docs and code summary for full context
        full_context = f"{docs_content}\n\n=== Code Summary ===\n{json.dumps(code_summary, indent=2)}"
        
        logger.info("Generating PRD using LLM Service...")
        return self.llm.generate_prd(full_context)
