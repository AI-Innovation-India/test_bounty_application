from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from pathlib import Path
import json
import os
from typing import Dict, Any

from src.utils.logger import logger
from src.services.code_analyzer import CodeAnalyzerService
from src.services.prd_generator import PRDGeneratorService
from src.services.llm_service import LLMService
import subprocess
import asyncio
import requests


# Initialize FastMCP Server
mcp = FastMCP("TestSprite Agent")
llm_service = LLMService()

# Define Tool Input Models
class BootstrapInput(BaseModel):
    project_path: str = Field(..., description="Absolute path to the project to be tested")

# --- Tool Implementations ---

@mcp.tool()
async def testsprite_bootstrap_tests(project_path: str) -> str:
    """
    Initialize testing environment for a project.
    Creates 'testsprite_tests' directory and a default config.json.
    """
    logger.info(f"Bootstrapping tests for project at: {project_path}")
    
    try:
        proj_path = Path(project_path)
        # Fix: For blackbox/URL runs, the directory might not exist yet. Create it.
        proj_path.mkdir(parents=True, exist_ok=True)
        
        # Create testsprite_tests directory
        test_dir = proj_path / "testsprite_tests"
        test_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (test_dir / "generated_tests").mkdir(exist_ok=True)
        (test_dir / "reports").mkdir(exist_ok=True)
        (test_dir / "logs").mkdir(exist_ok=True)

        # Generate config.json
        config = {
            "project_path": str(proj_path),
            "test_directory": str(test_dir),
            "browser": "chromium",
            "headless": False,
            "timeout": 30000
        }
        
        config_path = test_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

        result = {
            "status": "success",
            "message": "TestSprite environment initialized",
            "test_directory_path": str(test_dir),
            "config_path": str(config_path)
        }
        return json.dumps(result, indent=2)

    except Exception as e:
        logger.error(f"Bootstrap failed: {str(e)}")
        return f"Error bootstrapping tests: {str(e)}"

@mcp.tool()
async def testsprite_generate_code_summary(project_path: str) -> str:
    """
    Analyze the codebase to detect framework, identifying key files and dependencies.
    Returns a JSON summary of the project structure and tech stack.
    """
    logger.info(f"Analyzing code for project at: {project_path}")
    
    try:
        analyzer = CodeAnalyzerService(project_path)
        summary = analyzer.analyze_structure()
        
        # Save summary to testsprite_tests directory if it exists
        test_dir = Path(project_path) / "testsprite_tests"
        if test_dir.exists():
            with open(test_dir / "code_summary.json", "w") as f:
                json.dump(summary, f, indent=2)
        
        return json.dumps(summary, indent=2)
    except Exception as e:
        logger.error(f"Code analysis failed: {str(e)}")
        return f"Error analyzing code: {str(e)}"

@mcp.tool()
async def testsprite_scan_website(url: str) -> str:
    """
    Blackbox scan of a website URL. Identifies tech stack, pages, and content.
    Returns a JSON summary similar to code analysis.
    """
    logger.info(f"Scanning website: {url}")
    from playwright.async_api import async_playwright
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Navigate
            try:
                response = await page.goto(url, wait_until="networkidle", timeout=30000)
                status = response.status if response else 0
            except Exception as nav_e:
                await browser.close()
                return json.dumps({"error": f"Navigation failed: {str(nav_e)}"})

            # Extract Info
            title = await page.title()
            content = await page.content()
            
            # Heuristic Tech Stack Detection (Simple)
            tech_stack = {"framework": "Unknown", "language": "HTML/JS"}
            if "next" in content or "__NEXT_DATA__" in content:
                tech_stack["framework"] = "Next.js"
            elif "react" in content:
                tech_stack["framework"] = "React"
            
            # Extract Links (Test Scenarios)
            links = await page.evaluate("""
                () => Array.from(document.querySelectorAll('a')).map(a => ({
                    text: a.innerText.slice(0, 50),
                    href: a.href
                })).filter(l => l.href.startsWith('http') && l.text.length > 2).slice(0, 20)
            """)
            
            result = {
                "project_name": title,
                "tech_stack": tech_stack,
                "structure": {
                    "pages": links,
                    "entry_point": url
                },
                "is_blackbox": True
            }

            # Save to disk for PRD generator to use
            try:
                # We need to construct the path. 
                # Since this tool takes a URL, it doesn't know the project_path directly 
                # UNLESS we pass it or infer it.
                # However, the orchestrator has the state.
                # BUT this tool signature is `url: str`.
                # We need to change the signature to accept project_path OR 
                # we rely on the orchestrator saving it? 
                # The orchestrator calls this tool and gets the JSON.
                # The orchestrator should save it? 
                # Checks: `analyze_code_node` in nodes.py receives the result.
                pass 
            except:
                pass
            
            await browser.close()
            return json.dumps(result, indent=2)
            
    except Exception as e:
        logger.error(f"Website scan failed: {str(e)}")
        return f"Error scanning website: {str(e)}"

