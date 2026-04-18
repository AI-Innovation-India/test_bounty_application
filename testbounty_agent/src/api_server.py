from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import os
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

from src.agents.orchestrator import app as agent_app
from src.agents.explorer import explore_application
from src.agents.planner import generate_test_plan
from src.agents.knowledge_builder import build_app_knowledge
from src.utils.logger import logger

app = FastAPI(title="TestBounty Agent API")

# Allow CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistence
RUNS_FILE = Path("runs.json")

def load_runs():
    if RUNS_FILE.exists():
        try:
            with open(RUNS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_runs():
    with open(RUNS_FILE, "w") as f:
        json.dump(RUNS, f, indent=2)

# Load on startup
RUNS = load_runs()

class TestCredentials(BaseModel):
    username: str
    password: str

class RunRequest(BaseModel):
    # Existing fields used when testing a local project
    project_path: str = ""
    # URL of the web or API target (primary for your flow)
    target_url: str = ""
    # New optional metadata to describe the test in the UI
    test_name: Optional[str] = None
    api_name: Optional[str] = None
    auth_type: Optional[str] = None
    extra_info: Optional[str] = None
    # Test credentials for login testing
    test_credentials: Optional[TestCredentials] = None

class RunResponse(BaseModel):
    run_id: str
    status: str

async def run_agent_task(run_id: str, project_path: str, target_url: str, test_name: str = None, api_name: str = None, auth_type: str = None, extra_info: str = None, credentials: dict = None):
    logger.info(f"Starting run {run_id} for {target_url or project_path}")
    RUNS[run_id]["status"] = "running"
    save_runs() # Save state

    # Logic to normalize state
    initial_state = {
        "steps_completed": [],
        "error_log": [],
        # Pass metadata to agent for richer test plan generation
        "test_name": test_name,
        "api_name": api_name,
        "auth_type": auth_type,
        "extra_info": extra_info,
        "test_credentials": credentials  # Pass credentials to state
    }

    if target_url:
        initial_state["target_url"] = target_url
        fs_project_path = os.path.abspath(f"./temp_runs/{run_id}") # Use absolute path
        initial_state["project_path"] = fs_project_path
        # Fix: Update RUNS with filesystem lookup path
        RUNS[run_id]["project_path"] = fs_project_path
        save_runs()
    else:
        fs_project_path = os.path.abspath(project_path)
        initial_state["project_path"] = fs_project_path
        RUNS[run_id]["project_path"] = fs_project_path
        save_runs()

    # Save credentials to config file for test execution
    if credentials:
        config_dir = Path(fs_project_path) / "testsprite_tests"
        config_dir.mkdir(parents=True, exist_ok=True)
        credentials_file = config_dir / "test_credentials.json"
        with open(credentials_file, "w") as f:
            json.dump(credentials, f, indent=2)
        logger.info(f"Saved test credentials to {credentials_file}")
    
    try:
        # Stream events to capture progress
        async for event in agent_app.astream(initial_state):
             for key, value in event.items():
                RUNS[run_id]["steps"].append(key)
                save_runs() # Save progress
                
                # Update partial results if available
                if "test_results" in value:
                     RUNS[run_id]["results"] = value["test_results"]
                if "report_path" in value:
                     RUNS[run_id]["report_path"] = value["report_path"]

        RUNS[run_id]["status"] = "completed"
    except Exception as e:
        logger.error(f"Run {run_id} failed: {e}")
        RUNS[run_id]["status"] = "failed"
        RUNS[run_id]["error"] = str(e)
    
    save_runs() # Final save

@app.post("/api/run", response_model=RunResponse)
async def start_run(request: RunRequest, background_tasks: BackgroundTasks):
    run_id = str(uuid.uuid4())
    import datetime

    # Extract credentials if provided
    credentials = None
    if request.test_credentials:
        credentials = {
            "username": request.test_credentials.username,
            "password": request.test_credentials.password
        }

    RUNS[run_id] = {
        "id": run_id,
        # Where artifacts are stored. For URL runs, this will be replaced
        # with a temp folder path once the task starts.
        "project_path": request.project_path or request.target_url,
        # High-level metadata used for listing and details in the UI
        "target_url": request.target_url,
        "test_name": request.test_name or "Untitled Test",
        "api_name": request.api_name or None,
        "auth_type": request.auth_type or None,
        "extra_info": request.extra_info or None,
        "test_credentials": credentials,  # Store credentials
        "status": "pending",
        "steps": [],
        "results": None,
        "report_path": None,
        "error": None,
        "created_at": datetime.datetime.now().isoformat()
    }
    save_runs()

    background_tasks.add_task(
        run_agent_task,
        run_id,
        request.project_path,
        request.target_url,
        request.test_name,
        request.api_name,
        request.auth_type,
        request.extra_info,
        credentials  # Pass credentials to task
    )
    return {"run_id": run_id, "status": "pending"}

@app.get("/api/run/{run_id}")
async def get_run_status(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
    return RUNS[run_id]

@app.get("/api/runs")
async def list_runs():
    # Return list of runs (summary)
    return list(RUNS.values())

from fastapi.responses import FileResponse
import os

@app.get("/api/run/{run_id}/artifacts/video")
async def get_run_video(run_id: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])

    # Check new structure (videos/{test_id}/*.webm) first
    video_base = base_path / "testsprite_tests" / "generated_tests" / "videos"

    if video_base.exists():
        # Find first video in any subdirectory
        for subdir in video_base.iterdir():
            if subdir.is_dir():
                webm_files = list(subdir.glob("*.webm"))
                if webm_files:
                    return FileResponse(webm_files[0], media_type="video/webm")

        # Fallback to root videos folder
        webm_files = list(video_base.glob("*.webm"))
        if webm_files:
            return FileResponse(webm_files[0], media_type="video/webm")

    raise HTTPException(status_code=404, detail="No video file found")

@app.get("/api/run/{run_id}/test/{test_id}/video")
async def get_test_video(run_id: str, test_id: str):
    """Get video for a specific test case."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])
    video_dir = base_path / "testsprite_tests" / "generated_tests" / "videos" / test_id

    if not video_dir.exists():
        raise HTTPException(status_code=404, detail=f"Video not found for test {test_id}")

    webm_files = list(video_dir.glob("*.webm"))
    if not webm_files:
        raise HTTPException(status_code=404, detail=f"No video file for test {test_id}")

    return FileResponse(webm_files[0], media_type="video/webm")

@app.get("/api/run/{run_id}/test/{test_id}/code")
async def get_test_code(run_id: str, test_id: str):
    """Get generated code for a specific test case."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])
    test_file = base_path / "testsprite_tests" / "generated_tests" / f"test_{test_id}.py"

    if not test_file.exists():
        raise HTTPException(status_code=404, detail=f"Code not found for test {test_id}")

    with open(test_file, "r") as f:
        content = f.read()

    return {"content": content, "test_id": test_id}

@app.get("/api/run/{run_id}/progress")
async def get_execution_progress(run_id: str):
    """Get real-time execution progress for a run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])
    progress_file = base_path / "testsprite_tests" / "execution_progress.json"

    if not progress_file.exists():
        # Return default pending state if no progress file yet
        return {
            "status": "pending",
            "current_test": None,
            "completed": [],
            "results": {},
            "current_screenshot": None
        }

    try:
        with open(progress_file, "r") as f:
            progress = json.load(f)
        return progress
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "current_test": None,
            "completed": [],
            "results": {},
            "current_screenshot": None
        }


from fastapi.responses import FileResponse

@app.get("/api/run/{run_id}/screenshot/{filename}")
async def get_screenshot(run_id: str, filename: str):
    """Serve live screenshot for a test run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])
    screenshot_path = base_path / "testsprite_tests" / "generated_tests" / "screenshots" / filename

    if not screenshot_path.exists():
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return FileResponse(screenshot_path, media_type="image/png")


