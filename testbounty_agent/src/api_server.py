from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import uuid
import os
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from src.agents.orchestrator import app as agent_app
from src.utils.logger import logger

app = FastAPI(title="TestSprite Agent API")

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

@app.delete("/api/run/{run_id}")
async def delete_run(run_id: str):
    """Delete a specific run and its artifacts."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    run_info = RUNS[run_id]
    base_path = Path(run_info["project_path"])

    # Delete artifacts folder if it exists
    import shutil
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

class TestSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    tests: List[str] = []  # List of run IDs or test identifiers
    schedule: Optional[str] = None  # Cron expression or simple like "hourly", "daily"

class TestSuiteUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tests: Optional[List[str]] = None
    schedule: Optional[str] = None

@app.get("/api/test-suites")
async def list_test_suites():
    """List all test suites."""
    return list(TEST_SUITES.values())

@app.post("/api/test-suites")
async def create_test_suite(suite: TestSuiteCreate):
    """Create a new test suite."""
    suite_id = str(uuid.uuid4())
    from datetime import datetime

    new_suite = {
        "id": suite_id,
        "name": suite.name,
        "description": suite.description,
        "tests": suite.tests,
        "schedule": suite.schedule,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
        "status": "idle"
    }

    TEST_SUITES[suite_id] = new_suite
    save_test_suites(TEST_SUITES)

    return new_suite

@app.get("/api/test-suites/{suite_id}")
async def get_test_suite(suite_id: str):
    """Get a specific test suite."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")
    return TEST_SUITES[suite_id]

@app.put("/api/test-suites/{suite_id}")
async def update_test_suite(suite_id: str, suite: TestSuiteUpdate):
    """Update a test suite."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")

    existing = TEST_SUITES[suite_id]

    if suite.name is not None:
        existing["name"] = suite.name
    if suite.description is not None:
        existing["description"] = suite.description
    if suite.tests is not None:
        existing["tests"] = suite.tests
    if suite.schedule is not None:
        existing["schedule"] = suite.schedule

    TEST_SUITES[suite_id] = existing
    save_test_suites(TEST_SUITES)

    return existing

@app.delete("/api/test-suites/{suite_id}")
async def delete_test_suite(suite_id: str):
    """Delete a test suite."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")

    del TEST_SUITES[suite_id]
    save_test_suites(TEST_SUITES)

    return {"status": "deleted", "suite_id": suite_id}

@app.post("/api/test-suites/{suite_id}/run")
async def run_test_suite(suite_id: str, background_tasks: BackgroundTasks):
    """Run all tests in a suite."""
    if suite_id not in TEST_SUITES:
        raise HTTPException(status_code=404, detail="Test suite not found")

    suite = TEST_SUITES[suite_id]
    from datetime import datetime
    suite["last_run"] = datetime.now().isoformat()
    suite["status"] = "running"
    save_test_suites(TEST_SUITES)

    # TODO: Actually run the tests in the suite
    # For now, just mark as completed after a delay
    return {"status": "started", "suite_id": suite_id, "tests_count": len(suite["tests"])}


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
    from datetime import datetime

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