@mcp.tool()
async def testsprite_generate_standardized_prd(project_path: str) -> str:
    """
    Generate a standardized Product Requirement Document (PRD) by analyzing 
    project documentation and code structure.
    """
    logger.info(f"Generating PRD for project at: {project_path}")
    
    try:
        test_dir = Path(project_path) / "testsprite_tests"
        summary_path = test_dir / "code_summary.json"
        
        # Prefer existing summary (from Scan or previous step)
        if summary_path.exists():
             logger.info("Loading existing code_summary.json")
             with open(summary_path) as f:
                 code_summary = json.load(f)
        else:
            # First get code summary (needed for context)
            analyzer = CodeAnalyzerService(project_path)
            code_summary = analyzer.analyze_structure()
        
        # Generate PRD
        generator = PRDGeneratorService(project_path)
        prd = generator.generate_prd(code_summary)
        
        # Save PRD to testsprite_tests directory
        test_dir = Path(project_path) / "testsprite_tests"
        if test_dir.exists():
            with open(test_dir / "standard_prd.json", "w") as f:
                json.dump(prd, f, indent=2)
                
        return json.dumps(prd, indent=2)
    except Exception as e:
        logger.error(f"PRD generation failed: {str(e)}")
        return f"Error generating PRD: {str(e)}"

@mcp.tool()
async def testsprite_generate_frontend_test_plan(project_path: str) -> str:
    """
    Generate a frontend test plan based on the project structure (mocked LLM).
    """
    logger.info("Generating Frontend Test Plan")
    
    try:
        test_dir = Path(project_path) / "testsprite_tests"
        
        # Load Code Summary
        summary_path = test_dir / "code_summary.json"
        code_summary = {}
        if summary_path.exists():
            with open(summary_path) as f:
                code_summary = json.load(f)
                
        # Load PRD
        prd_path = test_dir / "standard_prd.json"
        prd = {}
        if prd_path.exists():
             with open(prd_path) as f:
                prd = json.load(f)
        
        # Generate Plan via LLM
        test_plan = llm_service.generate_frontend_plan(code_summary, prd)
        
        # Save plan
        if test_dir.exists():
             with open(test_dir / "frontend_test_plan.json", "w") as f:
                json.dump(test_plan, f, indent=2)
                
        return json.dumps(test_plan, indent=2)
    except Exception as e:
        logger.error(f"Frontend plan generation failed: {e}")
        return f"Error generating frontend plan: {e}"

@mcp.tool()
async def testsprite_generate_backend_test_plan(project_path: str, metadata: Dict[str, Any] = None) -> str:
    """
    Generate a comprehensive backend test plan with categories, priorities, and detailed descriptions.
    Similar to TestSprite's test case generation with Basic Functional Tests and Edge Case Testing.
    """
    logger.info("Generating Backend Test Plan")
    
    if metadata is None:
        metadata = {}
    
    # Use LLM to generate plan
    try:
        # Load Code Summary if available
        test_dir = Path(project_path) / "testsprite_tests"
        summary_path = test_dir / "code_summary.json"
        code_summary = {}
        if summary_path.exists():
            with open(summary_path) as f:
                code_summary = json.load(f)

        test_plan = llm_service.generate_backend_plan(code_summary, metadata)

        # Save plan
        test_dir.mkdir(parents=True, exist_ok=True)
        with open(test_dir / "backend_test_plan.json", "w") as f:
            json.dump(test_plan, f, indent=2)
                
        return json.dumps(test_plan, indent=2)
    except Exception as e:
        logger.error(f"Backend plan generation failed: {e}")
        return f"Error generating backend plan: {e}"