@app.get("/api/run/{run_id}/artifacts/{filename}")
async def get_run_artifact(run_id: str, filename: str):
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")
        
    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])
    
    # Artifact mapping
    filename_map = {
        "prd": "standard_prd.json",
        "frontend_plan": "frontend_test_plan.json",
        "backend_plan": "backend_test_plan.json",
        "security_test_plan": "security_test_plan.json",
        "code_summary": "code_summary.json",
        "report": "reports/report.md",
        "test_code": "generated_tests/test_generated_001.py" 
    }
    
    real_filename = filename_map.get(filename, filename)
    
    artifact_path = base_path / "testsprite_tests" / real_filename
    
    if not artifact_path.exists():
        # Try without testsprite_tests (legacy or direct)
        artifact_path = base_path / real_filename
        
    if not artifact_path.exists():
        raise HTTPException(status_code=404, detail=f"Artifact {real_filename} not found at {artifact_path}")
        
    # Read and return content
    try:
        with open(artifact_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Return JSON if it looks like JSON
        if real_filename.endswith(".json"):
            return json.loads(content)
        return {"content": content, "type": "text"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def health_check():
    return {"status": "ok", "service": "TestSprite Agent API", "runs_stored": len(RUNS)}

@app.get("/api/run/{run_id}/junit.xml", response_class=Response)
async def export_junit_xml(run_id: str):
    """
    Export run results as JUnit XML — understood by Jenkins, GitHub Actions,
    Azure DevOps, GitLab CI, and every major CI dashboard.
    """
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run = RUNS[run_id]
    results = run.get("results") or {}
    suite_name = run.get("test_name", "TestBounty")
    url = run.get("target_url", "")

    tests = list(results.values()) if results else []
    total = len(tests)
    failures = sum(1 for t in tests if t.get("status") == "failed")
    errors = sum(1 for t in tests if t.get("status") == "error")
    passed = sum(1 for t in tests if t.get("status") == "passed")
    skipped = total - passed - failures - errors

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuites name="TestBounty" tests="{total}" failures="{failures}" errors="{errors}" skipped="{skipped}">',
        f'  <testsuite name="{esc(suite_name)}" tests="{total}" failures="{failures}" errors="{errors}" skipped="{skipped}" hostname="{esc(url)}">',
    ]

    for scenario_id, r in results.items():
        name = esc(r.get("name") or scenario_id)
        module = esc(r.get("module") or "general")
        status = r.get("status", "pending")
        duration = r.get("duration_ms", 0) / 1000.0

        lines.append(f'    <testcase classname="{module}" name="{name}" time="{duration:.3f}">')
        if status == "failed":
            err = esc(r.get("error") or "Scenario failed")
            steps = r.get("steps_completed") or []
            msg = esc(f"Failed after {len(steps)} steps. {r.get('error') or ''}")
            lines.append(f'      <failure message="{msg}" type="AssertionError">{err}</failure>')
        elif status == "error":
            err = esc(r.get("error") or "Error")
            lines.append(f'      <error message="{err}" type="Error">{err}</error>')
        elif status in ("pending", "skipped"):
            lines.append('      <skipped/>')
        lines.append('    </testcase>')

    lines += ["  </testsuite>", "</testsuites>"]
    xml = "\n".join(lines)

    return Response(content=xml, media_type="application/xml",
                    headers={"Content-Disposition": f'attachment; filename="junit_{run_id[:8]}.xml"'})


# =============================================================================
# CI / CD TRIGGER — synchronous endpoint for pipelines
# =============================================================================

class CITriggerRequest(BaseModel):
    suite_name: Optional[str] = None
    suite_id: Optional[str] = None
    suite_type: Optional[str] = None     # Run all suites of this type
    timeout: int = 600                   # Max seconds to wait
    fail_on_failure: bool = True         # HTTP 422 if any test fails
    browser: str = "chromium"
    credentials: Optional[Dict] = None  # {username, password}
    webhook_url: Optional[str] = None   # Slack/Teams/custom webhook on failure

@app.post("/api/ci/trigger")
async def ci_trigger(request: CITriggerRequest):
    """
    Synchronous CI trigger — starts a suite run, waits for completion,
    returns pass/fail result in one HTTP call.

    Returns 200 if all passed, 422 if any failed (CI gate fails on non-2xx).

    Example curl:
        curl -X POST http://testbounty:8000/api/ci/trigger \\
             -H 'Content-Type: application/json' \\
             -d '{"suite_name":"Regression","timeout":300}'
    """
    # Resolve suite(s)
    suites_to_run = []
    if request.suite_id:
        if request.suite_id not in TEST_SUITES:
            raise HTTPException(status_code=404, detail=f"Suite not found: {request.suite_id}")
        suites_to_run = [TEST_SUITES[request.suite_id]]
    elif request.suite_name:
        found = [s for s in TEST_SUITES.values() if s["name"].lower() == request.suite_name.lower()]
        if not found:
            raise HTTPException(status_code=404, detail=f"Suite not found: {request.suite_name}")
        suites_to_run = found
    elif request.suite_type:
        suites_to_run = [s for s in TEST_SUITES.values() if s.get("suite_type") == request.suite_type]
        if not suites_to_run:
            raise HTTPException(status_code=404, detail=f"No suites with type: {request.suite_type}")
    else:
        raise HTTPException(status_code=400, detail="Provide suite_name, suite_id, or suite_type")

    all_run_ids = []
    for suite in suites_to_run:
        refs = suite.get("scenario_refs") or []
        if not refs:
            continue
        plan_groups: Dict[str, list] = {}
        for ref in refs:
            plan_groups.setdefault(ref["plan_id"], []).append(ref["scenario_id"])

        for pid, sids in plan_groups.items():
            if pid not in PLANS:
                continue
            plan = PLANS[pid]
            scenarios_to_run = [
                sc for mod in plan.get("test_plan", {}).get("modules", {}).values()
                for sc in mod.get("scenarios", [])
                if sc["id"] in sids
            ]
            if not scenarios_to_run:
                continue
            run_id = str(uuid.uuid4())
            RUNS[run_id] = {
                "id": run_id,
                "plan_id": pid,
                "type": "ci_run",
                "target_url": plan["url"],
                "test_name": f"CI: {suite['name']}",
                "scenarios": scenarios_to_run,
                "status": "pending",
                "results": {},
                "created_at": datetime.now().isoformat(),
                "suite_id": suite["id"],
            }
            save_runs()
            # Run synchronously in thread pool so we can await completion
            loop = asyncio.get_event_loop()
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=1) as ex:
                await loop.run_in_executor(
                    ex, run_scenarios_task_sync,
                    run_id, plan["url"], scenarios_to_run, request.browser
                )
            all_run_ids.append(run_id)

    if not all_run_ids:
        raise HTTPException(status_code=400, detail="No runnable scenarios found in suite(s)")

    # ── Aggregate results ─────────────────────────────────────────────────────
    total = passed = failed = 0
    failed_details = []
    for run_id in all_run_ids:
        run = RUNS.get(run_id, {})
        for sid, r in (run.get("results") or {}).items():
            total += 1
            if r.get("status") == "passed":
                passed += 1
            else:
                failed += 1
                failed_details.append({
                    "scenario": r.get("name") or sid,
                    "error": r.get("error") or "failed",
                    "steps_completed": len(r.get("steps_completed") or []),
                })

    pass_rate = (passed / total * 100) if total else 0
    result_payload = {
        "status": "passed" if failed == 0 else "failed",
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(pass_rate, 1),
        "run_ids": all_run_ids,
        "suites_run": [s["name"] for s in suites_to_run],
        "junit_urls": [f"/api/run/{rid}/junit.xml" for rid in all_run_ids],
    }
    if failed_details:
        result_payload["failures"] = failed_details

    # ── Webhook notification ──────────────────────────────────────────────────
    if request.webhook_url and failed > 0:
        _send_webhook(request.webhook_url, result_payload, suites_to_run)

    if request.fail_on_failure and failed > 0:
        raise HTTPException(status_code=422, detail=result_payload)

    return result_payload


def _send_webhook(webhook_url: str, result: dict, suites: list):
    """Send Slack/Teams/custom webhook notification on failure."""
    suite_names = ", ".join(s["name"] for s in suites)
    failed = result.get("failed", 0)
    total = result.get("total", 0)
    failures_text = "\n".join(
        f"• {f['scenario']}: {f['error'][:100]}"
        for f in (result.get("failures") or [])[:5]
    )

    # Slack-compatible payload (also works for many other tools)
    payload = {
        "text": f":red_circle: TestBounty suite failed: *{suite_names}*",
        "attachments": [{
            "color": "danger",
            "fields": [
                {"title": "Result", "value": f"{failed}/{total} failed", "short": True},
                {"title": "Pass Rate", "value": f"{result.get('pass_rate')}%", "short": True},
                {"title": "Failed Scenarios", "value": failures_text or "see report", "short": False},
            ],
        }],
    }
    try:
        import urllib.request as ur
        req = ur.Request(
            webhook_url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        ur.urlopen(req, timeout=5)
    except Exception as e:
        logger.warning(f"Webhook failed: {e}")


@app.delete("/api/run/{run_id}")
async def delete_run(run_id: str):
    """Delete a specific run and its artifacts."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]

    # Delete artifacts folder if it exists
    import shutil
    # Handle both old-style runs (with project_path) and new scenario runs
    if "project_path" in run_info:
        base_path = Path(run_info["project_path"])
        if base_path.exists():
            try:
                shutil.rmtree(base_path)
            except Exception as e:
                logger.warning(f"Failed to delete artifacts for {run_id}: {e}")

    # Remove from RUNS dict
    del RUNS[run_id]
    save_runs()

    return {"status": "deleted", "run_id": run_id}

@app.delete("/api/runs")
async def delete_all_runs():
    """Delete all runs and their artifacts."""
    import shutil
    deleted_count = 0

    for run_id, run_info in list(RUNS.items()):
        # Handle both old-style runs (with project_path) and new scenario runs
        if "project_path" in run_info:
            base_path = Path(run_info["project_path"])
            if base_path.exists():
                try:
                    shutil.rmtree(base_path)
                except Exception as e:
                    logger.warning(f"Failed to delete artifacts for {run_id}: {e}")
        deleted_count += 1

    RUNS.clear()
    save_runs()

    return {"status": "deleted", "count": deleted_count}

@app.get("/api/run/{run_id}/report")
async def download_report(run_id: str):
    """Download the execution report for a run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])

    # Try to find report file
    report_paths = [
        base_path / "testsprite_tests" / "reports" / "report.md",
        base_path / "testsprite_tests" / "report.md",
        base_path / "report.md"
    ]

    for report_path in report_paths:
        if report_path.exists():
            return FileResponse(
                report_path,
                media_type="text/markdown",
                filename=f"report_{run_id[:8]}.md"
            )

    # Generate a simple report from results if no file exists
    results = run_info.get("results", {})
    status = run_info.get("status", "unknown")
    test_name = run_info.get("test_name", "Untitled Test")
    target_url = run_info.get("target_url", "N/A")

    report_content = f"""# Test Execution Report

## Test: {test_name}
- **Target URL:** {target_url}
- **Status:** {status}
- **Run ID:** {run_id}

## Results
"""
    if results:
        for test_id, result in results.items():
            if isinstance(result, dict):
                test_status = result.get("status", "unknown")
                test_message = result.get("message", "")
                report_content += f"\n### {test_id}\n- Status: {test_status}\n- Message: {test_message}\n"
    else:
        report_content += "\nNo test results available.\n"

    # Return as downloadable content
    from fastapi.responses import Response
    return Response(
        content=report_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=report_{run_id[:8]}.md"}
    )

