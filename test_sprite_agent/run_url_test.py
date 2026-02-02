import asyncio
import os
import sys
import json
from pathlib import Path

# Set Google API Key BEFORE imports
os.environ["GOOGLE_API_KEY"] = "AIzaSyClrxL0XGFEiRxOXj_BJK042c3xmphiKGk"

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.agents.orchestrator import app

async def main():
    target_url = "https://www.testsprite.com/dashboard"
    # Create a directory for this test run
    project_path = os.path.abspath("url_test_targets/testsprite_dashboard")
    os.makedirs(project_path, exist_ok=True)
    
    print(f"\n🚀 STARTING URL TEST")
    print(f"Target URL: {target_url}")
    print(f"Artifacts Path: {project_path}\n")

    initial_state = {
        "project_path": project_path,
        "target_url": target_url,
        "steps_completed": [],
        "error_log": []
    }

    # Run the graph
    async for event in app.astream(initial_state):
        for key, value in event.items():
            print(f"✅ Completed Step: {key}")
            if "error_log" in value and value["error_log"]:
                print(f"❌ Errors: {value['error_log']}")
    
    print("\n✨ TEST COMPLETE")

    # Verify artifacts
    report_path = Path(project_path) / "testsprite_tests" / "reports" / "report.md"
    if report_path.exists():
        print(f"\n📄 Report Generated at: {report_path}")
        print("-" * 40)
        with open(report_path, "r") as f:
            print(f.read())
        print("-" * 40)
    else:
        print("\n❌ Report NOT found!")

if __name__ == "__main__":
    asyncio.run(main())