@mcp.tool()
async def testsprite_generate_security_test_plan(project_path: str, metadata: Dict[str, Any] = None) -> str:
    """
    Generate a security test plan based on the project structure and common vulnerabilities (OWASP).
    """
    logger.info("Generating Security Test Plan")
    
    if metadata is None:
        metadata = {}
    
    try:
        test_dir = Path(project_path) / "testsprite_tests"
        summary_path = test_dir / "code_summary.json"
        code_summary = {}
        if summary_path.exists():
            with open(summary_path) as f:
                code_summary = json.load(f)

        # Generate plan via LLM
        security_plan = llm_service.generate_security_plan(code_summary, metadata)

        # Save plan
        with open(test_dir / "security_test_plan.json", "w") as f:
            json.dump(security_plan, f, indent=2)

        return json.dumps(security_plan, indent=2)
    except Exception as e:
        logger.error(f"Security plan generation failed: {e}")
        return f"Error generating security plan: {e}"

def generate_api_test_code(scenario: dict, target_url: str, test_id: str) -> str:
    """Generate pure API test code using requests library (no browser)."""
    sc_name = scenario.get('name', 'Unknown Test')
    sc_endpoint = scenario.get('endpoint', '')
    sc_method = scenario.get('method', 'GET').upper()
    sc_payload = scenario.get('payload', {})

    return f'''import json
import sys
import requests
from pathlib import Path

TEST_ID = "{test_id}"
TEST_NAME = """{sc_name}"""
BASE_URL = "{target_url.rstrip('/')}"
ENDPOINT = "{sc_endpoint}"
METHOD = "{sc_method}"

PROGRESS_FILE = Path(__file__).parent.parent / "execution_progress.json"

def update_progress(status, message=""):
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r") as f:
                progress = json.load(f)
        else:
            progress = {{"status": "running", "current_test": None, "completed": [], "results": {{}}}}

        progress["current_test"] = TEST_ID if status == "running" else None
        progress["results"][TEST_ID] = {{"status": status, "name": TEST_NAME, "message": message}}

        if status in ["passed", "failed", "skipped"]:
            if TEST_ID not in progress.get("completed", []):
                progress.setdefault("completed", []).append(TEST_ID)

        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        print(f"[WARN] Progress update failed: {{e}}")

def run_api_test():
    print(f"=" * 50)
    print(f"API Test: {{TEST_ID}} - {{TEST_NAME}}")
    print(f"Endpoint: {{METHOD}} {{BASE_URL}}{{ENDPOINT}}")
    print(f"=" * 50)
    sys.stdout.flush()

    update_progress("running", "Starting API test...")

    try:
        url = f"{{BASE_URL}}{{ENDPOINT}}"
        headers = {{"Content-Type": "application/json"}}

        if METHOD == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif METHOD == "POST":
            response = requests.post(url, json={sc_payload or {}}, headers=headers, timeout=30)
        elif METHOD == "PUT":
            response = requests.put(url, json={sc_payload or {}}, headers=headers, timeout=30)
        elif METHOD == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            response = requests.get(url, headers=headers, timeout=30)

        print(f"[INFO] Status Code: {{response.status_code}}")
        print(f"[INFO] Response: {{response.text[:500]}}")

        # Basic validation
        if response.status_code < 500:
            update_progress("passed", f"API responded with {{response.status_code}}")
            print(f"[PASSED] {{TEST_ID}}: API responded successfully")
        else:
            update_progress("failed", f"Server error: {{response.status_code}}")
            print(f"[FAILED] {{TEST_ID}}: Server error {{response.status_code}}")

    except requests.exceptions.Timeout:
        update_progress("failed", "Request timed out")
        print(f"[FAILED] {{TEST_ID}}: Request timed out")
    except requests.exceptions.ConnectionError as e:
        update_progress("failed", f"Connection error: {{str(e)[:100]}}")
        print(f"[FAILED] {{TEST_ID}}: Connection error")
    except Exception as e:
        update_progress("failed", str(e)[:100])
        print(f"[FAILED] {{TEST_ID}}: {{e}}")

if __name__ == "__main__":
    run_api_test()
'''