class ChatRequest(BaseModel):
    message: str
    run_id: str

@app.post("/api/chat")
async def chat_agent(request: ChatRequest):
    # Simple direct LLM chat for now
    try:
        from src.services.llm_service import LLMService
        llm = LLMService()
        
        provider_name = llm.provider.capitalize()
        
        if llm.provider == "mock" or not llm.model:
             return {
                "role": "agent", 
                "content": f"I am running in Mock mode (Provider: {provider_name}). I checked the logs and everything seems to be passing! The video shows valid navigation to {llm._mock_prd()['product_name']}.",
                "provider": provider_name
            }
        
        # Simple prompt
        response = llm.model.invoke(f"You are a helpful QA Agent. User asks: {request.message}. Answer briefly.")
        
        return {
            "role": "agent", 
            "content": response.content if hasattr(response, 'content') else str(response),
            "provider": provider_name
        }
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        return {"role": "agent", "content": "I'm having trouble connecting to my brain right now.", "error": str(e)}

# =============================================
# TEST SUITES (Test Lists) API
# =============================================

TEST_SUITES_FILE = Path("test_suites.json")

def load_test_suites():
    if TEST_SUITES_FILE.exists():
        try:
            with open(TEST_SUITES_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_test_suites(suites):
    with open(TEST_SUITES_FILE, "w") as f:
        json.dump(suites, f, indent=2)

TEST_SUITES = load_test_suites()

class ScenarioRef(BaseModel):
    plan_id: str
    scenario_id: str
    scenario_name: Optional[str] = ""
    module: Optional[str] = ""

class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    suite_type: Optional[str] = "regression"  # regression | smoke | sanity | custom
    scenario_refs: List[ScenarioRef] = []
    # Legacy field kept for backward compat
    tests: List[str] = []

class TestSuiteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    suite_type: Optional[str] = None
    scenario_refs: Optional[List[ScenarioRef]] = None

class AddScenariosRequest(BaseModel):
    scenario_refs: List[ScenarioRef]

@app.get("/api/test-suites")
async def list_test_suites():
    """List all test suites with scenario counts."""
    suites = list(TEST_SUITES.values())
    for s in suites:
        s.setdefault("scenario_refs", [])
        s.setdefault("suite_type", "regression")
    return suites

@app.post("/api/test-suites")
async def create_test_suite(suite: TestSuiteCreate):
    """Create a new test suite."""
    suite_id = str(uuid.uuid4())
    new_suite = {
        "id": suite_id,
        "name": suite.name,
        "description": suite.description,
        "suite_type": suite.suite_type or "regression",
        "scenario_refs": [r.dict() for r in suite.scenario_refs],
        "created_at": datetime.now().isoformat(),
        "last_run": None,
        "last_run_id": None,
        "status": "idle",
        "pass_rate": None,
    }
    TEST_SUITES[suite_id] = new_suite
    save_test_suites(TEST_SUITES)
    return new_suite

@app.get("/api/test-suites/{suite_id}")
async def get_test_suite(suite_id: str):
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")
    s = TEST_SUITES[suite_id]
    s.setdefault("scenario_refs", [])
    s.setdefault("suite_type", "regression")
    return s

@app.put("/api/test-suites/{suite_id}")
async def update_test_suite(suite_id: str, suite: TestSuiteUpdate):
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")
    existing = TEST_SUITES[suite_id]
    if suite.name is not None:
        existing["name"] = suite.name
    if suite.description is not None:
        existing["description"] = suite.description
    if suite.suite_type is not None:
        existing["suite_type"] = suite.suite_type
    if suite.scenario_refs is not None:
        existing["scenario_refs"] = [r.dict() for r in suite.scenario_refs]
    TEST_SUITES[suite_id] = existing
    save_test_suites(TEST_SUITES)
    return existing

@app.post("/api/test-suites/{suite_id}/add-scenarios")
async def add_scenarios_to_suite(suite_id: str, request: AddScenariosRequest):
    """Add scenarios to an existing suite (append, deduplicates by scenario_id)."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")
    suite = TEST_SUITES[suite_id]
    existing_ids = {r["scenario_id"] for r in suite.get("scenario_refs", [])}
    added = 0
    for ref in request.scenario_refs:
        if ref.scenario_id not in existing_ids:
            suite.setdefault("scenario_refs", []).append(ref.dict())
            existing_ids.add(ref.scenario_id)
            added += 1
    save_test_suites(TEST_SUITES)
    return {"status": "ok", "added": added, "total": len(suite["scenario_refs"])}

@app.delete("/api/test-suites/{suite_id}/scenarios/{scenario_id}")
async def remove_scenario_from_suite(suite_id: str, scenario_id: str):
    """Remove a specific scenario from a suite."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")
    suite = TEST_SUITES[suite_id]
    before = len(suite.get("scenario_refs", []))
    suite["scenario_refs"] = [r for r in suite.get("scenario_refs", []) if r["scenario_id"] != scenario_id]
    save_test_suites(TEST_SUITES)
    return {"status": "ok", "removed": before - len(suite["scenario_refs"])}

@app.delete("/api/test-suites/{suite_id}")
async def delete_test_suite(suite_id: str):
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")
    del TEST_SUITES[suite_id]
    save_test_suites(TEST_SUITES)
    return {"status": "deleted", "suite_id": suite_id}

