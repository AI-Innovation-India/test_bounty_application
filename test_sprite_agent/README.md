# TestSprite: Autonomous AI Quality Assurance Agent

> **"Zero-Code, Full-Cycle QA Automation powered by Generative AI."**

TestSprite is an advanced AI agent designed to autonomously plan, write, and execute end-to-end (E2E) tests for web applications. By simply providing a target URL, TestSprite acts as a virtual QA Engineer, analyzing the application, generating comprehensive test strategies, and engaging in self-healing code execution—all without human intervention.

---

## 🚀 Mission & Goals

Our goal is to **eliminate the bottleneck of manual testing** in modern software development.

### **What We Are Achieving:**
1.  **Autonomous Test Planning**: Converting a simple URL into a structured Product Requirement Document (PRD) and detailed Test Plans (Functional, Edge Case, Security).
2.  **Instant Code Generation**: Writing production-grade Playwright (Python) scripts on the fly.
3.  **Visual Verification**: Executing tests in a headless browser while recording video and capturing logs for human review.
4.  **Self-correction**: If a test fails due to a script error, the Agent analyzes the stack trace and attempts to fix its own code.

---

## ✨ Key Features

### 🧠 Intelligent Planning
- **Context Awareness**: Scrapes the target website to understand user flows.
- **Strategy Generation**: Creates distinct plans for:
    - **Functional Testing**: Happy paths (Login, Signup, Checkout).
    - **Edge Case Testing**: Invalid inputs, boundary conditions.
    - **Security Testing**: SQL Injection, XSS, IDOR checks (OWASP Top 10).

### ⚡ Autonomous Execution Engine
- **Powered by Playwright**: Uses industry-standard browser automation.
- **Real-time Feedback**: Streams execution logs (`[PASSED]`, `[FAILED]`) directly to the UI.
- **Video Recording**: Captures every test run for visual debugging.

### 🖥️ Modern "Cyberpunk" UI
- Built with **Next.js 14** and **Tailwind CSS**.
- Features a dark, high-contrast interface for clarity.
- **Interactive Chat**: Talk to the Agent to ask questions about the test results or request new scenarios.

---

## 🛠️ Technology Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Frontend** | Next.js 14, React, Tailwind | User Dashboard & Execution/Chat UI |
| **Backend** | FastAPI (Python) | API Server, Job Management, Artifact Serving |
| **AI / LLM** | LangChain, LangGraph, Google Gemini | Reasoning, Planning, Code Generation |
| **Automation** | Playwright (Python) | Browser Control & Video Recording |
| **Protocol** | Model Context Protocol (MCP) | (Optional) Integration with IDEs |

---

## 📦 Project Structure

```bash
/test_sprite_agent         # 🧠 The Brain (Backend)
├── src/
│   ├── agents/           # LangGraph workflows (Plan -> Code -> Run)
│   ├── services/         # LLM & Playwright services
│   ├── mcp_server/       # MCP Server implementation
│   └── api_server.py     # FastAPI Entrypoint
├── demo_target/          # Simple target app for self-testing
└── runs.json             # Local database of test runs

/test_sprite_web          # 💻 The Face (Frontend)
├── src/app/              # Next.js App Router pages
├── components/           # UI Components (Sidebar, CodeViewer)
└── lib/api.ts            # Backend API client
```

---

## 🚦 Getting Started

### 1. Backend Setup
Navigate to the agent directory and start the API server:
```bash
cd test_sprite_agent

# Install dependencies (requires Python 3.10+)
pip install -e .
playwright install

# Create .env with your API Key
echo "GOOGLE_API_KEY=your_key_here" > .env

# Start the Server
python -m src.api_server
```
*Server runs on `http://localhost:8000`*

### 2. Frontend Setup
Navigate to the web directory and start the UI:
```bash
cd test_sprite_web
npm install
npm run dev
```
*UI runs on `http://localhost:3000`*

---

## 🔮 Future Roadmap
- [ ] **Cloud Execution**: Integrate with BrowserStack/SauceLabs.
- [ ] **CI/CD Integration**: GitHub Actions plugin for PR checks.
- [ ] **Visual Regression**: AI-powered screenshot comparison.
- [ ] **Mobile Testing**: Appium integration for mobile apps.

---
*Built with ❤️ by the TestSprite Team.*
