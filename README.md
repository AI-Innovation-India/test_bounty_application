# TestBounty - AI-Powered Autonomous Testing Platform

TestBounty is an autonomous AI testing platform that writes, executes, and debugs your tests automatically. Just provide a URL and let the AI handle the rest.

## Features

- **AI Test Generation** - Automatically generates comprehensive test cases from your application URL
- **Security Testing** - OWASP Top 10 coverage including SQL injection, XSS, and CSRF detection
- **Self-Healing Scripts** - AI automatically fixes broken selectors and adapts to UI changes
- **Visual Regression** - Pixel-perfect screenshot comparison to catch visual bugs
- **Video Recording** - Full video capture of every test run for easy debugging
- **Smart Reports** - Detailed HTML reports with actionable insights and metrics

## Architecture

```
testbounty/
├── testbounty_agent/     # Python backend (FastAPI + AI Agent)
│   ├── src/
│   │   ├── agents/       # LangGraph orchestration
│   │   ├── services/     # LLM, code analysis, reporting
│   │   └── testing_engine/  # Playwright browser automation
│   └── start_api.py      # API server entry point
│
└── testbounty_web/       # Next.js frontend
    └── src/
        ├── app/          # Pages (App Router)
        ├── components/   # React components
        └── lib/          # API client
```

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key (or OpenAI/Anthropic)

### Backend Setup

```bash
cd testbounty_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Set environment variable
export GOOGLE_API_KEY=your_api_key_here

# Start the API server
python start_api.py
```

The backend runs on http://localhost:8000

### Frontend Setup

```bash
cd testbounty_web

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend runs on http://localhost:3000

## Usage

1. Open http://localhost:3000 in your browser
2. Navigate to "Create Tests" page
3. Enter your application URL
4. AI will analyze and generate test cases
5. Run tests and view results with video recordings

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/runs` | GET | List all test runs |
| `/api/runs` | POST | Create new test run |
| `/api/runs/{id}` | GET | Get run details |
| `/api/runs/{id}` | DELETE | Delete a run |
| `/api/test-suites` | GET | List test suites |
| `/api/test-suites` | POST | Create test suite |
| `/api/test-suites/{id}/run` | POST | Execute test suite |
| `/api/monitors` | GET/POST | Manage monitors |

## Tech Stack

### Backend
- FastAPI - API framework
- LangGraph - AI agent orchestration
- Playwright - Browser automation
- Google Gemini / OpenAI / Anthropic - LLM providers

### Frontend
- Next.js 16 - React framework
- Tailwind CSS - Styling
- Lucide React - Icons

## Environment Variables

### Backend (.env)
```
GOOGLE_API_KEY=your_google_api_key
# OR
OPENAI_API_KEY=your_openai_api_key
# OR
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
