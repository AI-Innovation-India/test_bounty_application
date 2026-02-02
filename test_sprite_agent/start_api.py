import uvicorn
import sys
import os
from dotenv import load_dotenv

load_dotenv()

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.api_server import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
