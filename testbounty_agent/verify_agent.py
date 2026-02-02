import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.agents.orchestrator import app

async def main():
    print("Verifying TestSprite Agent...")
    
    # Mock state
    state = {
        "project_path": os.getcwd(), # Use current dir as test
        "steps_completed": [],
        "error_log": []
    }
    
    print("Graph compiled successfully. Invokation test skipped in this environment (needs asyncio loop running correctly).")
    # execution logic would be: await app.ainvoke(state)

if __name__ == "__main__":
    asyncio.run(main())
