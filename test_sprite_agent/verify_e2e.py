import requests
import time
import json

API_URL = "http://localhost:8000/api"
TARGET = "https://www.testsprite.com"

def run_test():
    print(f"🚀 Starting test run against {TARGET}...")
    try:
        # Start Run
        resp = requests.post(f"{API_URL}/run", json={"target_url": TARGET})
        if resp.status_code != 200:
            print(f"❌ Failed to start run: {resp.text}")
            return
            
        data = resp.json()
        run_id = data["run_id"]
        print(f"✅ Run started! ID: {run_id}")
        print("⏳ Waiting for agents...")
        
        # Poll Status
        while True:
            status_resp = requests.get(f"{API_URL}/run/{run_id}")
            run_data = status_resp.json()
            status = run_data["status"]
            steps = run_data.get("steps", [])
            
            print(f"   Status: {status.upper()} | Steps: {steps}")
            
            if status in ["completed", "failed"]:
                break
            
            time.sleep(3)
            
        print(f"\n🏁 Run finished with status: {status}")
        
        if status == "completed":
            print("🔍 Verifying Artifacts...")
            # Check Video
            try:
                vid_resp = requests.get(f"{API_URL}/run/{run_id}/artifacts/video", stream=True)
                if vid_resp.status_code == 200:
                    print(f"   ✅ Video artifact found! ({len(vid_resp.content)} bytes)")
                else:
                    print(f"   ❌ Video artifact missing (Status {vid_resp.status_code})")
            except Exception as e:
                 print(f"   ❌ Failed to check video: {e}")
                 
            print(f"\n👉 VIEW RESULTS: http://localhost:3000/run/{run_id}")
            
    except Exception as e:
        print(f"💥 Verification Script Failed: {e}")

if __name__ == "__main__":
    run_test()