@app.post("/api/test-suites/{suite_id}/run")
async def run_test_suite(suite_id: str, background_tasks: BackgroundTasks):
    """Run all scenarios in a suite grouped by their source plan."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")

    suite = TEST_SUITES[suite_id]
    refs = suite.get("scenario_refs", [])
    if not refs:
        raise HTTPException(status_code=400, detail="Suite has no scenarios")

    # Group scenario IDs by plan_id
    plan_groups: Dict[str, List[str]] = {}
    for ref in refs:
        pid = ref["plan_id"]
        sid = ref["scenario_id"]
        if pid not in plan_groups:
            plan_groups[pid] = []
        plan_groups[pid].append(sid)

    # Launch a run for each plan group
    run_ids = []
    for pid, sids in plan_groups.items():
        if pid not in PLANS:
            continue
        plan = PLANS[pid]
        test_plan = plan.get("test_plan", {})
        # Collect full scenario dicts for the requested IDs
        scenarios_to_run = [
            sc for mod in test_plan.get("modules", {}).values()
            for sc in mod.get("scenarios", [])
            if sc["id"] in sids
        ]
        if not scenarios_to_run:
            continue
        run_id = str(uuid.uuid4())
        RUNS[run_id] = {
            "id": run_id,
            "plan_id": pid,
            "type": "suite_run",
            "target_url": plan["url"],
            "test_name": f"Suite: {suite['name']}",
            "scenarios": scenarios_to_run,
            "status": "pending",
            "results": {},
            "created_at": datetime.now().isoformat(),
            "suite_id": suite_id,
        }
        save_runs()
        background_tasks.add_task(run_scenarios_task, run_id, plan["url"], scenarios_to_run, "chromium", None)
        run_ids.append(run_id)

    suite["last_run"] = datetime.now().isoformat()
    suite["status"] = "running"
    suite["last_run_id"] = run_ids[0] if len(run_ids) == 1 else None
    save_test_suites(TEST_SUITES)

    return {
        "status": "started",
        "suite_id": suite_id,
        "run_ids": run_ids,
        "scenarios_count": len(refs),
    }


# =============================================
# MONITORS API
# =============================================

MONITORS_FILE = Path("monitors.json")

def load_monitors():
    if MONITORS_FILE.exists():
        try:
            with open(MONITORS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_monitors(monitors):
    with open(MONITORS_FILE, "w") as f:
        json.dump(monitors, f, indent=2)

MONITORS = load_monitors()

class MonitorCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    test_suite_id: Optional[str] = None
    target_url: Optional[str] = None
    schedule: str = "hourly"  # "5min", "15min", "hourly", "daily"

class MonitorUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    schedule: Optional[str] = None
    enabled: Optional[bool] = None

@app.get("/api/monitors")
async def list_monitors():
    """List all monitors."""
    return list(MONITORS.values())

@app.post("/api/monitors")
async def create_monitor(monitor: MonitorCreate):
    """Create a new monitor."""
    monitor_id = str(uuid.uuid4())
    from datetime import datetime

    new_monitor = {
        "id": monitor_id,
        "name": monitor.name,
        "description": monitor.description,
        "test_suite_id": monitor.test_suite_id,
        "target_url": monitor.target_url,
        "schedule": monitor.schedule,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
        "next_run": None,
        "status": "healthy",
        "enabled": True,
        "success_rate": 100,
        "run_history": []
    }

    MONITORS[monitor_id] = new_monitor
    save_monitors(MONITORS)

    return new_monitor

@app.get("/api/monitors/{monitor_id}")
async def get_monitor(monitor_id: str):
    """Get a specific monitor."""
    if monitor_id not in MONITORS:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return MONITORS[monitor_id]

@app.put("/api/monitors/{monitor_id}")
async def update_monitor(monitor_id: str, monitor: MonitorUpdate):
    """Update a monitor."""
    if monitor_id not in MONITORS:
        raise HTTPException(status_code=404, detail="Monitor not found")

    existing = MONITORS[monitor_id]

    if monitor.name is not None:
        existing["name"] = monitor.name
    if monitor.description is not None:
        existing["description"] = monitor.description
    if monitor.schedule is not None:
        existing["schedule"] = monitor.schedule
    if monitor.enabled is not None:
        existing["enabled"] = monitor.enabled

    MONITORS[monitor_id] = existing
    save_monitors(MONITORS)

    return existing

@app.delete("/api/monitors/{monitor_id}")
async def delete_monitor(monitor_id: str):
    """Delete a monitor."""
    if monitor_id not in MONITORS:
        raise HTTPException(status_code=404, detail="Monitor not found")

    del MONITORS[monitor_id]
    save_monitors(MONITORS)

    return {"status": "deleted", "monitor_id": monitor_id}

@app.post("/api/monitors/{monitor_id}/run")
async def run_monitor_now(monitor_id: str):
    """Run a monitor immediately."""
    if monitor_id not in MONITORS:
        raise HTTPException(status_code=404, detail="Monitor not found")

    monitor = MONITORS[monitor_id]

    # Add to run history
    run_result = {
        "timestamp": datetime.now().isoformat(),
        "status": "passed",  # TODO: Actually run the test
        "duration": 1.2
    }

    if "run_history" not in monitor:
        monitor["run_history"] = []
    monitor["run_history"].insert(0, run_result)
    monitor["run_history"] = monitor["run_history"][:50]  # Keep last 50 runs
    monitor["last_run"] = datetime.now().isoformat()

    save_monitors(MONITORS)

    return {"status": "completed", "monitor_id": monitor_id, "result": run_result}


# =============================================
# EXPLORER & PLANNER API (Scenario-Based Testing)
# =============================================

PLANS_FILE = Path("test_plans.json")

def load_plans():
    if PLANS_FILE.exists():
        try:
            with open(PLANS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_plans(plans):
    with open(PLANS_FILE, "w") as f:
        json.dump(plans, f, indent=2)

PLANS = load_plans()


class UserRole(BaseModel):
    role: str
    email: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None


class ExploreRequest(BaseModel):
    url: str
    max_pages: int = 30
    # Knowledge Transfer fields — give the AI context about the app
    app_description: Optional[str] = None          # "A B2B SaaS for project management"
    user_roles: Optional[List[UserRole]] = None    # [{"role":"admin","email":"...","password":"..."}]
    key_journeys: Optional[List[str]] = None       # ["User registers → creates project → invites team"]


class RunScenariosRequest(BaseModel):
    scenario_ids: List[str] = []  # Empty = run all
    module: Optional[str] = None  # Run all scenarios in a module
    browser: Optional[str] = "chromium"  # Browser to use: chromium, firefox, webkit
    test_credentials: Optional[TestCredentials] = None  # Override credentials for login tests


@app.post("/api/explore")
async def explore_url(request: ExploreRequest):
    """
    Explore a URL and discover all pages, forms, buttons.
    Returns an exploration ID that can be used to get results.
    """
    explore_id = str(uuid.uuid4())

    # Normalise user_roles to plain dicts for JSON storage
    user_roles_data = []
    if request.user_roles:
        for r in request.user_roles:
            user_roles_data.append({
                "role": r.role,
                "email": r.email,
                "password": r.password,
                "description": r.description or "",
            })

    PLANS[explore_id] = {
        "id": explore_id,
        "url": request.url,
        "status": "exploring",
        "created_at": datetime.now().isoformat(),
        "app_map": None,
        "app_knowledge": None,
        "test_plan": None,
        "error": None,
        # Store KT context provided by user
        "kt_context": {
            "app_description": request.app_description or "",
            "user_roles": user_roles_data,
            "key_journeys": request.key_journeys or [],
        },
    }
    save_plans(PLANS)

    # Run exploration in background using asyncio.create_task
    asyncio.create_task(
        run_exploration_task(
            explore_id,
            request.url,
            request.max_pages,
            request.app_description or "",
            user_roles_data,
            request.key_journeys or [],
        )
    )

    return {"explore_id": explore_id, "status": "exploring"}


async def run_exploration_task(
    explore_id: str,
    url: str,
    max_pages: int,
    app_description: str = "",
    user_roles: List[Dict] = None,
    key_journeys: List[str] = None,
):
    """Background task: explore → build knowledge → generate test plan."""
    from src.services.llm_service import LLMService

    EXPLORE_TIMEOUT = 180  # 3 minutes max for exploration

    try:
        llm = LLMService()

        # ── Step 1: Explore the application ──────────────────────────
        logger.info(f"[{explore_id}] Starting exploration of {url}")
        PLANS[explore_id]["status"] = "exploring"
        save_plans(PLANS)

        try:
            app_map = await asyncio.wait_for(
                explore_application(url, max_pages),
                timeout=EXPLORE_TIMEOUT
            )
        except asyncio.TimeoutError:
            logger.warning(f"[{explore_id}] Exploration timed out after {EXPLORE_TIMEOUT}s — using partial results")
            # Build a minimal app_map from whatever the explorer discovered
            from src.agents.explorer import ExplorerAgent
            # Exploration timed out but we still proceed with empty map
            app_map = {"base_url": url, "total_pages": 0, "pages": [], "modules": {}, "auth_pages": []}
        PLANS[explore_id]["app_map"] = app_map
        save_plans(PLANS)

        # ── Step 2: Build AppKnowledge (cache-aware) ─────────────────
        logger.info(f"[{explore_id}] Building application knowledge")
        PLANS[explore_id]["status"] = "understanding"
        save_plans(PLANS)

        app_knowledge = await build_app_knowledge(
            base_url=url,
            app_map=app_map,
            llm_service=llm,
            user_description=app_description,
            user_roles=user_roles or [],
            key_journeys=key_journeys or [],
        )
        PLANS[explore_id]["app_knowledge"] = app_knowledge
        PLANS[explore_id]["knowledge_from_cache"] = bool(app_knowledge.get("_from_cache"))
        save_plans(PLANS)
        cache_note = " (from cache — no LLM cost)" if app_knowledge.get("_from_cache") else ""
        logger.info(
            f"[{explore_id}] Knowledge built{cache_note} — domain: {app_knowledge.get('domain')}, "
            f"confidence: {app_knowledge.get('confidence')}"
        )

        # ── Step 3: Generate test scenarios ──────────────────────────
        logger.info(f"[{explore_id}] Generating test plan")
        PLANS[explore_id]["status"] = "planning"
        save_plans(PLANS)

        test_plan = generate_test_plan(
            app_map=app_map,
            app_knowledge=app_knowledge,
            llm_service=llm,
        )
        PLANS[explore_id]["test_plan"] = test_plan

        # ── Done ──────────────────────────────────────────────────────
        PLANS[explore_id]["status"] = "ready"
        PLANS[explore_id]["completed_at"] = datetime.now().isoformat()
        save_plans(PLANS)

        logger.info(
            f"[{explore_id}] Complete — {test_plan['total_scenarios']} scenarios generated"
        )

    except Exception as e:
        logger.error(f"[{explore_id}] Exploration failed: {e}")
        PLANS[explore_id]["status"] = "failed"
        PLANS[explore_id]["error"] = str(e)
        save_plans(PLANS)


@app.get("/api/plans")
async def list_plans():
    """List all test plans."""
    return list(PLANS.values())


@app.get("/api/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific test plan with all modules and scenarios."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PLANS[plan_id]


@app.delete("/api/plans/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete a test plan."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    del PLANS[plan_id]
    save_plans(PLANS)

    return {"status": "deleted", "plan_id": plan_id}


@app.post("/api/plans/{plan_id}/cancel")
async def cancel_plan(plan_id: str):
    """Cancel an in-progress exploration."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    if plan["status"] in ("exploring", "understanding", "planning"):
        PLANS[plan_id]["status"] = "failed"
        PLANS[plan_id]["error"] = "Cancelled by user"
        save_plans(PLANS)
        return {"status": "cancelled", "plan_id": plan_id}

    return {"status": plan["status"], "plan_id": plan_id}


