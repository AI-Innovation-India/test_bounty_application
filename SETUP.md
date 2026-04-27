# TestBounty — Complete Setup Guide (Office / Fresh Machine)

Follow every step in order. Each section must be completed before moving to the next.

---

## Step 1 — Install Prerequisites

### 1.1 Python 3.11

1. Open browser → go to **https://www.python.org/downloads/release/python-3110/**
2. Download **Windows installer (64-bit)**
3. Run the installer
4. **IMPORTANT:** On the first screen, check the box **"Add Python to PATH"** before clicking Install
5. Click **"Install Now"**
6. After install, open **Command Prompt** and verify:

```cmd
python --version
```

Expected output: `Python 3.11.x`

> **If you see "python is not recognized":** You forgot to check "Add to PATH". Re-run the installer → Modify → check "Add Python to environment variables".

---

### 1.2 Node.js 18+

1. Go to **https://nodejs.org/en/download**
2. Download the **LTS version** (Windows Installer .msi, 64-bit)
3. Run the installer — accept all defaults
4. Verify in Command Prompt:

```cmd
node --version
npm --version
```

Expected: `v18.x.x` or higher for node, `9.x.x` or higher for npm.

---

### 1.3 Git

1. Go to **https://git-scm.com/download/win**
2. Download and run the installer
3. Accept all defaults
4. Verify:

```cmd
git --version
```

Expected: `git version 2.x.x`

---

## Step 2 — Clone the Repository

Open **Command Prompt** or **PowerShell**:

```cmd
cd C:\Users\<your-username>\Documents

git clone https://github.com/AI-Innovation-India/test_bounty_application.git

cd test_bounty_application
```

> Replace `<your-username>` with your actual Windows username.

---

## Step 3 — Backend Setup (Python)

All commands in this section are run from inside the `testbounty_agent` folder.

```cmd
cd testbounty_agent
```

### 3.1 Create a virtual environment

```cmd
python -m venv venv
```

This creates a `venv` folder. You will activate it every time you work on the backend.

### 3.2 Activate the virtual environment

```cmd
venv\Scripts\activate
```

Your prompt will change to show `(venv)` at the start. This means it is active.

> **Note:** You must run this every time you open a new terminal window before starting the backend.

### 3.3 Upgrade pip

```cmd
python -m pip install --upgrade pip
```

### 3.4 Install Python dependencies

```cmd
pip install fastapi uvicorn python-dotenv playwright anthropic openai langchain-anthropic langchain-openai pydantic requests beautifulsoup4 jinja2 aiohttp python-multipart
```

> **If you get a proxy/SSL error** (common in corporate networks):
> ```cmd
> pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org fastapi uvicorn python-dotenv playwright anthropic openai langchain-anthropic langchain-openai pydantic requests beautifulsoup4 jinja2 aiohttp python-multipart
> ```

### 3.5 Install Playwright browsers

```cmd
playwright install chromium
```

> This downloads the Chromium browser that the AI agents use. It is ~150 MB.

> **If this hangs or fails on corporate network:**
> ```cmd
> playwright install --with-deps chromium
> ```

---

## Step 4 — Configure Environment Variables (.env)

The backend needs API keys to call the AI model. You must create a `.env` file inside the `testbounty_agent` folder.

### 4.1 Create the .env file

In Command Prompt (still in `testbounty_agent` folder):

```cmd
notepad .env
```

Notepad will ask if you want to create a new file — click **Yes**.

### 4.2 Paste your configuration

Copy one of the sections below depending on which AI service your office uses:

---

**Option A — Azure OpenAI (recommended for office)**

```env
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01
```

> Where to find these values:
> - Go to **Azure Portal** → Azure OpenAI resource → **Keys and Endpoint**
> - `AZURE_OPENAI_ENDPOINT` = the Endpoint URL (ends with `.openai.azure.com/`)
> - `AZURE_OPENAI_API_KEY` = Key 1 or Key 2
> - `AZURE_OPENAI_DEPLOYMENT` = the model deployment name you created (e.g. `gpt-4o`)

---

**Option B — Anthropic Claude**

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

---

**Option C — OpenAI**

```env
OPENAI_API_KEY=sk-your-key-here
```

---

**Save the file** (Ctrl+S) and close Notepad.

### 4.3 Verify the file was created

```cmd
dir .env
```

You should see the `.env` file listed.

---

## Step 5 — Frontend Setup (Node.js)

Open a **second** Command Prompt window and navigate to the frontend folder:

```cmd
cd C:\Users\<your-username>\Documents\test_bounty_application\testbounty_web
```

Install frontend dependencies:

```cmd
npm install
```

> This installs ~500 packages and takes 2–5 minutes. You will see a progress bar.

> **If you get an npm error on corporate network:**
> ```cmd
> npm install --legacy-peer-deps
> ```

---

## Step 6 — Running the Application

You need **two terminal windows open at the same time** — one for the backend, one for the frontend.

### Terminal 1 — Start the Backend

```cmd
cd C:\Users\<your-username>\Documents\test_bounty_application\testbounty_agent

venv\Scripts\activate

python -m uvicorn src.api_server:app --host 0.0.0.0 --port 8001 --reload
```

Wait until you see:
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### Terminal 2 — Start the Frontend

```cmd
cd C:\Users\<your-username>\Documents\test_bounty_application\testbounty_web

npm run dev
```

Wait until you see:
```
▲ Next.js 14.x.x
- Local:   http://localhost:3000
```

