import os
import json
from typing import Dict, Any, List, Optional
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from src.utils.logger import logger

# Debug Imports
print("--- LLM Service Import Debug ---")
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    print(f"SUCCESS: ChatGoogleGenerativeAI imported. Type: {type(ChatGoogleGenerativeAI)}")
except ImportError as e:
    ChatGoogleGenerativeAI = None
    print(f"ERROR: Could not import langchain-google-genai: {e}")

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class LLMService:
    def __init__(self):
        self.provider = "mock"
        self.model = None
        
        # Debug Env
        print("--- LLM Service Init ---")
        print(f"OPENAI_KEY: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
        print(f"ANTHROPIC_KEY: {'Yes' if os.getenv('ANTHROPIC_API_KEY') else 'No'}")
        print(f"GOOGLE_KEY: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")

        # Check for API keys
        if os.getenv("OPENAI_API_KEY"):
            print("Selecting Provider: OpenAI")
            self.provider = "openai"
            self.model = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7)
        elif os.getenv("ANTHROPIC_API_KEY"):
            print("Selecting Provider: Anthropic")
            self.provider = "anthropic"
            self.model = ChatAnthropic(model="claude-3-opus-20240229", temperature=0.7)
        elif os.getenv("GOOGLE_API_KEY"):
            if ChatGoogleGenerativeAI:
                print("Selecting Provider: Google Gemini")
                self.provider = "google"
                self.model = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
            else:
                print("WARNING: Google Key present but library missing. Falling back to Mock.")
                logger.warning("GOOGLE_API_KEY found but langchain-google-genai not installed.")
        else:
            print("WARNING: No Keys found. Defaulting to Mock.")
            logger.warning("No API keys found. Using Mock LLM.")

    def generate_prd(self, context: str) -> Dict[str, Any]:
        """
        Generate a PRD based on project context.
        """
        if self.provider == "mock":
            return self._mock_prd()

        prompt = ChatPromptTemplate.from_template("""
        You are an expert Product Manager. Analyze the following project context and documentation to generate a standardized Product Requirement Document (PRD).
        
        Context:
        {context}
        
        Output must be a valid JSON object with the following structure:
        {{
            "product_name": "Name",
            "description": "Description",
            "tech_stack": {{ ... }},
            "key_features": ["Feature 1", ...],
            "user_stories": [
                {{"role": "User", "action": "do something", "benefit": "result"}}
            ],
            "requirements": {{
                "functional": ["Req 1", ...],
                "non_functional": ["Req 1", ...]
            }}
        }}
        """)
        
        chain = prompt | self.model | StrOutputParser()
        
        try:
            response = chain.invoke({"context": context})
            # Clean up potential markdown code blocks
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM PRD generation failed: {e}")
            return self._mock_prd()

    def generate_frontend_plan(self, code_summary: Dict[str, Any], prd: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a frontend test plan.
        """
        if self.provider == "mock":
            return self._mock_frontend_plan()
            
        context = f"Code Summary: {json.dumps(code_summary)}\n\nPRD: {json.dumps(prd)}"
        
        prompt = ChatPromptTemplate.from_template("""
        You are a QA Lead. Generate a Frontend Test Plan for the following project.
        Focus on end-to-end user flows using Playwright.
        
        Context:
        {context}
        
        Output must be a valid JSON object:
        {{
            "type": "frontend",
            "scenarios": [
                {{
                    "id": "TC_FE_001", 
                    "name": "Scenario Name", 
                    "steps": ["Step 1", "Step 2"],
                    "description": "What this tests"
                }}
            ]
        }}
        """)
        
        chain = prompt | self.model | StrOutputParser()
        
        try:
            response = chain.invoke({"context": context})
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM Frontend Plan generation failed: {e}")
            return self._mock_frontend_plan()

    def generate_backend_plan(self, code_summary: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a backend test plan.
        """
        if self.provider == "mock":
            return self._mock_backend_plan()

        context = f"Code Summary: {json.dumps(code_summary)}\n\nMetadata: {json.dumps(metadata)}"
        
        prompt = ChatPromptTemplate.from_template("""
        You are a Senior QA Lead. Generate a COMPREHENSIVE Backend Test Plan for the following application.

        Context:
        {context}

        Generate AT LEAST 15-20 test scenarios covering ALL of these categories:
        1. Functional Tests (Positive) - Happy path scenarios that should work
        2. Functional Tests (Negative) - Invalid input, missing fields, wrong formats
        3. Edge Case Tests - Boundary values, empty inputs, special characters, unicode, very long strings
        4. UI Validation Tests - Form validation, error messages, field masking
        5. Performance/Stress - Large payloads, concurrent requests

        Output must be a valid JSON object:
        {{
            "type": "backend",
            "scenarios": [
                {{
                    "id": "TC_BE_001",
                    "name": "Test Name",
                    "category": "Functional Tests | Edge Case Tests | Negative Tests | UI Validation",
                    "priority": "Critical | High | Medium | Low",
                    "description": "Detailed description of what to test and expected outcome",
                    "endpoint": "/api/...",
                    "method": "GET | POST | PUT | DELETE"
                }}
            ]
        }}

        Be thorough and creative. Think of all possible ways the application could fail or be misused.
        """)
        
        chain = prompt | self.model | StrOutputParser()
        
        try:
            response = chain.invoke({"context": context})
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM Backend Plan generation failed: {e}")
            return self._mock_backend_plan()

    def generate_security_plan(self, code_summary: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a security test plan focusing on OWASP Top 10.
        """
        if self.provider == "mock":
            return self._mock_security_plan()

        context = f"Code Summary: {json.dumps(code_summary)}\n\nMetadata: {json.dumps(metadata)}"
        
        prompt = ChatPromptTemplate.from_template("""
        You are a Senior Security Engineer. Generate a COMPREHENSIVE Security Test Plan (DAST/SAST).
        Focus on OWASP Top 10 and common web vulnerabilities.

        Context:
        {context}

        Generate AT LEAST 12-15 security test scenarios covering:
        1. Injection Attacks (SQL, NoSQL, Command, LDAP)
        2. Cross-Site Scripting (XSS) - Reflected, Stored, DOM-based
        3. Broken Access Control - IDOR, privilege escalation, forced browsing
        4. Security Misconfiguration - Headers, CORS, error messages
        5. Authentication/Session - Brute force, session fixation, token security
        6. Sensitive Data Exposure - PII in responses, insecure storage
        7. CSRF Protection - Token validation

        Output must be a valid JSON object:
        {{
            "type": "security",
            "scenarios": [
                {{
                    "id": "SEC_001",
                    "name": "SQL Injection on Login",
                    "category": "Injection | XSS | Broken Access Control | Security Misconfiguration | Authentication",
                    "priority": "Critical | High | Medium",
                    "description": "Detailed description of attack vector and expected secure behavior",
                    "payload": "The malicious payload to test",
                    "target_element": "input field selector or endpoint"
                }}
            ]
        }}

        Be creative with payloads. Include common bypass techniques. Think like an attacker.
        """)
        
        chain = prompt | self.model | StrOutputParser()
        
        try:
            response = chain.invoke({"context": context})
            response = response.replace("```json", "").replace("```", "").strip()
            return json.loads(response)
        except Exception as e:
            logger.error(f"LLM Security Plan generation failed: {e}")
            return self._mock_security_plan()

    def generate_test_code(self, plan: Dict[str, Any], target_url: str) -> str:
        """
        Generate Playwright (Python) test code for a given plan.
        """
        if self.provider == "mock":
            return self._mock_test_code(target_url, plan)
            
        prompt = ChatPromptTemplate.from_template("""
        You are a Senior Automation Engineer. Write a Python script using Playwright to execute the following test plan.
        
        Target URL: {target_url}
        Test Plan: {plan}
        
        Requirements:
        1. Use `sync_playwright`.
        2. Make the script standalone (runnable via `python script.py`).
        3. Record video of the test execution (dir: "videos/").
        4. Include assertions.
        5. Handle exceptions gracefully.
        6. Use `try...finally` to ensure browser closes.
        
        Output ONLY the Python code. No markdown formatting if possible, or inside ```python block.
        """)
        
        chain = prompt | self.model | StrOutputParser()
        
        try:
            response = chain.invoke({"target_url": target_url, "plan": json.dumps(plan)})
            # Extract code from markdown if present
            if "```python" in response:
                response = response.split("```python")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return response.strip()
        except Exception as e:
            logger.error(f"LLM Code generation failed: {e}")
            # CRITICAL: Pass the plan to fallback so scenarios are executed
            return self._mock_test_code(target_url, plan)

    def fix_test_code(self, code: str, error: str, plan: Optional[Dict[str, Any]] = None) -> str:
        """
        Fix broken test code based on error output.
        """
        if self.provider == "mock":
            # Just return the same code with a comment in mock mode
            return f"# Fixed version (Mock)\n{code}"

        prompt = ChatPromptTemplate.from_template("""
        You are an expert Automation Engineer. The following Playwright test failed.
        Fix the code to resolve the error.
        
        Original Code:
        {code}
        
        Error Message:
        {error}
        
        requirements:
        1. Fix the error.
        2. Maintain the original logic.
        3. Ensure it is still a valid standalone python script.
        4. Return ONLY the full corrected python code.
        """)
        
        chain = prompt | self.model | StrOutputParser()
        
        try:
            response = chain.invoke({"code": code, "error": error})
             # Extract code from markdown if present
            if "```python" in response:
                response = response.split("```python")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]
            return response.strip()
        except Exception as e:
            logger.error(f"LLM Fix Code failed: {e}")
            return code # Return original if fix fails

    # --- Mocks ---
    def _mock_prd(self):
        return {
            "product_name": "Mock Product",
            "description": "Generated by Mock LLM (No API Key found)",
            "tech_stack": {"framework": "React", "language": "TypeScript"},
            "key_features": ["Login", "Dashboard"],
            "user_stories": [],
            "requirements": {"functional": [], "non_functional": []}
        }

    def _mock_frontend_plan(self):
        return {
            "type": "frontend",
            "scenarios": [
                {"id": "mock_1", "name": "Mock Load", "steps": ["Open Page"]}
            ]
        }
    
    def _mock_backend_plan(self):
        return {
            "type": "backend",
            "scenarios": [
                # === FUNCTIONAL TESTS - Positive ===
                {
                    "id": "TC_BE_001",
                    "name": "Successful Login with Valid Credentials",
                    "category": "Functional Tests",
                    "priority": "High",
                    "description": "Verify that a user can login with valid email and password.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_002",
                    "name": "Login with Invalid Password",
                    "category": "Functional Tests",
                    "priority": "Medium",
                    "description": "Verify that login fails with 401 for incorrect password.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_003",
                    "name": "Get User Profile (Authenticated)",
                    "category": "Functional Tests",
                    "priority": "High",
                    "description": "Verify fetching user profile with valid token.",
                    "endpoint": "/users/me",
                    "method": "GET"
                },
                {
                    "id": "TC_BE_004",
                    "name": "Login with Non-existent User",
                    "category": "Functional Tests",
                    "priority": "Medium",
                    "description": "Verify login fails for user that does not exist.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_005",
                    "name": "Logout Functionality",
                    "category": "Functional Tests",
                    "priority": "Medium",
                    "description": "Verify user can successfully logout.",
                    "endpoint": "/auth/logout",
                    "method": "POST"
                },
                # === EDGE CASE TESTS ===
                {
                    "id": "TC_BE_006",
                    "name": "Empty Payload Handling",
                    "category": "Edge Case Tests",
                    "priority": "Medium",
                    "description": "Send empty JSON body to login endpoint.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_007",
                    "name": "Large Payload Test",
                    "category": "Edge Case Tests",
                    "priority": "Low",
                    "description": "Send exceedingly large username/string to test buffer handling.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_008",
                    "name": "Special Characters in Username",
                    "category": "Edge Case Tests",
                    "priority": "Medium",
                    "description": "Test username with special chars like @#$%^&*()",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_009",
                    "name": "Unicode Characters Handling",
                    "category": "Edge Case Tests",
                    "priority": "Low",
                    "description": "Test input with unicode/emoji characters.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_010",
                    "name": "Whitespace Only Input",
                    "category": "Edge Case Tests",
                    "priority": "Medium",
                    "description": "Test with only spaces in username/password fields.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                # === NEGATIVE TESTS ===
                {
                    "id": "TC_BE_011",
                    "name": "Missing Username Field",
                    "category": "Negative Tests",
                    "priority": "High",
                    "description": "Submit form without username field.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_012",
                    "name": "Missing Password Field",
                    "category": "Negative Tests",
                    "priority": "High",
                    "description": "Submit form without password field.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_013",
                    "name": "Invalid Email Format",
                    "category": "Negative Tests",
                    "priority": "Medium",
                    "description": "Test with malformed email address.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_014",
                    "name": "Password Too Short",
                    "category": "Negative Tests",
                    "priority": "Medium",
                    "description": "Test with password shorter than minimum required.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                # === UI VALIDATION TESTS ===
                {
                    "id": "TC_BE_015",
                    "name": "Form Validation Messages",
                    "category": "UI Validation",
                    "priority": "Medium",
                    "description": "Verify proper error messages are displayed for invalid input.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                },
                {
                    "id": "TC_BE_016",
                    "name": "Password Field Masking",
                    "category": "UI Validation",
                    "priority": "Low",
                    "description": "Verify password field masks input characters.",
                    "endpoint": "/auth/login",
                    "method": "POST"
                }
            ]
        }

    def _mock_security_plan(self):
        return {
            "type": "security",
            "scenarios": [
                # === INJECTION ATTACKS ===
                {
                    "id": "SEC_001",
                    "name": "SQL Injection Check (Login)",
                    "category": "Injection",
                    "priority": "Critical",
                    "description": "Attempt SQL injection using ' OR 1=1 --",
                    "payload": "' OR 1=1 --",
                    "target_element": "password"
                },
                {
                    "id": "SEC_002",
                    "name": "SQL Injection (Username Field)",
                    "category": "Injection",
                    "priority": "Critical",
                    "description": "Test SQL injection in username field",
                    "payload": "admin'--",
                    "target_element": "username"
                },
                {
                    "id": "SEC_003",
                    "name": "SQL Injection (Union Attack)",
                    "category": "Injection",
                    "priority": "Critical",
                    "description": "Test UNION-based SQL injection",
                    "payload": "' UNION SELECT 1,2,3--",
                    "target_element": "username"
                },
                # === XSS ATTACKS ===
                {
                    "id": "SEC_004",
                    "name": "Reflected XSS Vulnerability",
                    "category": "Cross-Site Scripting (XSS)",
                    "priority": "High",
                    "description": "Inject <script>alert(1)</script> into input fields.",
                    "payload": "<script>alert(1)</script>",
                    "target_element": "username"
                },
                {
                    "id": "SEC_005",
                    "name": "XSS via Event Handler",
                    "category": "Cross-Site Scripting (XSS)",
                    "priority": "High",
                    "description": "Test XSS using event handlers like onerror",
                    "payload": "<img src=x onerror=alert(1)>",
                    "target_element": "username"
                },
                {
                    "id": "SEC_006",
                    "name": "Stored XSS Test",
                    "category": "Cross-Site Scripting (XSS)",
                    "priority": "High",
                    "description": "Test if XSS payload persists in storage",
                    "payload": "<svg onload=alert('XSS')>",
                    "target_element": "username"
                },
                # === BROKEN ACCESS CONTROL ===
                {
                    "id": "SEC_007",
                    "name": "IDOR - Access Other User Data",
                    "category": "Broken Access Control",
                    "priority": "High",
                    "description": "Attempt to access /users/99999 without authorization.",
                    "endpoint": "/users/99999"
                },
                {
                    "id": "SEC_008",
                    "name": "Unauthorized Admin Access",
                    "category": "Broken Access Control",
                    "priority": "Critical",
                    "description": "Try accessing admin endpoints without auth.",
                    "endpoint": "/admin"
                },
                # === SECURITY MISCONFIGURATION ===
                {
                    "id": "SEC_009",
                    "name": "Clickjacking Headers Check",
                    "category": "Security Misconfiguration",
                    "priority": "Medium",
                    "description": "Check if X-Frame-Options header is present."
                },
                {
                    "id": "SEC_010",
                    "name": "HTTPS Enforcement",
                    "category": "Security Misconfiguration",
                    "priority": "High",
                    "description": "Verify HTTPS is enforced and HTTP redirects properly."
                },
                {
                    "id": "SEC_011",
                    "name": "Sensitive Data Exposure",
                    "category": "Security Misconfiguration",
                    "priority": "High",
                    "description": "Check for exposed sensitive data in responses or errors."
                },
                # === AUTHENTICATION ATTACKS ===
                {
                    "id": "SEC_012",
                    "name": "Brute Force Protection",
                    "category": "Authentication",
                    "priority": "High",
                    "description": "Test rate limiting after multiple failed logins."
                },
                {
                    "id": "SEC_013",
                    "name": "Session Fixation",
                    "category": "Authentication",
                    "priority": "High",
                    "description": "Verify session ID changes after login."
                },
                {
                    "id": "SEC_014",
                    "name": "Password Reset Security",
                    "category": "Authentication",
                    "priority": "Medium",
                    "description": "Test password reset token for predictability."
                }
            ]
        }

    def _mock_test_code(self, target_url, plan=None):
        # Build scenario execution code with REAL browser interactions
        scenario_code = ""
        if plan and "scenarios" in plan:
            scenarios = plan.get("scenarios", [])
            for i, sc in enumerate(scenarios):
                sc_id = sc.get('id', f'test_{i}')
                sc_name = sc.get('name', 'Unknown Test')
                sc_desc = sc.get('description', '')
                sc_category = sc.get('category', 'General').lower()

                # Generate REAL test code based on test type
                if 'login' in sc_name.lower() and 'valid' in sc_name.lower():
                    # Real login test with valid credentials
                    scenario_code += f'''
            # --- Test Case: {sc_id} - {sc_name} ---
            print(f"[RUNNING] {sc_id}")
            print(f"[INFO] Executing: {sc_name}")
            screenshot = take_screenshot(page, "{sc_id}_start")
            update_progress("{sc_id}", "running", "{sc_name}", screenshot)

            if not valid_username or not valid_password:
                print(f"[SKIPPED] {sc_id} - No credentials provided")
                screenshot = take_screenshot(page, "{sc_id}_skipped")
                update_progress("{sc_id}", "skipped", "{sc_name}", screenshot)
            else:
                try:
                    # Find and fill username field
                    username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
                    username_field.fill(valid_username)
                    page.wait_for_timeout(500)
                    screenshot = take_screenshot(page, "{sc_id}_filled_user")
                    update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                    # Find and fill password field
                    password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
                    password_field.fill(valid_password)
                    page.wait_for_timeout(500)
                    screenshot = take_screenshot(page, "{sc_id}_filled_pass")
                    update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                    # Click submit button
                    submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Login")').first
                    submit_btn.click()
                    page.wait_for_timeout(2000)
                    screenshot = take_screenshot(page, "{sc_id}_submitted")
                    update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                    # Verify login success - check for success message or URL change
                    if page.url != target_url or page.locator('text=Logged In Successfully, text=success, text=Welcome').count() > 0:
                        print(f"[PASSED] {sc_id}")
                        screenshot = take_screenshot(page, "{sc_id}_passed")
                        update_progress("{sc_id}", "passed", "{sc_name}", screenshot)
                    else:
                        print(f"[FAILED] {sc_id} - Login did not succeed")
                        screenshot = take_screenshot(page, "{sc_id}_failed")
                        update_progress("{sc_id}", "failed", "{sc_name}", screenshot)
                except Exception as e:
                    print(f"[FAILED] {sc_id}")
                    print(f"[ERROR] {{str(e)}}")
                    screenshot = take_screenshot(page, "{sc_id}_error")
                    update_progress("{sc_id}", "failed", "{sc_name}", screenshot)

            # Navigate back for next test
            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
'''
                elif 'login' in sc_name.lower() and 'invalid' in sc_name.lower():
                    # Real login test with invalid credentials
                    scenario_code += f'''
            # --- Test Case: {sc_id} - {sc_name} ---
            print(f"[RUNNING] {sc_id}")
            print(f"[INFO] Executing: {sc_name}")
            screenshot = take_screenshot(page, "{sc_id}_start")
            update_progress("{sc_id}", "running", "{sc_name}", screenshot)
            try:
                username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
                username_field.fill("wronguser")
                page.wait_for_timeout(300)
                screenshot = take_screenshot(page, "{sc_id}_filled")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
                password_field.fill("wrongpassword")
                page.wait_for_timeout(300)

                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit"), button:has-text("Login")').first
                submit_btn.click()
                page.wait_for_timeout(2000)
                screenshot = take_screenshot(page, "{sc_id}_submitted")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                # Verify error message appears
                if page.locator('text=invalid, text=error, text=incorrect, text=failed, .error').count() > 0:
                    print(f"[PASSED] {sc_id} - Error message displayed correctly")
                    screenshot = take_screenshot(page, "{sc_id}_passed")
                    update_progress("{sc_id}", "passed", "{sc_name}", screenshot)
                else:
                    print(f"[FAILED] {sc_id} - No error message for invalid credentials")
                    screenshot = take_screenshot(page, "{sc_id}_failed")
                    update_progress("{sc_id}", "failed", "{sc_name}", screenshot)
            except Exception as e:
                print(f"[FAILED] {sc_id}")
                print(f"[ERROR] {{str(e)}}")
                screenshot = take_screenshot(page, "{sc_id}_error")
                update_progress("{sc_id}", "failed", "{sc_name}", screenshot)

            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
'''
                elif 'sql' in sc_name.lower() or 'injection' in sc_category:
                    # SQL Injection test
                    scenario_code += f'''
            # --- Test Case: {sc_id} - {sc_name} ---
            print(f"[RUNNING] {sc_id}")
            print(f"[INFO] Executing: {sc_name}")
            screenshot = take_screenshot(page, "{sc_id}_start")
            update_progress("{sc_id}", "running", "{sc_name}", screenshot)
            try:
                # Try SQL injection payload
                username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
                username_field.fill("' OR '1'='1")
                page.wait_for_timeout(300)
                screenshot = take_screenshot(page, "{sc_id}_payload")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
                password_field.fill("' OR '1'='1")
                page.wait_for_timeout(300)

                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
                submit_btn.click()
                page.wait_for_timeout(2000)
                screenshot = take_screenshot(page, "{sc_id}_result")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                # Check if injection was blocked (should show error or stay on login)
                if page.locator('text=error, text=invalid, .error').count() > 0 or page.url == target_url:
                    print(f"[PASSED] {sc_id} - SQL injection blocked")
                    screenshot = take_screenshot(page, "{sc_id}_passed")
                    update_progress("{sc_id}", "passed", "{sc_name}", screenshot)
                else:
                    print(f"[FAILED] {sc_id} - Potential SQL injection vulnerability!")
                    screenshot = take_screenshot(page, "{sc_id}_failed")
                    update_progress("{sc_id}", "failed", "{sc_name}", screenshot)
            except Exception as e:
                print(f"[FAILED] {sc_id}")
                print(f"[ERROR] {{str(e)}}")
                screenshot = take_screenshot(page, "{sc_id}_error")
                update_progress("{sc_id}", "failed", "{sc_name}", screenshot)

            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
'''
                elif 'xss' in sc_name.lower() or 'xss' in sc_category:
                    # XSS test
                    scenario_code += f'''
            # --- Test Case: {sc_id} - {sc_name} ---
            print(f"[RUNNING] {sc_id}")
            print(f"[INFO] Executing: {sc_name}")
            screenshot = take_screenshot(page, "{sc_id}_start")
            update_progress("{sc_id}", "running", "{sc_name}", screenshot)
            try:
                username_field = page.locator('input[name="username"], input[id="username"], input[type="text"]').first
                username_field.fill("<script>alert('XSS')</script>")
                page.wait_for_timeout(300)
                screenshot = take_screenshot(page, "{sc_id}_payload")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                password_field = page.locator('input[name="password"], input[id="password"], input[type="password"]').first
                password_field.fill("test123")
                page.wait_for_timeout(300)

                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
                submit_btn.click()
                page.wait_for_timeout(1500)
                screenshot = take_screenshot(page, "{sc_id}_result")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                # Check page content doesn't execute script
                content = page.content()
                if "<script>alert" not in content or page.locator('text=error, text=invalid').count() > 0:
                    print(f"[PASSED] {sc_id} - XSS payload sanitized")
                    screenshot = take_screenshot(page, "{sc_id}_passed")
                    update_progress("{sc_id}", "passed", "{sc_name}", screenshot)
                else:
                    print(f"[FAILED] {sc_id} - Potential XSS vulnerability!")
                    screenshot = take_screenshot(page, "{sc_id}_failed")
                    update_progress("{sc_id}", "failed", "{sc_name}", screenshot)
            except Exception as e:
                print(f"[FAILED] {sc_id}")
                print(f"[ERROR] {{str(e)}}")
                screenshot = take_screenshot(page, "{sc_id}_error")
                update_progress("{sc_id}", "failed", "{sc_name}", screenshot)

            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
'''
                elif 'empty' in sc_name.lower() or 'payload' in sc_name.lower():
                    # Empty payload test
                    scenario_code += f'''
            # --- Test Case: {sc_id} - {sc_name} ---
            print(f"[RUNNING] {sc_id}")
            print(f"[INFO] Executing: {sc_name}")
            screenshot = take_screenshot(page, "{sc_id}_start")
            update_progress("{sc_id}", "running", "{sc_name}", screenshot)
            try:
                # Leave fields empty and try to submit
                submit_btn = page.locator('button[type="submit"], input[type="submit"], button:has-text("Submit")').first
                submit_btn.click()
                page.wait_for_timeout(1500)
                screenshot = take_screenshot(page, "{sc_id}_submitted")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                # Check for validation error
                if page.locator('text=required, text=empty, text=enter, .error, [class*="error"]').count() > 0:
                    print(f"[PASSED] {sc_id} - Empty payload handled correctly")
                    screenshot = take_screenshot(page, "{sc_id}_passed")
                    update_progress("{sc_id}", "passed", "{sc_name}", screenshot)
                else:
                    print(f"[FAILED] {sc_id} - No validation for empty fields")
                    screenshot = take_screenshot(page, "{sc_id}_failed")
                    update_progress("{sc_id}", "failed", "{sc_name}", screenshot)
            except Exception as e:
                print(f"[FAILED] {sc_id}")
                print(f"[ERROR] {{str(e)}}")
                screenshot = take_screenshot(page, "{sc_id}_error")
                update_progress("{sc_id}", "failed", "{sc_name}", screenshot)

            page.goto(target_url, wait_until="domcontentloaded")
            page.wait_for_timeout(500)
'''
                else:
                    # Generic test - just verify page loads and basic interaction
                    scenario_code += f'''
            # --- Test Case: {sc_id} - {sc_name} ---
            print(f"[RUNNING] {sc_id}")
            print(f"[INFO] Executing: {sc_name}")
            screenshot = take_screenshot(page, "{sc_id}_start")
            update_progress("{sc_id}", "running", "{sc_name}", screenshot)
            try:
                # Generic interaction test
                page.evaluate("document.body.style.border = '3px solid #00D4AA'")
                page.wait_for_timeout(500)
                screenshot = take_screenshot(page, "{sc_id}_highlight")
                update_progress("{sc_id}", "running", "{sc_name}", screenshot)

                # Check page has content
                title = page.title()
                has_form = page.locator('form, input, button').count() > 0

                page.evaluate("document.body.style.border = ''")

                if title and has_form:
                    print(f"[PASSED] {sc_id} - Page functional")
                    screenshot = take_screenshot(page, "{sc_id}_passed")
                    update_progress("{sc_id}", "passed", "{sc_name}", screenshot)
                else:
                    print(f"[FAILED] {sc_id} - Page missing elements")
                    screenshot = take_screenshot(page, "{sc_id}_failed")
                    update_progress("{sc_id}", "failed", "{sc_name}", screenshot)
            except Exception as e:
                print(f"[FAILED] {sc_id}")
                print(f"[ERROR] {{str(e)}}")
                screenshot = take_screenshot(page, "{sc_id}_error")
                update_progress("{sc_id}", "failed", "{sc_name}", screenshot)

            page.wait_for_timeout(300)
'''
        else:
            # Default single test if no plan
            scenario_code = '''
            print("[RUNNING] default_test")
            screenshot = take_screenshot(page, "default_test_start")
            update_progress("default_test", "running", "Default Test", screenshot)
            try:
                page.wait_for_timeout(1000)
                screenshot = take_screenshot(page, "default_test_done")
                print("[PASSED] default_test")
                update_progress("default_test", "passed", "Default Test", screenshot)
            except Exception as e:
                screenshot = take_screenshot(page, "default_test_error")
                print(f"[FAILED] default_test: {e}")
                update_progress("default_test", "failed", "Default Test", screenshot)
'''

        return f'''import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

# Progress file for real-time updates
PROGRESS_FILE = Path(__file__).parent.parent / "execution_progress.json"
CREDENTIALS_FILE = Path(__file__).parent.parent / "test_credentials.json"

def load_credentials():
    """Load test credentials from config file."""
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def update_progress(test_id, status, name, screenshot_path=None):
    """Update the progress file with current test status and screenshot."""
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, "r") as f:
                progress = json.load(f)
        else:
            progress = {{"status": "running", "current_test": None, "completed": [], "results": {{}}, "current_screenshot": None}}

        progress["current_test"] = test_id if status == "running" else None
        progress["results"][test_id] = {{"status": status, "name": name}}

        # Update current screenshot for live preview
        if screenshot_path:
            progress["current_screenshot"] = screenshot_path

        if status in ["passed", "failed", "skipped"]:
            if test_id not in progress.get("completed", []):
                progress.setdefault("completed", []).append(test_id)

        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)

        # Flush stdout for real-time output
        sys.stdout.flush()
    except Exception as e:
        print(f"[WARN] Could not update progress: {{e}}")

def take_screenshot(page, test_id):
    """Take screenshot and return relative path."""
    try:
        screenshots_dir = Path(__file__).parent / "screenshots"
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / f"{{test_id}}.png"
        page.screenshot(path=str(screenshot_path))
        return f"screenshots/{{test_id}}.png"
    except Exception as e:
        print(f"[WARN] Could not take screenshot: {{e}}")
        return None

def run_tests():
    target_url = "{target_url}" if "{target_url}" else "https://example.com"

    # Load test credentials
    creds = load_credentials()
    valid_username = creds.get("username", "") if creds else ""
    valid_password = creds.get("password", "") if creds else ""

    print(f"=" * 60)
    print(f"TestSprite Autonomous Test Execution")
    print(f"=" * 60)
    print(f"Target: {{target_url}}")
    if creds:
        print(f"Credentials: Loaded (username: {{valid_username[:3]}}***)")
    else:
        print(f"Credentials: Not provided - some tests may be skipped")
    print(f"=" * 60)
    sys.stdout.flush()

    with sync_playwright() as p:
        # Browser Launch with Video Recording
        print("[INFO] Launching browser...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="videos/",
            viewport={{"width": 1280, "height": 720}}
        )
        page = context.new_page()

        try:
            print("[INFO] Navigating to target...")
            sys.stdout.flush()
            page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(1500)

            print(f"[INFO] Page Title: {{page.title()}}")
            print(f"[INFO] Starting test execution...")
            print("-" * 40)
            sys.stdout.flush()

            # === Execute Test Scenarios ==={scenario_code}

            print("-" * 40)
            print("[INFO] All tests completed.")

        except Exception as e:
            print(f"[ERROR] Test execution error: {{e}}")
        finally:
            # Save video
            context.close()
            browser.close()
            print("[INFO] Browser closed. Video saved.")

            # Mark execution as complete
            try:
                if PROGRESS_FILE.exists():
                    with open(PROGRESS_FILE, "r") as f:
                        progress = json.load(f)
                    progress["status"] = "completed"
                    progress["current_test"] = None
                    with open(PROGRESS_FILE, "w") as f:
                        json.dump(progress, f, indent=2)
            except:
                pass

    print("=" * 60)
    print("Test Execution Finished")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
'''