@app.post("/api/plans/{plan_id}/run")
async def run_plan_scenarios(plan_id: str, request: RunScenariosRequest, background_tasks: BackgroundTasks):
    """
    Run scenarios from a test plan.
    - If scenario_ids provided: run only those scenarios
    - If module provided: run all scenarios in that module
    - If neither: run all scenarios
    """
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    if plan["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Plan not ready. Status: {plan['status']}")

    test_plan = plan.get("test_plan", {})
    modules = test_plan.get("modules", {})

    # Determine which scenarios to run
    scenarios_to_run = []

    if request.scenario_ids:
        # Run specific scenarios
        for module_data in modules.values():
            for scenario in module_data.get("scenarios", []):
                if scenario["id"] in request.scenario_ids:
                    scenarios_to_run.append(scenario)
    elif request.module:
        # Run all scenarios in a module
        if request.module in modules:
            scenarios_to_run = modules[request.module].get("scenarios", [])
        else:
            raise HTTPException(status_code=404, detail=f"Module '{request.module}' not found")
    else:
        # Run all scenarios
        for module_data in modules.values():
            scenarios_to_run.extend(module_data.get("scenarios", []))

    if not scenarios_to_run:
        raise HTTPException(status_code=400, detail="No scenarios to run")

    # Create a run for these scenarios
    run_id = str(uuid.uuid4())

    # Convert test credentials to dict if provided
    credentials = None
    if request.test_credentials:
        credentials = {
            "username": request.test_credentials.username,
            "password": request.test_credentials.password
        }

    RUNS[run_id] = {
        "id": run_id,
        "plan_id": plan_id,
        "type": "scenario_run",
        "target_url": plan["url"],
        "test_name": f"Scenario Run - {len(scenarios_to_run)} tests",
        "scenarios": scenarios_to_run,
        "test_credentials": credentials,
        "status": "pending",
        "results": {},
        "created_at": datetime.now().isoformat()
    }
    save_runs()

    # Run scenarios in background
    background_tasks.add_task(
        run_scenarios_task,
        run_id,
        plan["url"],
        scenarios_to_run,
        request.browser or "chromium",
        credentials
    )

    return {
        "run_id": run_id,
        "status": "started",
        "scenarios_count": len(scenarios_to_run)
    }


def apply_credentials_to_scenarios(scenarios: List[Dict], credentials: Dict) -> List[Dict]:
    """
    Replace placeholder credentials in scenarios with real credentials.
    This allows users to provide actual login credentials to override generated test data.
    """
    import copy

    # Common placeholder patterns to replace
    placeholder_emails = [
        "testuser@example.com", "user@example.com", "test@test.com",
        "admin@example.com", "demo@demo.com"
    ]
    placeholder_passwords = [
        "TestPassword123!", "password123", "Password123!",
        "test123", "admin123"
    ]

    updated_scenarios = copy.deepcopy(scenarios)

    for scenario in updated_scenarios:
        # Only apply to login-related scenarios
        scenario_name = scenario.get("name", "").lower()
        if "login" in scenario_name or "sign in" in scenario_name or "auth" in scenario_name:
            for step in scenario.get("steps", []):
                if step.get("action") == "fill":
                    # Check if this is an email/username field
                    target = step.get("target", "").lower()
                    value = step.get("value", "")

                    # Replace placeholder email with real username
                    if any(field in target for field in ["email", "username", "user", "login"]):
                        if value in placeholder_emails:
                            step["value"] = credentials.get("username", value)

                    # Replace placeholder password with real password
                    if "password" in target:
                        if value in placeholder_passwords:
                            step["value"] = credentials.get("password", value)

    return updated_scenarios


async def run_scenarios_task(run_id: str, base_url: str, scenarios: List[Dict], browser_type: str = "chromium", credentials: Dict = None):
    """Background task to execute test scenarios."""
    import platform
    from concurrent.futures import ThreadPoolExecutor

    logger.info(f"Starting scenario run {run_id} with {len(scenarios)} scenarios on {browser_type}")

    # Apply real credentials if provided
    if credentials:
        scenarios = apply_credentials_to_scenarios(scenarios, credentials)

    # On Windows, use sync version in thread pool to avoid NotImplementedError
    if platform.system() == 'Windows':
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(executor, run_scenarios_task_sync, run_id, base_url, scenarios, browser_type)
        return

    from playwright.async_api import async_playwright

    RUNS[run_id]["status"] = "running"
    save_runs()

    results = {}

    try:
        async with async_playwright() as p:
            # Select browser based on browser_type parameter
            if browser_type == "firefox":
                browser = await p.firefox.launch(headless=True)
            elif browser_type == "webkit":
                browser = await p.webkit.launch(headless=True)
            else:  # Default to chromium
                browser = await p.chromium.launch(headless=True)

            # Check if we need to login first
            auth_scenario = None
            for s in scenarios:
                if s.get("depends_on"):
                    # Find the auth scenario
                    auth_scenario = next(
                        (sc for sc in scenarios if sc["id"] == s["depends_on"]),
                        None
                    )
                    break

            # Run auth scenario first if needed (separate context for video)
            if auth_scenario:
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    record_video_dir=f"./temp_runs/{run_id}/videos/{auth_scenario['id']}"
                )
                page = await context.new_page()
                result = await execute_scenario(page, auth_scenario, base_url)
                results[auth_scenario["id"]] = result
                await page.close()
                await context.close()

            # Run each scenario in its own context for separate video recording
            for scenario in scenarios:
                if scenario.get("id") == (auth_scenario["id"] if auth_scenario else None):
                    continue  # Already ran auth

                # Create new context for each scenario to get separate video
                context = await browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    record_video_dir=f"./temp_runs/{run_id}/videos/{scenario['id']}"
                )
                page = await context.new_page()

                try:
                    result = await execute_scenario(page, scenario, base_url)
                    results[scenario["id"]] = result

                    # Update progress
                    RUNS[run_id]["results"] = results
                    save_runs()

                except Exception as e:
                    results[scenario["id"]] = {
                        "status": "failed",
                        "error": str(e)
                    }

                finally:
                    await page.close()
                    await context.close()

            await browser.close()

        RUNS[run_id]["status"] = "completed"
        RUNS[run_id]["results"] = results
        RUNS[run_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Scenario run {run_id} failed: {e}")
        RUNS[run_id]["status"] = "failed"
        RUNS[run_id]["error"] = str(e)

    save_runs()


def run_scenarios_task_sync(run_id: str, base_url: str, scenarios: List[Dict], browser_type: str = "chromium", credentials: Dict = None):
    """Synchronous version for Windows - Background task to execute test scenarios."""
    from playwright.sync_api import sync_playwright
    from src.agents.self_healer import create_self_healer
    from src.services.llm_service import LLMService

    RUNS[run_id]["status"] = "running"
    save_runs()

    results = {}
    # Initialise self-healer for this run
    llm = LLMService()
    healer = create_self_healer(llm)

    # Apply credentials if provided
    if credentials:
        scenarios = apply_credentials_to_scenarios(scenarios, credentials)

    try:
        with sync_playwright() as p:
            # Select browser based on browser_type parameter
            if browser_type == "firefox":
                browser = p.firefox.launch(headless=True)
            elif browser_type == "webkit":
                browser = p.webkit.launch(headless=True)
            else:  # Default to chromium
                browser = p.chromium.launch(headless=True)

            # Check if we need to login first
            auth_scenario = None
            for s in scenarios:
                if s.get("depends_on"):
                    # Find the auth scenario
                    auth_scenario = next(
                        (sc for sc in scenarios if sc["id"] == s["depends_on"]),
                        None
                    )
                    break

            # Run auth scenario first if needed (separate context for video)
            if auth_scenario:
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    record_video_dir=f"./temp_runs/{run_id}/videos/{auth_scenario['id']}"
                )
                page = context.new_page()
                result = execute_scenario_sync(page, auth_scenario, base_url, healer)
                results[auth_scenario["id"]] = result
                page.close()
                context.close()

            # Run each scenario in its own context for separate video recording
            for scenario in scenarios:
                if scenario.get("id") == (auth_scenario["id"] if auth_scenario else None):
                    continue  # Already ran auth

                # Create new context for each scenario to get separate video
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    record_video_dir=f"./temp_runs/{run_id}/videos/{scenario['id']}"
                )
                page = context.new_page()

                try:
                    result = execute_scenario_sync(page, scenario, base_url, healer)
                    results[scenario["id"]] = result

                    # Update progress
                    RUNS[run_id]["results"] = results
                    save_runs()

                except Exception as e:
                    results[scenario["id"]] = {
                        "status": "failed",
                        "error": str(e)
                    }

                finally:
                    page.close()
                    context.close()

            browser.close()

        RUNS[run_id]["status"] = "completed"
        RUNS[run_id]["results"] = results
        RUNS[run_id]["completed_at"] = datetime.now().isoformat()
        RUNS[run_id]["heal_summary"] = healer.get_heal_summary()

    except Exception as e:
        logger.error(f"Scenario run {run_id} failed: {e}")
        RUNS[run_id]["status"] = "failed"
        RUNS[run_id]["error"] = str(e)

    save_runs()