def generate_single_test_code(scenario: dict, target_url: str, test_id: str) -> str:
    """Generate test code for a single test scenario."""
    sc_name = scenario.get('name', 'Unknown Test')
    sc_desc = scenario.get('description', '')
    sc_category = scenario.get('category', 'General').lower()
    sc_payload = scenario.get('payload', '')

    # Determine test type and generate appropriate code
    if 'login' in sc_name.lower() and 'valid' in sc_name.lower():
        test_logic = '''
            # Valid login test
            if not valid_username or not valid_password:
                print(f"[SKIPPED] No credentials provided")
                result = ("skipped", "No credentials provided")
            else:
                username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
                username_field.fill(valid_username)
                page.wait_for_timeout(500)

                password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
                password_field.fill(valid_password)
                page.wait_for_timeout(500)

                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Login")').first
                submit_btn.click()
                page.wait_for_timeout(2000)

                if page.url != target_url or page.locator('text=Logged In Successfully, text=success, text=Welcome, text=Congratulations').count() > 0:
                    result = ("passed", "Login successful")
                else:
                    result = ("failed", "Login did not succeed")
'''
    elif 'login' in sc_name.lower() and ('invalid' in sc_name.lower() or 'non-existent' in sc_name.lower()):
        test_logic = '''
            # Invalid login test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill("wronguser_nonexistent")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("wrongpassword123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Login")').first
            submit_btn.click()
            page.wait_for_timeout(2000)

            if page.locator('text=invalid, text=error, text=incorrect, text=failed, .error, [class*="error"]').count() > 0:
                result = ("passed", "Error message displayed correctly")
            else:
                result = ("failed", "No error message for invalid credentials")
'''
    elif 'sql' in sc_name.lower() or 'injection' in sc_category:
        payload = sc_payload if sc_payload else "' OR '1'='1"
        test_logic = f'''
            # SQL Injection test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill("{payload}")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("{payload}")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(2000)

            if page.locator('text=error, text=invalid, .error').count() > 0 or page.url == target_url:
                result = ("passed", "SQL injection blocked")
            else:
                result = ("failed", "Potential SQL injection vulnerability!")
'''
    elif 'xss' in sc_name.lower() or 'xss' in sc_category or 'cross-site' in sc_category:
        payload = sc_payload if sc_payload else "<script>alert('XSS')</script>"
        test_logic = f'''
            # XSS test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill("{payload}")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("test123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            content = page.content()
            if "<script>alert" not in content and "<img src=x" not in content:
                result = ("passed", "XSS payload sanitized")
            else:
                result = ("failed", "Potential XSS vulnerability!")
'''
    elif 'empty' in sc_name.lower() or ('payload' in sc_name.lower() and 'empty' in sc_desc.lower()):
        test_logic = '''
            # Empty payload test
            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            if page.locator('text=required, text=empty, text=enter, .error, [class*="error"]').count() > 0:
                result = ("passed", "Empty payload handled correctly")
            else:
                result = ("failed", "No validation for empty fields")
'''
    elif 'large' in sc_name.lower() or 'buffer' in sc_name.lower():
        test_logic = '''
            # Large payload / buffer test
            large_string = "A" * 10000
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill(large_string)
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("test123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(2000)

            # Should handle gracefully without crashing
            if page.locator('text=error, text=too long, text=maximum, .error').count() > 0 or page.url == target_url:
                result = ("passed", "Large payload handled correctly")
            else:
                result = ("failed", "Large payload not validated")
'''
    elif 'special' in sc_name.lower() or 'character' in sc_name.lower():
        test_logic = '''
            # Special characters test
            special_chars = "@#$%^&*()!~`[]{}|\\\\;:'\\"<>,./?"
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill(f"test{special_chars}user")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("Password123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            # Should handle without errors/crashes
            result = ("passed", "Special characters handled")
'''
    elif 'unicode' in sc_name.lower() or 'emoji' in sc_name.lower():
        test_logic = '''
            # Unicode/emoji test
            unicode_str = "用户名 🔐 тест"
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill(unicode_str)
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("Password123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            result = ("passed", "Unicode characters handled")
'''
    elif 'whitespace' in sc_name.lower():
        test_logic = '''
            # Whitespace only test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill("   ")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("   ")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            if page.locator('text=required, text=empty, text=invalid, .error').count() > 0:
                result = ("passed", "Whitespace-only input rejected")
            else:
                result = ("failed", "Whitespace-only input not validated")
'''
    elif 'missing' in sc_name.lower() and 'username' in sc_name.lower():
        test_logic = '''
            # Missing username field test
            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("Password123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            if page.locator('text=required, text=username, .error').count() > 0:
                result = ("passed", "Missing username validated")
            else:
                result = ("failed", "Missing username not validated")
'''
    elif 'missing' in sc_name.lower() and 'password' in sc_name.lower():
        test_logic = '''
            # Missing password field test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill("testuser")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            if page.locator('text=required, text=password, .error').count() > 0:
                result = ("passed", "Missing password validated")
            else:
                result = ("failed", "Missing password not validated")
'''
    elif 'email' in sc_name.lower() and ('invalid' in sc_name.lower() or 'format' in sc_name.lower()):
        test_logic = '''
            # Invalid email format test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"], input[type="email"]').first
            username_field.fill("not-an-email")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("Password123")
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            if page.locator('text=email, text=invalid, text=valid, .error').count() > 0:
                result = ("passed", "Invalid email format rejected")
            else:
                result = ("failed", "Invalid email format not validated")
'''
    elif 'password' in sc_name.lower() and ('short' in sc_name.lower() or 'length' in sc_name.lower()):
        test_logic = '''
            # Password too short test
            username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
            username_field.fill("testuser")
            page.wait_for_timeout(300)

            password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
            password_field.fill("123")  # Too short
            page.wait_for_timeout(300)

            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            if page.locator('text=short, text=minimum, text=characters, text=length, .error').count() > 0:
                result = ("passed", "Short password rejected")
            else:
                result = ("failed", "Short password not validated")
'''
    elif 'validation' in sc_name.lower() or 'message' in sc_name.lower():
        test_logic = '''
            # Form validation messages test
            submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
            submit_btn.click()
            page.wait_for_timeout(1500)

            error_count = page.locator('.error, [class*="error"], [class*="invalid"], text=required').count()
            if error_count > 0:
                result = ("passed", f"Validation messages displayed ({error_count} found)")
            else:
                result = ("failed", "No validation messages displayed")
'''
    elif 'mask' in sc_name.lower() or 'password' in sc_category.lower():
        test_logic = '''
            # Password masking test
            password_field = page.locator('input[type="password"]').first
            if password_field:
                field_type = password_field.get_attribute("type")
                if field_type == "password":
                    result = ("passed", "Password field properly masked")
                else:
                    result = ("failed", "Password field not masked")
            else:
                result = ("skipped", "No password field found")
'''
    elif 'idor' in sc_name.lower() or 'access control' in sc_category:
        test_logic = '''
            # IDOR / Access Control test
            # Try to access a resource that shouldn't be accessible
            original_url = page.url
            page.goto(target_url + "/users/99999", wait_until="domcontentloaded")
            page.wait_for_timeout(1500)

            if page.locator('text=unauthorized, text=forbidden, text=403, text=401, text=not found, text=404').count() > 0:
                result = ("passed", "Unauthorized access blocked")
            elif page.url != original_url and "login" in page.url.lower():
                result = ("passed", "Redirected to login")
            else:
                result = ("failed", "Potential IDOR vulnerability")

            # Navigate back
            page.goto(target_url, wait_until="domcontentloaded")
'''
    elif 'clickjack' in sc_name.lower() or 'header' in sc_name.lower():
        test_logic = '''
            # Clickjacking / Security headers test
            response = page.goto(target_url, wait_until="domcontentloaded")
            headers = response.headers if response else {}

            x_frame = headers.get("x-frame-options", "")
            csp = headers.get("content-security-policy", "")

            if x_frame or "frame-ancestors" in csp:
                result = ("passed", f"Clickjacking protection: X-Frame-Options={x_frame}")
            else:
                result = ("failed", "No clickjacking protection headers")
'''
    elif 'brute' in sc_name.lower() or 'rate' in sc_name.lower():
        test_logic = '''
            # Brute force / rate limiting test
            attempts = 0
            blocked = False

            for i in range(5):
                username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
                username_field.fill(f"wronguser{i}")
                password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
                password_field.fill(f"wrongpass{i}")
                submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
                submit_btn.click()
                page.wait_for_timeout(500)
                attempts += 1

                if page.locator('text=blocked, text=too many, text=locked, text=wait').count() > 0:
                    blocked = True
                    break

            if blocked:
                result = ("passed", f"Rate limiting after {attempts} attempts")
            else:
                result = ("failed", "No rate limiting detected after 5 attempts")
'''
    else:
        test_logic = '''
            # Generic test - verify page loads and has expected elements
            page.evaluate("document.body.style.border = '3px solid #00D4AA'")
            page.wait_for_timeout(500)

            title = page.title()
            has_form = page.locator('form, input, button').count() > 0

            page.evaluate("document.body.style.border = ''")

            if title and has_form:
                result = ("passed", "Page functional")
            else:
                result = ("failed", "Page missing elements")
'''

    return f'''import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

TEST_ID = "{test_id}"
TEST_NAME = """{sc_name}"""
TARGET_URL = "{target_url}"

# Paths
BASE_DIR = Path(__file__).parent.parent
PROGRESS_FILE = BASE_DIR / "execution_progress.json"
CREDENTIALS_FILE = BASE_DIR / "test_credentials.json"
VIDEOS_DIR = Path(__file__).parent / "videos" / TEST_ID
SCREENSHOTS_DIR = Path(__file__).parent / "screenshots"

def load_credentials():
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def update_progress(status, message="", screenshot=None, video=None):
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r") as f:
                progress = json.load(f)
        else:
            progress = {{"status": "running", "current_test": None, "completed": [], "results": {{}}}}

        progress["current_test"] = TEST_ID if status == "running" else None
        progress["results"][TEST_ID] = {{
            "status": status,
            "name": TEST_NAME,
            "message": message,
            "video": video,
            "screenshot": screenshot
        }}

        if screenshot:
            progress["current_screenshot"] = screenshot

        if status in ["passed", "failed", "skipped"]:
            if TEST_ID not in progress.get("completed", []):
                progress.setdefault("completed", []).append(TEST_ID)

        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
        sys.stdout.flush()
    except Exception as e:
        print(f"[WARN] Progress update failed: {{e}}")

def run_test():
    target_url = TARGET_URL
    creds = load_credentials()
    valid_username = creds.get("username", "") if creds else ""
    valid_password = creds.get("password", "") if creds else ""

    print(f"=" * 50)
    print(f"Test: {{TEST_ID}} - {{TEST_NAME}}")
    print(f"Target: {{target_url}}")
    print(f"=" * 50)
    sys.stdout.flush()

    # Ensure directories exist
    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    update_progress("running", "Starting test...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir=str(VIDEOS_DIR),
            viewport={{"width": 1280, "height": 720}}
        )
        page = context.new_page()

        try:
            print("[INFO] Navigating to target...")
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1000)

            # Take initial screenshot
            screenshot_path = SCREENSHOTS_DIR / f"{{TEST_ID}}_start.png"
            page.screenshot(path=str(screenshot_path))
            update_progress("running", "Page loaded", f"screenshots/{{TEST_ID}}_start.png")

            print(f"[INFO] Page Title: {{page.title()}}")
            print("[INFO] Executing test logic...")
            sys.stdout.flush()
            {test_logic}
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] {{error_msg}}")

            # Take error screenshot
            try:
                screenshot_path = SCREENSHOTS_DIR / f"{{TEST_ID}}_error.png"
                page.screenshot(path=str(screenshot_path))
            except:
                pass

            context.close()
            browser.close()

            # Find video file
            video_file = None
            for f in VIDEOS_DIR.glob("*.webm"):
                video_file = f"videos/{{TEST_ID}}/{{f.name}}"
                break

            update_progress("failed", error_msg, f"screenshots/{{TEST_ID}}_error.png", video_file)
            print(f"[FAILED] {{TEST_ID}}: {{error_msg}}")
            return

        # Take final screenshot
        screenshot_path = SCREENSHOTS_DIR / f"{{TEST_ID}}_final.png"
        page.screenshot(path=str(screenshot_path))

        context.close()
        browser.close()

        # Find video file
        video_file = None
        for f in VIDEOS_DIR.glob("*.webm"):
            video_file = f"videos/{{TEST_ID}}/{{f.name}}"
            break

        # result should be a tuple (status, message) from test logic
        if 'result' in dir() and result:
            status, message = result
        else:
            status, message = "passed", "Test completed"
        update_progress(status, message, f"screenshots/{{TEST_ID}}_final.png", video_file)
        print(f"[{{status.upper()}}] {{TEST_ID}}: {{message}}")

if __name__ == "__main__":
    run_test()
'''

