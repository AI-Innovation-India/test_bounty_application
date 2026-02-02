from pathlib import Path
import json
import asyncio
from typing import Dict, Any

from src.agents.state import TestingState
from src.utils.logger import logger

# Import services/tools directly to use in nodes
from src.mcp_server.server import (
    testsprite_bootstrap_tests,
    testsprite_generate_code_summary,
    testsprite_scan_website,
    testsprite_generate_standardized_prd,
    testsprite_generate_frontend_test_plan,
    testsprite_generate_backend_test_plan,
    testsprite_generate_code_and_execute,
    testsprite_fix_test_code,
    testsprite_generate_security_test_plan
)

from src.services.report_service import ReportGeneratorService

async def bootstrap_node(state: TestingState) -> TestingState:
    logger.info("Node: Bootstrap")
    try:
        result_json = await testsprite_bootstrap_tests(state["project_path"])
        result = json.loads(result_json)
        return {
            "bootstrap_result": result,
            "steps_completed": ["bootstrap"]
        }
    except Exception as e:
        logger.error(f"Bootstrap node failed: {e}")
        return {"error_log": [f"Bootstrap failed: {e}"]}

async def analyze_code_node(state: TestingState) -> TestingState:
    logger.info("Node: Analyze")
    try:
        # Check if URL mode
        if state.get("target_url"):
            logger.info("Using Blackbox Scanner")
            result_json = await testsprite_scan_website(state["target_url"])
        else:
             logger.info("Using Static Analyzer")
             result_json = await testsprite_generate_code_summary(state["project_path"])
             
        result = json.loads(result_json)
        
        # Save summary to disk so subsequent steps (PRD, Plans) can use it
        try:
            p_path = Path(state["project_path"])
            # Ensure folder exists (bootstrap handles it, but just in case)
            (p_path / "testsprite_tests").mkdir(exist_ok=True)
            
            with open(p_path / "testsprite_tests" / "code_summary.json", "w") as f:
                json.dump(result, f, indent=2)
            logger.info("Saved code_summary.json to disk")
        except Exception as save_err:
             logger.error(f"Failed to save code_summary: {save_err}")
        
        project_type = result.get("tech_stack", {}).get("framework", "Unknown")
        
        return {
            "code_summary": result,
            "project_type": project_type,
            "steps_completed": ["analyze"]
        }
    except Exception as e:
        return {"error_log": [f"Analysis failed: {e}"]}

async def generate_prd_node(state: TestingState) -> TestingState:
    logger.info("Node: Generate PRD")
    try:
        result_json = await testsprite_generate_standardized_prd(state["project_path"])
        result = json.loads(result_json)
        return {
            "prd": result,
            "steps_completed": ["prd"]
        }
    except Exception as e:
        return {"error_log": [f"PRD generation failed: {e}"]}

async def frontend_plan_node(state: TestingState) -> TestingState:
    logger.info("Node: Frontend Plan")
    try:
        result_json = await testsprite_generate_frontend_test_plan(state["project_path"])
        result = json.loads(result_json)
        return {
            "frontend_plan": result,
            "steps_completed": ["frontend_plan"]
        }
    except Exception as e:
        return {"error_log": [f"Frontend planning failed: {e}"]}

async def backend_plan_node(state: TestingState) -> TestingState:
    logger.info("Node: Backend Plan")
    try:
        # Pass metadata for richer test case generation
        metadata = {
            "test_name": state.get("test_name"),
            "api_name": state.get("api_name"),
            "auth_type": state.get("auth_type"),
            "extra_info": state.get("extra_info"),
            "target_url": state.get("target_url")
        }
        result_json = await testsprite_generate_backend_test_plan(state["project_path"], metadata)
        result = json.loads(result_json)
        return {
            "backend_plan": result,
            "steps_completed": ["backend_plan"]
        }
    except Exception as e:
        return {"error_log": [f"Backend planning failed: {e}"]}

async def security_plan_node(state: TestingState) -> TestingState:
    logger.info("Node: Security Plan")
    try:
        # Generate OWASP Top 10 vulnerabilities plan
        metadata = {
            "target_url": state.get("target_url"),
            "test_name": state.get("test_name"),
            "extra_info": state.get("extra_info")
        }
        result_json = await testsprite_generate_security_test_plan(state["project_path"], metadata)
        result = json.loads(result_json)
        return {
            "security_plan": result,
            "steps_completed": ["security_plan"]
        }
    except Exception as e:
        logger.error(f"Security planning failed: {e}")
        # Don't fail the whole run if security scan fails
        return {"error_log": [f"Security planning failed: {e}"]}

async def execute_tests_node(state: TestingState) -> TestingState:
    logger.info("Node: Execute Tests")
    try:
        # Pass target_url from state to ensure tests navigate to correct URL
        target_url = state.get("target_url", None)
        logger.info(f"Executing tests with target_url: {target_url}")
        result_json = await testsprite_generate_code_and_execute(state["project_path"], target_url)
        result = json.loads(result_json)
        return {
            "test_results": result,
            "steps_completed": ["execute"]
        }
    except Exception as e:
        return {"error_log": [f"Execution failed: {e}"]}

async def report_node(state: TestingState) -> TestingState:
    logger.info("Node: Report")
    
    try:
        project_path = state["project_path"]
        test_results = state.get("test_results", {})
        code_summary = state.get("code_summary", {})
        
        generator = ReportGeneratorService(project_path)
        
        # Generate reports
        html_path = generator.generate_html_report(test_results, code_summary)
        md_path = generator.generate_markdown_report(test_results)
        
        return {
            "report_path": html_path,
            "steps_completed": ["report"]
        }
    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {"error_log": [f"Report generation failed: {e}"]}

async def fix_tests_node(state: TestingState) -> TestingState:
    logger.info("Node: Fix Tests")
    try:
        results = state.get("test_results", {})
        error_msg = results.get("stderr", "") + "\n" + results.get("stdout", "")
        
        # Call fix tool
        result_json = await testsprite_fix_test_code(state["project_path"], error_msg)
        result = json.loads(result_json)
        
        if result.get("success"):
            return {
                "retries": state.get("retries", 0) + 1,
                "steps_completed": ["fix_tests"]
            }
        else:
             return {
                "retries": state.get("retries", 0) + 1,
                "error_log": [f"Fix failed: {result.get('error')}"]
            }
            
    except Exception as e:
        return {"error_log": [f"Fix node failed: {e}"]}