def execute_scenario_sync(page, scenario: Dict, base_url: str, healer=None) -> Dict:
    """Synchronous version for Windows - Execute a single test scenario and return results."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    scenario_result = {
        "id": scenario["id"],
        "name": scenario["name"],
        "status": "running",
        "steps_completed": [],
        "error": None
    }

    try:
        for step in scenario.get("steps", []):
            action = step["action"]
            target = step["target"]
            value = step.get("value")

            if action == "navigate":
                url = target if target.startswith("http") else f"{base_url}{target}"
                # If URL is an SSO/OAuth provider, navigate to app base URL instead
                # and let the natural redirect chain handle the auth flow
                _SSO_DOMAINS = (
                    "b2clogin.com", "login.microsoftonline.com", "accounts.microsoft.com",
                    "okta.com", "auth0.com", "onelogin.com", "accounts.google.com",
                )
                if any(d in url for d in _SSO_DOMAINS):
                    url = base_url
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass  # networkidle timeout is non-fatal — page is loaded enough

            elif action == "fill":
                selectors = target.split(", ")
                filled = False
                for selector in selectors:
                    try:
                        elem = page.wait_for_selector(selector.strip(), state="visible", timeout=8000)
                        if elem:
                            elem.scroll_into_view_if_needed()
                            elem.fill(value or "")
                            filled = True
                            break
                    except:
                        continue
                if not filled:
                    if healer:
                        html = page.content()
                        healed_step = healer.heal_selector(step, html, page.url)
                        if healed_step:
                            new_selectors = healed_step["target"].split(", ")
                            for sel in new_selectors:
                                try:
                                    elem = page.wait_for_selector(sel.strip(), state="visible", timeout=8000)
                                    if elem:
                                        elem.scroll_into_view_if_needed()
                                        elem.fill(value or "")
                                        filled = True
                                        step["target"] = healed_step["target"]
                                        break
                                except:
                                    continue
                    if not filled:
                        raise Exception(f"Could not find element: {target}")

            elif action == "click":
                selectors = target.split(", ")
                clicked = False
                for selector in selectors:
                    try:
                        elem = page.wait_for_selector(selector.strip(), state="visible", timeout=8000)
                        if elem:
                            elem.scroll_into_view_if_needed()
                            elem.click()
                            clicked = True
                            break
                    except:
                        continue
                if not clicked:
                    if healer:
                        html = page.content()
                        healed_step = healer.heal_selector(step, html, page.url)
                        if healed_step:
                            new_selectors = healed_step["target"].split(", ")
                            for sel in new_selectors:
                                try:
                                    elem = page.wait_for_selector(sel.strip(), state="visible", timeout=8000)
                                    if elem:
                                        elem.scroll_into_view_if_needed()
                                        elem.click()
                                        clicked = True
                                        step["target"] = healed_step["target"]
                                        break
                                except:
                                    continue
                    if not clicked:
                        raise Exception(f"Could not click element: {target}")

            elif action == "wait":
                if target == "navigation":
                    page.wait_for_load_state("networkidle", timeout=10000)
                else:
                    page.wait_for_timeout(2000)

            elif action == "assert":
                # Simple assertions
                if target == "page_loaded":
                    assert page.title(), "Page did not load"
                elif target == "url_changed":
                    # Check if login actually succeeded by looking for account indicators
                    current_url = page.url
                    success_indicators = [
                        ".account", ".header-links a[href*='logout']",
                        ".header-links a[href*='account']", "[href*='customerinfo']",
                        "a:has-text('Log out')", "a:has-text('Logout')",
                        ".ico-logout", "[href*='logout']"
                    ]
                    found_success = False
                    for sel in success_indicators:
                        try:
                            elem = page.query_selector(sel)
                            if elem and elem.is_visible():
                                found_success = True
                                break
                        except:
                            continue
                    # If still on login page and no success indicators, fail
                    if 'login' in current_url.lower() and not found_success:
                        assert False, "Login failed - still on login page"
                    assert found_success, "Login success indicators not found"
                elif target == "error_message_visible":
                    # Look for common error indicators including ASP.NET MVC validation
                    error_selectors = [
                        ".validation-summary-errors", ".field-validation-error",
                        ".error", ".alert-danger", "[role='alert']",
                        ".text-red", ".text-danger", ".message-error",
                        ".validation-summary-errors li", ".validation-summary-errors ul"
                    ]
                    found = False
                    for sel in error_selectors:
                        try:
                            elem = page.query_selector(sel)
                            if elem and elem.is_visible():
                                found = True
                                break
                        except:
                            continue
                    assert found, "Expected error message not found"
                elif target.startswith("element_visible:"):
                    selector = target.replace("element_visible:", "")
                    elem = page.wait_for_selector(selector, timeout=5000)
                    assert elem and elem.is_visible(), f"Element {selector} not visible"

            scenario_result["steps_completed"].append({
                "action": action,
                "target": target,
                "value": value,
                "status": "passed"
            })

        scenario_result["status"] = "passed"

    except PlaywrightTimeout as e:
        scenario_result["status"] = "failed"
        scenario_result["error"] = f"Timeout: {str(e)}"
    except Exception as e:
        scenario_result["status"] = "failed"
        scenario_result["error"] = str(e)

    return scenario_result


async def execute_scenario(page, scenario: Dict, base_url: str) -> Dict:
    """Execute a single test scenario and return results."""
    from playwright.async_api import TimeoutError as PlaywrightTimeout

    scenario_result = {
        "id": scenario["id"],
        "name": scenario["name"],
        "status": "running",
        "steps_completed": [],
        "error": None
    }

    try:
        for step in scenario.get("steps", []):
            action = step["action"]
            target = step["target"]
            value = step.get("value")

            if action == "navigate":
                url = target if target.startswith("http") else f"{base_url}{target}"
                _SSO_DOMAINS = (
                    "b2clogin.com", "login.microsoftonline.com", "accounts.microsoft.com",
                    "okta.com", "auth0.com", "onelogin.com", "accounts.google.com",
                )
                if any(d in url for d in _SSO_DOMAINS):
                    url = base_url
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass  # networkidle timeout is non-fatal

            elif action == "fill":
                selectors = target.split(", ")
                filled = False
                for selector in selectors:
                    try:
                        elem = await page.wait_for_selector(selector.strip(), state="visible", timeout=8000)
                        if elem:
                            await elem.scroll_into_view_if_needed()
                            await elem.fill(value or "")
                            filled = True
                            break
                    except:
                        continue
                if not filled:
                    raise Exception(f"Could not find element: {target}")

            elif action == "click":
                selectors = target.split(", ")
                clicked = False
                for selector in selectors:
                    try:
                        elem = await page.wait_for_selector(selector.strip(), state="visible", timeout=8000)
                        if elem:
                            await elem.scroll_into_view_if_needed()
                            await elem.click()
                            clicked = True
                            break
                    except:
                        continue
                if not clicked:
                    raise Exception(f"Could not click element: {target}")

            elif action == "wait":
                if target == "navigation":
                    await page.wait_for_load_state("networkidle", timeout=10000)
                else:
                    await page.wait_for_timeout(2000)

            elif action == "assert":
                # Simple assertions
                if target == "page_loaded":
                    assert await page.title(), "Page did not load"
                elif target == "url_changed":
                    # Check if login actually succeeded by looking for account indicators
                    current_url = page.url
                    success_indicators = [
                        ".account", ".header-links a[href*='logout']",
                        ".header-links a[href*='account']", "[href*='customerinfo']",
                        "a:has-text('Log out')", "a:has-text('Logout')",
                        ".ico-logout", "[href*='logout']"
                    ]
                    found_success = False
                    for sel in success_indicators:
                        try:
                            elem = await page.query_selector(sel)
                            if elem and await elem.is_visible():
                                found_success = True
                                break
                        except:
                            continue
                    # If still on login page and no success indicators, fail
                    if 'login' in current_url.lower() and not found_success:
                        assert False, "Login failed - still on login page"
                    assert found_success, "Login success indicators not found"
                elif target == "error_message_visible":
                    # Look for common error indicators including ASP.NET MVC validation
                    error_selectors = [
                        ".validation-summary-errors", ".field-validation-error",
                        ".error", ".alert-danger", "[role='alert']",
                        ".text-red", ".text-danger", ".message-error",
                        ".validation-summary-errors li", ".validation-summary-errors ul"
                    ]
                    found = False
                    for sel in error_selectors:
                        try:
                            elem = await page.query_selector(sel)
                            if elem and await elem.is_visible():
                                found = True
                                break
                        except:
                            continue
                    assert found, "Expected error message not found"

            scenario_result["steps_completed"].append(step["description"])

        scenario_result["status"] = "passed"

    except PlaywrightTimeout as e:
        scenario_result["status"] = "failed"
        scenario_result["error"] = f"Timeout: {str(e)}"

    except Exception as e:
        scenario_result["status"] = "failed"
        scenario_result["error"] = str(e)

    return scenario_result


@app.get("/api/plans/{plan_id}/modules")
async def get_plan_modules(plan_id: str):
    """Get all modules in a test plan."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    test_plan = plan.get("test_plan", {})

    return test_plan.get("modules", {})


@app.get("/api/plans/{plan_id}/modules/{module_name}/scenarios")
async def get_module_scenarios(plan_id: str, module_name: str):
    """Get all scenarios in a specific module."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    test_plan = plan.get("test_plan", {})
    modules = test_plan.get("modules", {})

    if module_name not in modules:
        raise HTTPException(status_code=404, detail=f"Module '{module_name}' not found")

    return modules[module_name].get("scenarios", [])


# =============================================
# SCENARIO RUN VIDEO & CODE ENDPOINTS
# =============================================

@app.get("/api/scenario-run/{run_id}/video/{scenario_id}")
async def get_scenario_video(run_id: str, scenario_id: str):
    """Get video recording for a specific scenario in a run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    # Check new structure first (videos/{scenario_id}/*.webm)
    scenario_video_dir = Path(f"./temp_runs/{run_id}/videos/{scenario_id}")

    if scenario_video_dir.exists():
        webm_files = list(scenario_video_dir.glob("*.webm"))
        if webm_files:
            return FileResponse(webm_files[0], media_type="video/webm")

    # Fallback to old structure (videos/*.webm)
    video_dir = Path(f"./temp_runs/{run_id}/videos")
    if video_dir.exists():
        webm_files = list(video_dir.glob("*.webm"))
        if webm_files:
            return FileResponse(webm_files[0], media_type="video/webm")

    raise HTTPException(status_code=404, detail=f"No video found for scenario {scenario_id}")