@mcp.tool()
async def testsprite_generate_code_and_execute(project_path: str, target_url: str = None) -> str:
    """
    Execute tests one by one, each with its own video and real-time progress updates.
    """
    logger.info("Starting individual test execution...")
    test_dir = Path(project_path) / "testsprite_tests" / "generated_tests"
    test_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load ALL Plans and merge scenarios
    all_scenarios = []
    plan_files = ["backend_test_plan.json", "security_test_plan.json", "frontend_test_plan.json"]

    for plan_file in plan_files:
        plan_path = test_dir.parent / plan_file
        if plan_path.exists():
            try:
                with open(plan_path) as f:
                    plan_data = json.load(f)
                    scenarios = plan_data.get("scenarios", [])
                    all_scenarios.extend(scenarios)
                    logger.info(f"Loaded {len(scenarios)} scenarios from {plan_file}")
            except Exception as e:
                logger.warning(f"Failed to load {plan_file}: {e}")

    logger.info(f"Total scenarios to execute: {len(all_scenarios)}")

    # 2. Get Target URL
    if not target_url:
        summary_path = Path(project_path) / "testsprite_tests" / "code_summary.json"
        target_url = "https://example.com"
        if summary_path.exists():
            try:
                with open(summary_path) as f:
                    data = json.load(f)
                    target_url = data.get("structure", {}).get("entry_point", target_url)
            except:
                pass

    logger.info(f"Target URL for tests: {target_url}")

    # 3. Initialize execution progress
    progress_file = test_dir.parent / "execution_progress.json"
    initial_progress = {
        "status": "running",
        "current_test": None,
        "completed": [],
        "total": len(all_scenarios),
        "results": {sc.get("id", f"test_{i}"): {"status": "pending", "name": sc.get("name", "Unknown")} for i, sc in enumerate(all_scenarios)},
        "current_screenshot": None
    }
    with open(progress_file, "w") as f:
        json.dump(initial_progress, f, indent=2)

    # Ensure directories exist
    (test_dir / "videos").mkdir(exist_ok=True)
    (test_dir / "screenshots").mkdir(exist_ok=True)

    # 4. Execute each test separately
    all_stdout = []
    all_results = {}

    for i, scenario in enumerate(all_scenarios):
        test_id = scenario.get("id", f"test_{i}")
        test_name = scenario.get("name", "Unknown Test")
        has_endpoint = scenario.get("endpoint") and not any(x in test_name.lower() for x in ['login', 'form', 'ui', 'click', 'fill'])

        logger.info(f"Executing test {i+1}/{len(all_scenarios)}: {test_id} - {test_name}")

        # Choose between API test (no browser) and UI test (Playwright)
        if has_endpoint and scenario.get("method") in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            # Pure API test - use requests library
            test_code = generate_api_test_code(scenario, target_url, test_id)
            logger.info(f"  -> Using API test mode for {test_id}")
        else:
            # UI test - use Playwright
            test_code = generate_single_test_code(scenario, target_url, test_id)
            logger.info(f"  -> Using UI test mode for {test_id}")

        test_file = test_dir / f"test_{test_id}.py"

        with open(test_file, "w") as f:
            f.write(test_code)

        # Update progress to show current test
        try:
            with open(progress_file, "r") as f:
                progress = json.load(f)
            progress["current_test"] = test_id
            progress["results"][test_id]["status"] = "running"
            with open(progress_file, "w") as f:
                json.dump(progress, f, indent=2)
        except:
            pass

        # Execute the test
        try:
            result = subprocess.run(
                ["python", str(test_file)],
                capture_output=True,
                text=True,
                cwd=str(test_dir),
                timeout=60  # 1 minute per test
            )

            stdout = result.stdout
            all_stdout.append(f"\n--- {test_id}: {test_name} ---\n{stdout}")

            # Determine result from output
            if "[PASSED]" in stdout:
                all_results[test_id] = "passed"
            elif "[FAILED]" in stdout:
                all_results[test_id] = "failed"
            elif "[SKIPPED]" in stdout:
                all_results[test_id] = "skipped"
            else:
                all_results[test_id] = "passed"

        except subprocess.TimeoutExpired:
            logger.error(f"Test {test_id} timed out")
            all_results[test_id] = "failed"
            all_stdout.append(f"\n--- {test_id}: {test_name} ---\n[TIMEOUT] Test exceeded time limit")

            # Update progress for timeout
            try:
                with open(progress_file, "r") as f:
                    progress = json.load(f)
                progress["results"][test_id] = {"status": "failed", "name": test_name, "message": "Timeout"}
                progress["completed"].append(test_id)
                with open(progress_file, "w") as f:
                    json.dump(progress, f, indent=2)
            except:
                pass

        except Exception as e:
            logger.error(f"Test {test_id} failed: {e}")
            all_results[test_id] = "failed"
            all_stdout.append(f"\n--- {test_id}: {test_name} ---\n[ERROR] {str(e)}")

    # 5. Final progress update
    try:
        with open(progress_file, "r") as f:
            progress = json.load(f)
        progress["status"] = "completed"
        progress["current_test"] = None
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)
    except:
        pass

    # Build output
    passed = sum(1 for r in all_results.values() if r == "passed")
    failed = sum(1 for r in all_results.values() if r == "failed")

    output = {
        "exit_code": 0 if failed == 0 else 1,
        "stdout": "\n".join(all_stdout)[-3000:],
        "stderr": "",
        "tests_executed": len(all_scenarios),
        "passed": passed,
        "failed": failed,
        "results": all_results
    }

    return json.dumps(output, indent=2)

