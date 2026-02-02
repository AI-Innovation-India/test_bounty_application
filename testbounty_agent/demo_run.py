import asyncio
import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from src.agents.orchestrator import app

async def main():
    target_path = os.path.abspath("demo_target")
    print(f"\n🚀 STARTING TESTSPRITE AGENT DEMO")
    print(f"Target Project: {target_path}\n")

    initial_state = {
        "project_path": target_path,
        "steps_completed": [],
        "error_log": []
    }

    # Run the graph
    # We use stream to see steps happening
    async for event in app.astream(initial_state):
        for key, value in event.items():
            print(f"✅ Completed Step: {key}")
            if "error_log" in value and value["error_log"]:
                print(f"❌ Errors: {value['error_log']}")

    print("\n✨ DEMO COMPLETE")
    
    # Verify artifacts
    report_path = Path(target_path) / "testsprite_tests" / "reports" / "report.md"
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
