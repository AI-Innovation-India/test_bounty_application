import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from src.utils.logger import logger

class ReportGeneratorService:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.report_dir = self.project_path / "testsprite_tests" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, test_results: Dict[str, Any], code_summary: Dict[str, Any]) -> str:
        """
        Generate a comprehensive HTML report.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tech_stack = code_summary.get("tech_stack", {})
        
        # Simple HTML Template
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>TestSprite Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #333; color: #fff; padding: 10px; }}
                .summary {{ margin-top: 20px; padding: 15px; background: #f4f4f4; }}
                .results {{ margin-top: 20px; }}
                .pass {{ color: green; font-weight: bold; }}
                .fail {{ color: red; font-weight: bold; }}
                pre {{ background: #eee; padding: 10px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>TestSprite Autonomous Test Report</h1>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="summary">
                <h2>Project Summary</h2>
                <p><strong>Path:</strong> {self.project_path}</p>
                <p><strong>Framework:</strong> {tech_stack.get("framework", "Unknown")}</p>
                <p><strong>Language:</strong> {tech_stack.get("language", "Unknown")}</p>
            </div>
            
            <div class="results">
                <h2>Execution Results</h2>
                <p><strong>Exit Code:</strong> {test_results.get("exit_code", "N/A")}</p>
                
                <h3>Output (Last 500 chars)</h3>
                <pre>{test_results.get("stdout", "No output")}</pre>
                
                <h3>Errors</h3>
                <pre>{test_results.get("stderr", "No errors")}</pre>
                
                <h3>JUnit XML Report</h3>
                <p>Saved to: {test_results.get("report_path", "N/A")}</p>
            </div>
        </body>
        </html>
        """
        
        report_path = self.report_dir / "report.html"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML report generated: {report_path}")
        return str(report_path)

    def generate_markdown_report(self, test_results: Dict[str, Any]) -> str:
        """
        Generate a summary Markdown report.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        md_content = f"# TestSprite Report\n\n"
        md_content += f"**Generated:** {timestamp}\n\n"
        md_content += f"## Results\n\n"
        md_content += f"- **Exit Code:** {test_results.get('exit_code')}\n"
        md_content += f"- **Report Path:** {test_results.get('report_path')}\n\n"
        md_content += f"### Stdout\n```\n{test_results.get('stdout')}\n```\n"
        
        report_path = self.report_dir / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(md_content)
            
        logger.info(f"Markdown report generated: {report_path}")
        return str(report_path)
