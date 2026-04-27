# TestBounty — AI-Powered Testing Platform

An autonomous AI testing platform that crawls any web application, discovers features, and runs intelligent test scenarios with real browsers.

---

## Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org/downloads |
| Node.js | 18+ | https://nodejs.org |
| Git | any | https://git-scm.com |

---

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd game_development
```

### 2. Backend setup

```bash
cd testbounty_agent

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium firefox webkit
```

> **Windows only:** If `playwright install` hangs, run:
> ```bash
> playwright install --with-deps chromium
> ```

### 3. Frontend setup

```bash
cd testbounty_web
npm install
```

---

## Environment Variables

### Backend — `testbounty_agent/.env`

Create a `.env` file inside `testbounty_agent/`:

```env
# Required — get from https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...

# Optional — Azure OpenAI alternative
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### Frontend — `testbounty_web/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8001
```

---

## Running the Application

Open **two terminals**:

**Terminal 1 — Backend:**

```bash
cd testbounty_agent

# Windows
venv\Scripts\activate

# Mac/Linux
# source venv/bin/activate

python -m uvicorn src.api_server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 — Frontend:**

```bash
cd testbounty_web
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Quick Start Guide

### Option 1: Autonomous Testing (any website)

1. Click **Autonomous** in the sidebar
2. Paste any URL (e.g., `https://yourapp.com`)
3. Set **Max Pages** (default 25)
4. Click **Start Exploration**
5. A real browser window opens — the AI explores automatically
6. **If login is required:** log in manually in the visible browser, then click **"Continue exploring"** in the yellow prompt card
7. AI discovers features and spawns specialist agents per feature (Landing Page Agent, Login Agent, Dashboard Agent, etc.)
8. View live screenshots, agent activity, and findings in real time
9. Click **Stop** when done — the browser stays open for manual inspection

### Option 2: AI Scenario Builder

1. Navigate to **Scenarios**
2. Click the **Train AI** tab → paste your app's documentation or test requirements
3. Click **Parse Document** — AI generates structured test scenarios
4. Switch to **Run Controls** → click **Run All Scenarios**
5. Results appear with self-healing selector info (auto-fixed broken locators)

### Option 3: Regression Suites

1. Go to **Test Suites** → create a named suite
2. Add scenarios to the suite
3. Run on demand or via CI/CD (see below)

---

## Project Structure

```
game_development/
├── testbounty_agent/                    # Python backend (FastAPI)
│   ├── src/
│   │   ├── api_server.py                # All API & WebSocket endpoints
│   │   ├── agents/
│   │   │   ├── autonomous_explorer.py   # Autonomous crawl & agent orchestration
│   │   │   ├── explorer.py              # Scenario-based page explorer
│   │   │   ├── module_agent.py          # Per-feature AI test agent
│   │   │   └── session_recorder.py      # Record/replay sessions
│   │   └── utils/
│   │       └── page_intelligence.py     # DOM analysis helpers
│   ├── requirements.txt
│   └── .env                             # Your API keys (not committed)
│
├── testbounty_web/                      # Next.js 14 frontend
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx                 # Dashboard
│   │   │   ├── autonomous/page.tsx      # Autonomous testing UI
│   │   │   ├── scenarios/page.tsx       # Scenario builder + AI training
│   │   │   ├── testing/page.tsx         # Test runs
│   │   │   ├── test-lists/page.tsx      # Test suites
│   │   │   └── monitoring/page.tsx      # Uptime monitoring
│   │   ├── components/
│   │   │   └── Sidebar.tsx
│   │   └── lib/
│   │       └── api.ts                   # API + WebSocket client
│   ├── package.json
│   └── .env.local                       # Frontend env vars
│
└── README.md
```

---

## CI/CD Integration

Export test results as JUnit XML for CI pipelines:

```bash
# Trigger a test suite run
curl -X POST http://localhost:8001/api/ci/trigger \
  -H "Content-Type: application/json" \
  -d '{"suite_id": "your-suite-id"}'
```

Pipeline config examples:
- GitHub Actions: `.github/workflows/testbounty.yml`
- Azure Pipelines: `azure-pipelines.yml`

---

## Common Issues

### Backend port already in use

```bash
# Windows
netstat -ano | findstr :8001
taskkill /PID <pid> /F
```

### `ANTHROPIC_API_KEY` not found

- Ensure `.env` is inside `testbounty_agent/` (not the repo root)
- Key must start with `sk-ant-`

### Playwright browser not found

```bash
cd testbounty_agent
venv\Scripts\activate      # Windows
playwright install chromium
```

### Autonomous explorer stuck on "Waiting for browser..."

- Wait ~5 seconds for WebSocket to connect
- If still blank, refresh the page and click **Start** again

### Site behind SSO / login wall

- The AI will detect it can only see the login page
- A yellow prompt card appears: **"Please log in manually, then click Continue"**
- Log in through the visible browser window, then click the button — AI continues with your authenticated session

### Frontend shows CORS error

- Verify backend is running: `curl http://localhost:8001/api/plans`
- Check `testbounty_web/.env.local` has `NEXT_PUBLIC_API_URL=http://localhost:8001`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | Python 3.11, FastAPI, uvicorn |
| AI | Anthropic Claude (claude-sonnet-4-6) |
| Browser Automation | Playwright (Chromium, Firefox, WebKit) |
| Real-time | WebSockets |
| Test Export | JUnit XML |

---

## License

MIT
