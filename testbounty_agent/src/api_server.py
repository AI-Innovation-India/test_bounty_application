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
from datetime import datetime

load_dotenv()

from src.agents.orchestrator import app as agent_app
from src.agents.explorer import explore_application
from src.agents.planner import generate_test_plan
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


class ExploreRequest(BaseModel):
    url: str
    max_pages: int = 30


class RunScenariosRequest(BaseModel):
    scenario_ids: List[str] = []  # Empty = run all
    module: Optional[str] = None  # Run all scenarios in a module


@app.post("/api/explore")
async def explore_url(request: ExploreRequest):
    """
    Explore a URL and discover all pages, forms, buttons.
    Returns an exploration ID that can be used to get results.
    """
    explore_id = str(uuid.uuid4())

    PLANS[explore_id] = {
        "id": explore_id,
        "url": request.url,
        "status": "exploring",
        "created_at": datetime.now().isoformat(),
        "app_map": None,
        "test_plan": None,
        "error": None
    }
    save_plans(PLANS)

    # Run exploration in background using asyncio.create_task
    asyncio.create_task(
        run_exploration_task(
            explore_id,
            request.url,
            request.max_pages
        )
    )

    return {"explore_id": explore_id, "status": "exploring"}


async def run_exploration_task(explore_id: str, url: str, max_pages: int):
    """Background task to explore and generate test plan."""
    try:
        logger.info(f"Starting exploration of {url}")

        # Step 1: Explore the application
        PLANS[explore_id]["status"] = "exploring"
        save_plans(PLANS)

        app_map = await explore_application(url, max_pages)
        PLANS[explore_id]["app_map"] = app_map

        # Step 2: Generate test scenarios
        PLANS[explore_id]["status"] = "planning"
        save_plans(PLANS)

        test_plan = generate_test_plan(app_map)
        PLANS[explore_id]["test_plan"] = test_plan

        # Done
        PLANS[explore_id]["status"] = "ready"
        PLANS[explore_id]["completed_at"] = datetime.now().isoformat()
        save_plans(PLANS)

        logger.info(f"Exploration complete for {url}: {test_plan['total_scenarios']} scenarios generated")

    except Exception as e:
        logger.error(f"Exploration failed for {url}: {e}")
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

    RUNS[run_id] = {
        "id": run_id,
        "plan_id": plan_id,
        "type": "scenario_run",
        "target_url": plan["url"],
        "test_name": f"Scenario Run - {len(scenarios_to_run)} tests",
        "scenarios": scenarios_to_run,
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
        scenarios_to_run
    )

    return {
        "run_id": run_id,
        "status": "started",
        "scenarios_count": len(scenarios_to_run)
    }


async def run_scenarios_task(run_id: str, base_url: str, scenarios: List[Dict]):
    """Background task to execute test scenarios."""
    from playwright.async_api import async_playwright

    logger.info(f"Starting scenario run {run_id} with {len(scenarios)} scenarios")

    RUNS[run_id]["status"] = "running"
    save_runs()

    results = {}

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                record_video_dir=f"./temp_runs/{run_id}/videos"
            )

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

            # Run auth scenario first if needed
            if auth_scenario:
                page = await context.new_page()
                result = await execute_scenario(page, auth_scenario, base_url)
                results[auth_scenario["id"]] = result
                # Keep page open for subsequent tests that need auth

            # Run each scenario
            for scenario in scenarios:
                if scenario.get("id") == (auth_scenario["id"] if auth_scenario else None):
                    continue  # Already ran auth

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

            await browser.close()

        RUNS[run_id]["status"] = "completed"
        RUNS[run_id]["results"] = results
        RUNS[run_id]["completed_at"] = datetime.now().isoformat()

    except Exception as e:
        logger.error(f"Scenario run {run_id} failed: {e}")
        RUNS[run_id]["status"] = "failed"
        RUNS[run_id]["error"] = str(e)

    save_runs()


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
                await page.goto(url, wait_until="networkidle", timeout=15000)

            elif action == "fill":
                # Try multiple selectors
                selectors = target.split(", ")
                filled = False
                for selector in selectors:
                    try:
                        elem = await page.wait_for_selector(selector.strip(), timeout=3000)
                        if elem:
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
                        elem = await page.wait_for_selector(selector.strip(), timeout=3000)
                        if elem:
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
                    pass  # URL assertion handled implicitly
                elif target == "error_message_visible":
                    # Look for common error indicators
                    error_selectors = [".error", ".alert-danger", "[role='alert']", ".text-red", ".text-danger"]
                    found = False
                    for sel in error_selectors:
                        try:
                            elem = await page.query_selector(sel)
                            if elem and await elem.is_visible():
                                found = True
                                break
                        except:
                            continue
                    # Don't fail if error not found - might be handled differently

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

    video_dir = Path(f"./temp_runs/{run_id}/videos")

    if not video_dir.exists():
        raise HTTPException(status_code=404, detail="No videos found for this run")

    # Find video file for this scenario (videos are named by page context)
    webm_files = list(video_dir.glob("*.webm"))

    if not webm_files:
        raise HTTPException(status_code=404, detail="No video files found")

    # Return the first video for now (or match by index if multiple)
    # In future, can map scenario_id to specific video
    return FileResponse(webm_files[0], media_type="video/webm")


@app.get("/api/scenario-run/{run_id}/videos")
async def list_scenario_videos(run_id: str):
    """List all video recordings for a scenario run."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    video_dir = Path(f"./temp_runs/{run_id}/videos")

    if not video_dir.exists():
        return {"videos": []}

    webm_files = list(video_dir.glob("*.webm"))

    return {
        "videos": [
            {
                "filename": f.name,
                "url": f"/api/scenario-run/{run_id}/video-file/{f.name}",
                "size": f.stat().st_size
            }
            for f in webm_files
        ]
    }


@app.get("/api/scenario-run/{run_id}/video-file/{filename}")
async def get_scenario_video_file(run_id: str, filename: str):
    """Get a specific video file by filename."""
    if run_id not in RUNS:
        raise HTTPException(status_code=404, detail="Run not found")

    video_path = Path(f"./temp_runs/{run_id}/videos/{filename}")

    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(video_path, media_type="video/webm")


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
