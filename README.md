# House Helper

A multi-agent desktop assistant. Currently ships with a **Job Agent** that automates job searching, resume building, and application tracking.

> **Status:** Skeleton — backend is functional with 234 tests, frontend has full UI, but LLM integration and actual form-filling are not yet connected. Everything runs on local algorithms.

## Job Agent

An autonomous job application agent that searches, matches, generates tailored resumes, and tracks applications. Works in three modes:

- **No LLM** — local algorithms (TF-IDF, skill matching, template resumes). Works offline, zero cost.
- **Offline LLM** — Ollama/local models for better generation without cloud.
- **Online LLM** — Claude, OpenAI, or HuggingFace for best quality.

### Features

| Feature | Status |
|---------|--------|
| Import resume (DOCX/PDF drag-and-drop) | Working |
| Knowledge bank (experiences, skills, education, projects) | Working |
| Paste job links (auto-fetch + JSON-LD extraction) | Working |
| Job matching (skill overlap + TF-IDF) | Working |
| Resume generation (template-based) | Working |
| Cover letter generation (template-based) | Working |
| Export PDF / DOCX / TXT / Markdown | Working |
| Application tracker (kanban board) | Working |
| Auto-search (RemoteOK API) | Working |
| Auto-search (JSearch, Adzuna) | Needs free API key |
| Pipeline animation ("Do the Magic") | Working (demo) |
| ATS resume validation | Working |
| Match calibration (rate matches to tune scoring) | Working |
| Token budget management | Backend ready |
| LLM-powered resume/cover letter | Backend ready, not connected |
| Actual form filling (Playwright) | Not built |
| Offline model download | Not built |

### Architecture

```
Tauri 2.0 Desktop Shell
├── React + TypeScript + Tailwind + shadcn/ui (frontend)
├── Python + FastAPI (backend sidecar)
│   ├── Coordinator (agent routing)
│   ├── Job Agent
│   │   ├── Services: job_parser, job_matcher, resume, cover_letter,
│   │   │   auto_search, auto_apply, knowledge, tracker
│   │   ├── Repositories: knowledge, job, resume, cover_letter,
│   │   │   application, search, apply_queue, token, evidence
│   │   └── Prompts: 5 prompt templates (ready for LLM)
│   └── Shared
│       ├── algorithms/ (TF-IDF, skill matching, semantic, resume builder)
│       ├── job_boards/ (JSearch API, Adzuna API, RemoteOK API)
│       ├── scraping/ (URL fetcher, HTML extractor, resume parser)
│       ├── export/ (PDF, DOCX, TXT, Markdown)
│       ├── llm/ (Claude, OpenAI, Ollama, HuggingFace providers)
│       ├── calibration/ (weighted scoring, anonymized export)
│       ├── token_budget.py
│       └── ats_optimizer.py + ats_rules.json
└── SQLite (21 tables, WAL mode, auto-migration)
```

### Quick Start

```bash
# Backend
cd backend
python3 -m venv ../.venv
source ../.venv/bin/activate
pip install -e ".[dev]"
uvicorn main:app --reload --port 8040

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

### Job Board API Keys (optional)

RemoteOK works with zero setup. For more sources:

```bash
# JSearch — searches LinkedIn, Indeed, Glassdoor via RapidAPI
# Free: 500 requests/month at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
export RAPIDAPI_KEY="your-key"

# Adzuna — free: 250 requests/day at https://developer.adzuna.com
export ADZUNA_APP_ID="your-id"
export ADZUNA_APP_KEY="your-key"
```

### Tests

```bash
source .venv/bin/activate

# All tests (excluding network)
python -m pytest tests/ -m "not network"

# With network tests (needs internet)
python -m pytest tests/ -m network

# Frontend tests
cd frontend && npm run test:run
```

### Project Structure

```
house-helper/
├── backend/           71 Python files, 234 tests
├── frontend/          30 TypeScript/React files, 21 tests
├── requirements/      v1 + v2 requirements docs
├── architecture/      v1 + v2 architecture docs
├── reports/           Skill run reports
├── skills-feedback.md 60 lessons learned (useful for any project)
└── pyproject.toml
```

## Roadmap

- [ ] Connect LLM for AI-powered resume/cover letter generation
- [ ] Playwright browser automation for actual form filling
- [ ] Offline model download (Sentence Transformers, spaCy)
- [ ] ATS validation UI in resume builder
- [ ] Tauri desktop packaging
- [ ] More job board plugins
- [ ] Background scheduled search

## Skills Feedback

This project was built using an agent-toolkit with `/requirements`, `/architecture`, `/implementation`, and `/evaluate` skills. `skills-feedback.md` contains 60 battle-tested lessons applicable to any software project — covering requirements gathering, architecture decisions, implementation patterns, and UI/UX. Worth reading.

## License

MIT