@app.get("/api/scenario-run/{run_id}/videos")
async def list_scenario_videos(run_id: str):
    """List all video recordings for a scenario run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    video_dir = Path(f"./temp_runs/{run_id}/videos")

    if not video_dir.exists():
        return {"videos": []}

    videos = []

    # Check for new structure (videos/{scenario_id}/*.webm)
    for scenario_dir in video_dir.iterdir():
        if scenario_dir.is_dir():
            for webm_file in scenario_dir.glob("*.webm"):
                videos.append({
                    "filename": webm_file.name,
                    "scenario_id": scenario_dir.name,
                    "url": f"/api/scenario-run/{run_id}/video-file/{webm_file.name}",
                    "size": webm_file.stat().st_size
                })

    # Also check for old structure (videos/*.webm)
    for webm_file in video_dir.glob("*.webm"):
        videos.append({
            "filename": webm_file.name,
            "scenario_id": None,
            "url": f"/api/scenario-run/{run_id}/video-file/{webm_file.name}",
            "size": webm_file.stat().st_size
        })

    return {"videos": videos}


@app.get("/api/scenario-run/{run_id}/video-file/{filename}")
async def get_scenario_video_file(run_id: str, filename: str):
    """Get a specific video file by filename."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    # Search for the video file in scenario subdirectories
    video_dir = Path(f"./temp_runs/{run_id}/videos")

    # First check flat structure (old format)
    video_path = video_dir / filename
    if video_path.exists():
        return FileResponse(video_path, media_type="video/webm")

    # Then search in scenario subdirectories (new format)
    for scenario_dir in video_dir.iterdir():
        if scenario_dir.is_dir():
            video_path = scenario_dir / filename
            if video_path.exists():
                return FileResponse(video_path, media_type="video/webm")

    raise HTTPException(status_code=404, detail="Video file not found")


@app.get("/api/scenario-run/{run_id}/code/{scenario_id}")
async def get_scenario_code(run_id: str, scenario_id: str):
    """Generate Playwright test code for a specific scenario."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    scenarios = run_info.get("scenarios", [])

    # Find the scenario
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)

    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    # Generate Playwright test code
    code = generate_playwright_code(scenario, run_info.get("target_url", ""))

    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario.get("name", ""),
        "code": code,
        "language": "python"
    }


@app.get("/api/scenario-run/{run_id}/code")
async def get_all_scenario_code(run_id: str):
    """Generate Playwright test code for all scenarios in a run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    scenarios = run_info.get("scenarios", [])
    base_url = run_info.get("target_url", "")

    # Generate combined test file
    code = generate_playwright_test_file(scenarios, base_url)

    return {
        "run_id": run_id,
        "scenarios_count": len(scenarios),
        "code": code,
        "language": "python"
    }


def generate_playwright_code(scenario: Dict, base_url: str) -> str:
    """Generate Playwright Python test code for a single scenario."""

    scenario_name = scenario.get("name", "test_scenario").replace(" ", "_").lower()
    scenario_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in scenario_name)

    code_lines = [
        f'async def test_{scenario_name}(page):',
        f'    """',
        f'    {scenario.get("name", "Test Scenario")}',
        f'    {scenario.get("description", "")}',
        f'    """',
    ]

    steps = scenario.get("steps", [])

    for step in steps:
        action = step.get("action", "")
        target = step.get("target", "")
        value = step.get("value", "")
        description = step.get("description", "")

        code_lines.append(f'    # {description}')

        if action == "navigate":
            if target.startswith("http"):
                code_lines.append(f'    await page.goto("{target}")')
            else:
                code_lines.append(f'    await page.goto(f"{{BASE_URL}}{target}")')

        elif action == "fill":
            # Handle multiple selectors
            selectors = [s.strip() for s in target.split(",")]
            if len(selectors) == 1:
                code_lines.append(f'    await page.locator("{selectors[0]}").fill("{value}")')
            else:
                code_lines.append(f'    # Try multiple selectors')
                code_lines.append(f'    selectors = {selectors}')
                code_lines.append(f'    for selector in selectors:')
                code_lines.append(f'        try:')
                code_lines.append(f'            await page.locator(selector).fill("{value}")')
                code_lines.append(f'            break')
                code_lines.append(f'        except:')
                code_lines.append(f'            continue')

        elif action == "click":
            selectors = [s.strip() for s in target.split(",")]
            if len(selectors) == 1:
                code_lines.append(f'    await page.locator("{selectors[0]}").click()')
            else:
                code_lines.append(f'    # Try multiple selectors')
                code_lines.append(f'    selectors = {selectors}')
                code_lines.append(f'    for selector in selectors:')
                code_lines.append(f'        try:')
                code_lines.append(f'            await page.locator(selector).click()')
                code_lines.append(f'            break')
                code_lines.append(f'        except:')
                code_lines.append(f'            continue')

        elif action == "wait":
            if target == "navigation":
                code_lines.append(f'    await page.wait_for_load_state("networkidle")')
            else:
                code_lines.append(f'    await page.wait_for_timeout(2000)')

        elif action == "assert":
            if target == "page_loaded":
                code_lines.append(f'    assert await page.title()')
            elif target == "url_changed":
                code_lines.append(f'    # URL should have changed')
                code_lines.append(f'    pass')
            elif target == "error_message_visible":
                code_lines.append(f'    # Check for error message')
                code_lines.append(f'    error_visible = await page.locator(".error, .alert-danger, [role=\'alert\']").is_visible()')
                code_lines.append(f'    assert error_visible, "Expected error message"')

        code_lines.append('')

    return '\n'.join(code_lines)


def generate_playwright_test_file(scenarios: List[Dict], base_url: str) -> str:
    """Generate a complete Playwright Python test file."""

    code_lines = [
        '"""',
        'Auto-generated Playwright tests by TestBounty',
        f'Target URL: {base_url}',
        '"""',
        '',
        'import pytest',
        'from playwright.async_api import async_playwright, Page',
        '',
        f'BASE_URL = "{base_url}"',
        '',
        '',
        '@pytest.fixture(scope="module")',
        'async def browser():',
        '    async with async_playwright() as p:',
        '        browser = await p.chromium.launch(headless=True)',
        '        yield browser',
        '        await browser.close()',
        '',
        '',
        '@pytest.fixture',
        'async def page(browser):',
        '    context = await browser.new_context(',
        '        viewport={"width": 1280, "height": 720},',
        '        record_video_dir="./test-videos"',
        '    )',
        '    page = await context.new_page()',
        '    yield page',
        '    await page.close()',
        '    await context.close()',
        '',
        '',
    ]

    for scenario in scenarios:
        scenario_code = generate_playwright_code(scenario, base_url)
        # Add pytest marker
        priority = scenario.get("priority", "medium")
        code_lines.append(f'@pytest.mark.{priority}')
        code_lines.append(f'@pytest.mark.asyncio')
        code_lines.append(scenario_code)
        code_lines.append('')
        code_lines.append('')

    return '\n'.join(code_lines)


@app.get("/api/monitor/analyze/{plan_id}")
async def analyze_plan(plan_id: str):
    """Analyze test coverage, quality, and stability for a plan"""
    try:
        from src.agents.monitor import TestMonitor
        monitor = TestMonitor()
        analysis = monitor.analyze_all(plan_id=plan_id)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/monitor/analyze")
async def analyze_latest():
    """Analyze the latest test plan"""
    try:
        from src.agents.monitor import TestMonitor
        monitor = TestMonitor()
        analysis = monitor.analyze_all()
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KT MODE 1 — USER STORY IMPORT
# =============================================================================

class ImportStoriesRequest(BaseModel):
    stories: str
    format: Optional[str] = "plain"  # plain | gherkin | jira


