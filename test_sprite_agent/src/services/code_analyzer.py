import os
from pathlib import Path
from typing import Dict, List, Any
import json

from src.utils.logger import logger

class CodeAnalyzerService:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)

    def scan_directory(self) -> Dict[str, Any]:
        """
        Recursively scan the directory to understand structure and key files.
        """
        structure = {"files": [], "directories": []}
        
        try:
            for root, dirs, files in os.walk(self.project_path):
                # Skip node_modules, .git, venv etc.
                if "node_modules" in root or ".git" in root or "__pycache__" in root or "venv" in root:
                    continue

                rel_root = os.path.relpath(root, self.project_path)
                if rel_root == ".":
                    rel_root = ""
                
                for d in dirs:
                    if d not in ["node_modules", ".git", "__pycache__", "venv"]:
                        structure["directories"].append(os.path.join(rel_root, d).replace("\\", "/"))
                
                for f in files:
                    structure["files"].append(os.path.join(rel_root, f).replace("\\", "/"))
            
            return structure
        except Exception as e:
            logger.error(f"Error scanning directory: {e}")
            return {"error": str(e)}

    def detect_framework(self) -> Dict[str, Any]:
        """
        Identify the technology stack based on configuration files and dependencies.
        """
        tech_stack = {
            "language": "Unknown",
            "framework": "Unknown",
            "dependencies": []
        }

        # Check for package.json (Node.js)
        pkg_json = self.project_path / "package.json"
        if pkg_json.exists():
            tech_stack["language"] = "JavaScript/TypeScript"
            try:
                with open(pkg_json, 'r') as f:
                    data = json.load(f)
                    deps = data.get("dependencies", {})
                    dev_deps = data.get("devDependencies", {})
                    all_deps = {**deps, **dev_deps}
                    tech_stack["dependencies"] = list(all_deps.keys())

                    if "react" in all_deps:
                        tech_stack["framework"] = "React"
                        if "next" in all_deps:
                            tech_stack["framework"] = "Next.js"
                    elif "vue" in all_deps:
                        tech_stack["framework"] = "Vue"
                        if "nuxt" in all_deps:
                            tech_stack["framework"] = "Nuxt.js"
                    elif "angular" in all_deps:
                        tech_stack["framework"] = "Angular"
                    elif "express" in all_deps:
                        tech_stack["framework"] = "Express"
            except Exception as e:
                logger.error(f"Error reading package.json: {e}")

        # Check for requirements.txt or pyproject.toml (Python)
        elif (self.project_path / "requirements.txt").exists() or (self.project_path / "pyproject.toml").exists():
            tech_stack["language"] = "Python"
            # Simple check for common python frameworks
            # (In a real implementation, we'd parse the files)
            files = [f.name for f in self.project_path.glob("**/*") if f.is_file()]
            if "manage.py" in files:
                 tech_stack["framework"] = "Django"
            # etc.

        return tech_stack

    def analyze_structure(self) -> Dict[str, Any]:
        """
        Combine structure scan and framework detection.
        """
        structure = self.scan_directory()
        tech_stack = self.detect_framework()

        return {
            "project_path": str(self.project_path),
            "structure": structure,
            "tech_stack": tech_stack
        }