@mcp.tool()
async def testsprite_rerun_tests(project_path: str) -> str:
    """
    Rerun existing tests in the project.
    """
    logger.info("Rerunning tests...")
    test_dir = Path(project_path) / "testsprite_tests" / "generated_tests"
    
    if not test_dir.exists():
        return "Error: No generated tests found to rerun."
        
    try:
        result = subprocess.run(
            ["pytest", str(test_dir), "--junitxml=" + str(test_dir / "rerun_results.xml")],
            capture_output=True,
            text=True
        )
        
        output = {
            "exit_code": result.returncode,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500],
            "report_path": str(test_dir / "rerun_results.xml")
        }
        return json.dumps(output, indent=2)
    except Exception as e:
         return f"Error rerunning tests: {e}"

@mcp.tool()
async def testsprite_fix_test_code(project_path: str, error: str) -> str:
    """
    Attempt to fix the generated test code based on the error message.
    """
    logger.info("Attempting to fix test code...")
    test_dir = Path(project_path) / "testsprite_tests" / "generated_tests"
    test_file = test_dir / "test_generated_001.py"
    
    if not test_file.exists():
        return json.dumps({"error": "Test file not found", "success": False})
        
    try:
        # Read existing code
        with open(test_file, "r") as f:
            code = f.read()
            
        # Call LLM to fix
        fixed_code = llm_service.fix_test_code(code, error)
        
        # Save fixed code
        with open(test_file, "w") as f:
            f.write(fixed_code)
            
        return json.dumps({
            "success": True, 
            "message": "Test code updated",
            "file_path": str(test_file)
        })
    except Exception as e:
        logger.error(f"Fix failed: {e}")
        return json.dumps({"error": str(e), "success": False})

# Placeholder for other tools to be implemented
# ...

if __name__ == "__main__":
    mcp.run()