### Open the App

Open your browser and go to: **http://localhost:3000**

---

## Step 7 — Quick Test (Verify Everything Works)

1. In the browser, click **Autonomous** in the left sidebar
2. Paste any public URL, e.g.: `https://www.google.com`
3. Click **Launch Agents**
4. A Chromium browser window should appear
5. The Activity log on the right should show events within 5–10 seconds
6. The AI will analyze the page and show findings

If you see activity in the log and a screenshot in the Live View — **setup is complete**.

---

## Stopping the Application

- In Terminal 1: Press `Ctrl + C`
- In Terminal 2: Press `Ctrl + C`

---

## Daily Workflow (Starting Again After First Setup)

Every day when you want to use TestBounty:

**Terminal 1 (Backend):**
```cmd
cd C:\Users\<your-username>\Documents\test_bounty_application\testbounty_agent
venv\Scripts\activate
python -m uvicorn src.api_server:app --host 0.0.0.0 --port 8001 --reload
```

**Terminal 2 (Frontend):**
```cmd
cd C:\Users\<your-username>\Documents\test_bounty_application\testbounty_web
npm run dev
```

Open **http://localhost:3000**

---

## Pulling Latest Changes (After Updates)

When you're told a new version is available:

```cmd
cd C:\Users\<your-username>\Documents\test_bounty_application

git pull origin main
```

Then restart both terminals.

---

## Troubleshooting

### "python is not recognized"
Python is not in your PATH. Re-run the Python installer and check "Add to PATH".

### "venv\Scripts\activate is not recognized"
You are in the wrong folder. Make sure you are in `testbounty_agent`, not the root folder.

### "Module not found: anthropic / openai"
The venv is not activated. Run `venv\Scripts\activate` first, then re-run the pip install command.

### Backend starts but shows errors about missing modules
```cmd
pip install fastapi uvicorn python-dotenv playwright anthropic openai langchain-anthropic langchain-openai pydantic requests beautifulsoup4 jinja2 aiohttp python-multipart
```

### "playwright install" hangs / fails
Your corporate firewall may be blocking the download. Try:
```cmd
set HTTPS_PROXY=http://your-proxy:port
playwright install chromium
```
Ask your IT team for the proxy address.

### Frontend shows "Failed to fetch" or blank page
- Make sure the backend is running (Terminal 1 shows no errors)
- Check that the URL is `http://localhost:3000` (not https)
- Refresh the page

### Port 8001 already in use
```cmd
netstat -ano | findstr :8001
taskkill /PID <pid_number> /F
```
Then restart the backend.

### Port 3000 already in use
```cmd
netstat -ano | findstr :3000
taskkill /PID <pid_number> /F
```
Then restart the frontend.

### Azure OpenAI returns "DeploymentNotFound"
Your `AZURE_OPENAI_DEPLOYMENT` name in `.env` doesn't match the deployment name in Azure Portal. Go to **Azure OpenAI Studio → Deployments** and copy the exact name.

### Azure OpenAI returns "401 Unauthorized"
Your `AZURE_OPENAI_API_KEY` is wrong. Go to **Azure Portal → Azure OpenAI → Keys and Endpoint** and copy Key 1 again.

### AI agents run but "No test flows generated"
Your LLM API key is not set. Open `testbounty_agent\.env` and verify the key is correct. Then restart the backend.

---

## Folder Structure Reference

```
test_bounty_application/
│
├── testbounty_agent/           ← Python backend
│   ├── src/
│   │   ├── api_server.py       ← Main API (runs on port 8001)
│   │   ├── agents/
│   │   │   ├── autonomous_explorer.py   ← Autonomous crawl + agent orchestration
│   │   │   ├── feature_test_agent.py    ← Claude/Azure/OpenAI page analysis
│   │   │   └── scenario_writer.py       ← Saves generated test scenarios
│   │   └── utils/
│   │       └── page_intelligence.py     ← DOM analysis helpers
│   ├── venv/                   ← Python virtual environment (created by you)
│   ├── runs.json               ← Test run history
│   ├── test_plans.json         ← Generated test plans
│   ├── test_suites.json        ← Saved test suites
│   └── .env                    ← Your API keys (never commit this file)
│
├── testbounty_web/             ← Next.js frontend
│   ├── src/app/
│   │   ├── autonomous/page.tsx ← Autonomous testing UI
│   │   ├── scenarios/page.tsx  ← Scenario builder
│   │   └── testing/page.tsx    ← Test runs history
│   └── src/lib/api.ts          ← API client
│
├── README.md                   ← Quick start overview
└── SETUP.md                    ← This file
```

---

## Feature Overview

| Feature | Where | What it does |
|---|---|---|
| **Autonomous Testing** | Sidebar → Autonomous | Give any URL. AI launches a browser, crawls all pages, spawns one agent per feature (Tracking, Reports, Dashboard, etc.), interacts with UI, generates test scenarios automatically |
| **Scenario Builder** | Sidebar → Scenarios | Build and run individual test scenarios. AI can generate scenarios from your documentation |
| **Test Runs** | Sidebar → Test Runs | History of all test executions with pass/fail details and video recordings |
| **Test Suites** | Sidebar → Test Suites | Group scenarios into suites for regression testing. Auto-generated suites appear here after Autonomous runs |
| **Monitoring** | Sidebar → Monitoring | Uptime monitoring for your application URLs |

---

*Last updated: 2026-04-27*