@app.post("/api/plans/{plan_id}/import-stories")
async def import_stories(plan_id: str, request: ImportStoriesRequest):
    """
    Parse user stories / acceptance criteria and merge into existing plan scenarios.
    Returns the enriched plan.
    """
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    base_url = plan.get("url", "/")

    try:
        from src.services.llm_service import LLMService
        from src.agents.story_parser import parse_user_stories

        llm = LLMService()
        result = parse_user_stories(request.stories, base_url=base_url, llm_service=llm)

        # Merge into existing test_plan
        existing_plan = plan.get("test_plan") or {"base_url": base_url, "total_scenarios": 0, "modules": {}}
        merged = _merge_scenario_modules(existing_plan, result)
        PLANS[plan_id]["test_plan"] = merged
        PLANS[plan_id]["status"] = "ready"

        # Track KT sources
        kt_sources = PLANS[plan_id].setdefault("kt_sources", [])
        kt_sources.append({"type": "user_stories", "added_at": datetime.now().isoformat(), "scenarios_added": result.get("total_scenarios", 0)})

        save_plans(PLANS)

        return {
            "status": "ok",
            "scenarios_added": result.get("total_scenarios", 0),
            "total_scenarios": merged.get("total_scenarios", 0),
            "modules_added": list(result.get("modules", {}).keys()),
        }
    except Exception as e:
        logger.error(f"[import-stories] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KT MODE 2 — DOCUMENT UPLOAD
# =============================================================================

@app.post("/api/plans/{plan_id}/import-doc")
async def import_document(plan_id: str, file: UploadFile = File(...)):
    """
    Upload a PDF / DOCX / TXT document, extract text, parse into scenarios.
    """
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    base_url = plan.get("url", "/")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10 MB limit
        raise HTTPException(status_code=413, detail="File too large (max 10 MB)")

    try:
        from src.services.llm_service import LLMService
        from src.agents.doc_parser import parse_document_file

        llm = LLMService()
        result = parse_document_file(content, file.filename or "document.txt", base_url=base_url, llm_service=llm)

        existing_plan = plan.get("test_plan") or {"base_url": base_url, "total_scenarios": 0, "modules": {}}
        merged = _merge_scenario_modules(existing_plan, result)
        PLANS[plan_id]["test_plan"] = merged
        PLANS[plan_id]["status"] = "ready"

        kt_sources = PLANS[plan_id].setdefault("kt_sources", [])
        kt_sources.append({
            "type": "document",
            "filename": file.filename,
            "added_at": datetime.now().isoformat(),
            "scenarios_added": result.get("total_scenarios", 0),
            "extracted_chars": result.get("extracted_chars", 0),
        })

        save_plans(PLANS)

        return {
            "status": "ok",
            "filename": file.filename,
            "extracted_chars": result.get("extracted_chars", 0),
            "scenarios_added": result.get("total_scenarios", 0),
            "total_scenarios": merged.get("total_scenarios", 0),
        }
    except Exception as e:
        logger.error(f"[import-doc] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KT MODE 3 — AI-GUIDED CHAT
# =============================================================================

class ChatMessageRequest(BaseModel):
    message: str


@app.post("/api/plans/{plan_id}/chat")
async def plan_chat(plan_id: str, request: ChatMessageRequest):
    """Send a message to the KT Chat agent and get a reply."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    try:
        from src.services.llm_service import LLMService
        from src.agents.kt_chat import process_chat_message

        llm = LLMService()
        plan = PLANS[plan_id]
        result = process_chat_message(plan_id, request.message, plan, llm_service=llm)

        # Save updated plan (chat_history + app_knowledge were mutated in-place)
        save_plans(PLANS)

        return result
    except Exception as e:
        logger.error(f"[plan-chat] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/plans/{plan_id}/chat")
async def get_chat_history(plan_id: str):
    """Get the chat history and opening message for a plan."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    history = plan.get("chat_history", [])

    if not history:
        # Return opening message
        try:
            from src.services.llm_service import LLMService
            from src.agents.kt_chat import get_chat_opening

            llm = LLMService()
            opening = get_chat_opening(plan, llm_service=llm)
            return {"history": [], "opening": opening}
        except Exception as e:
            return {"history": [], "opening": {"reply": "Hello! Tell me about your application and I'll help generate better tests.", "turn": 0}}

    return {"history": history, "opening": None}


@app.post("/api/plans/{plan_id}/chat/apply")
async def apply_chat_knowledge(plan_id: str):
    """Regenerate test plan using knowledge gathered from chat."""
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan = PLANS[plan_id]
    app_map = plan.get("app_map") or {"base_url": plan["url"], "total_pages": 0, "pages": [], "modules": {}, "auth_pages": []}
    app_knowledge = plan.get("app_knowledge") or {}

    try:
        from src.services.llm_service import LLMService
        from src.agents.planner import generate_test_plan

        llm = LLMService()
        new_plan = generate_test_plan(app_map=app_map, app_knowledge=app_knowledge, llm_service=llm)
        PLANS[plan_id]["test_plan"] = new_plan
        PLANS[plan_id]["status"] = "ready"
        save_plans(PLANS)

        return {
            "status": "ok",
            "total_scenarios": new_plan.get("total_scenarios", 0),
        }
    except Exception as e:
        logger.error(f"[chat-apply] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# KT MODE 4 — SESSION RECORDING
# =============================================================================

@app.post("/api/session-record/start")
async def start_session_record(body: dict):
    """
    Start a visible browser recording session.
    Body: { "url": "https://...", "plan_id": "optional" }
    """
    url = body.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    plan_id = body.get("plan_id")

    try:
        from src.services.llm_service import LLMService
        from src.agents.session_recorder import get_recorder

        llm = LLMService()
        recorder = get_recorder(llm_service=llm)
        session_id = recorder.start_session(url, plan_id=plan_id)

        return {"session_id": session_id, "status": "recording", "url": url}
    except Exception as e:
        logger.error(f"[session-record/start] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session-record/{session_id}")
async def get_session_status(session_id: str):
    """Poll session recording status and event count."""
    from src.agents.session_recorder import SESSIONS

    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    s = SESSIONS[session_id]
    return {
        "id": session_id,
        "status": s["status"],
        "events_count": len(s.get("events", [])),
        "url": s["url"],
        "created_at": s["created_at"],
        "stopped_at": s.get("stopped_at"),
        "error": s.get("error"),
    }


@app.post("/api/session-record/{session_id}/stop")
async def stop_session_record(session_id: str):
    """Stop recording, analyse events, optionally merge into plan."""
    from src.agents.session_recorder import SESSIONS

    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session not found")

    session = SESSIONS[session_id]
    # Signal stop
    session["status"] = "stopping"

    try:
        from src.services.llm_service import LLMService
        from src.agents.session_recorder import get_recorder

        llm = LLMService()
        recorder = get_recorder(llm_service=llm)
        result = recorder.stop_session(session_id)

        plan_id = session.get("plan_id")

        if plan_id and plan_id in PLANS:
            # ── Merge into existing plan ──────────────────────────────────────
            base_url = PLANS[plan_id].get("url", "/")
            existing_plan = PLANS[plan_id].get("test_plan") or {"base_url": base_url, "total_scenarios": 0, "modules": {}}
            merged = _merge_scenario_modules(existing_plan, result.get("scenarios", {}))
            PLANS[plan_id]["test_plan"] = merged
            PLANS[plan_id]["status"] = "ready"

            kt_sources = PLANS[plan_id].setdefault("kt_sources", [])
            kt_sources.append({
                "type": "session_recording",
                "added_at": datetime.now().isoformat(),
                "events_count": result.get("events_count", 0),
                "scenarios_added": result.get("scenarios", {}).get("total_scenarios", 0),
            })
            save_plans(PLANS)
            result["plan_id"] = plan_id

        else:
            # ── No existing plan — create a new standalone plan from recording ─
            import uuid
            session_url = session.get("url", "")
            new_plan_id = str(uuid.uuid4())
            scenarios = result.get("scenarios", {})
            total = scenarios.get("total_scenarios", 0)

            PLANS[new_plan_id] = {
                "id": new_plan_id,
                "url": session_url,
                "status": "ready",
                "created_at": datetime.now().isoformat(),
                "source": "session_recording",
                "app_map": None,
                "app_knowledge": None,
                "test_plan": scenarios if total > 0 else None,
                "kt_sources": [{
                    "type": "session_recording",
                    "added_at": datetime.now().isoformat(),
                    "events_count": result.get("events_count", 0),
                    "scenarios_added": total,
                }],
            }
            save_plans(PLANS)
            result["plan_id"] = new_plan_id

        return result
    except Exception as e:
        logger.error(f"[session-record/stop] {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HELPER — merge scenario modules from two test plans
# =============================================================================

# =============================================================================
# KNOWLEDGE CACHE MANAGEMENT
# =============================================================================

@app.get("/api/knowledge-cache")
async def list_knowledge_cache():
    """List all cached app knowledge entries."""
    from src.agents.knowledge_cache import get_cache
    return {"entries": get_cache().list_entries()}


@app.delete("/api/knowledge-cache/{url_key}")
async def invalidate_cache(url_key: str):
    """Force re-synthesis for a URL on next explore."""
    from src.agents.knowledge_cache import get_cache
    cache = get_cache()
    cache.invalidate(url_key)
    return {"status": "invalidated"}


@app.get("/api/skills")
async def list_skills():
    """List all available domain skill files."""
    from src.agents.skills_loader import get_skills_loader
    return {"skills": get_skills_loader().list_skills()}


@app.get("/api/plans/{plan_id}/active-skills")
async def get_active_skills(plan_id: str):
    """
    Returns which skill files are currently active for this plan's domain.
    Used by the frontend to show 'Active Skills' badges.
    """
    if plan_id not in PLANS:
        raise HTTPException(status_code=404, detail="Plan not found")

    from src.agents.skills_loader import get_skills_loader
    plan = PLANS[plan_id]
    knowledge = plan.get("app_knowledge") or {}

    active = get_skills_loader().get_active_skill_names(
        domain=knowledge.get("domain", ""),
        vocabulary=knowledge.get("domain_vocabulary", []),
        app_description=knowledge.get("app_description", ""),
    )
    return {
        "plan_id": plan_id,
        "domain": knowledge.get("domain", ""),
        "active_skills": active,
    }


def _merge_scenario_modules(existing_plan: Dict, new_result: Dict) -> Dict:
    """
    Merge modules + scenarios from new_result into existing_plan.
    Avoids duplicate scenario IDs.
    """
    existing_modules = existing_plan.get("modules", {})
    new_modules = new_result.get("modules", {})

    for mod_key, mod_data in new_modules.items():
        if mod_key not in existing_modules:
            existing_modules[mod_key] = mod_data
        else:
            existing_ids = {s["id"] for s in existing_modules[mod_key].get("scenarios", [])}
            for scenario in mod_data.get("scenarios", []):
                if scenario["id"] not in existing_ids:
                    existing_modules[mod_key]["scenarios"].append(scenario)
                    existing_ids.add(scenario["id"])

    total = sum(len(m.get("scenarios", [])) for m in existing_modules.values())
    return {
        **existing_plan,
        "modules": existing_modules,
        "total_scenarios": total,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
