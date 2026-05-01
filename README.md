<div align="center">

# Panini

[![Tests](https://github.com/jvalin17/house-helper/actions/workflows/test.yml/badge.svg)](https://github.com/jvalin17/house-helper/actions/workflows/test.yml)
[![Download](https://img.shields.io/badge/download-latest-7b2ff7?style=flat&logo=github)](https://github.com/jvalin17/house-helper/releases/latest)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Tauri](https://img.shields.io/badge/Tauri-2-24C8D8?logo=tauri&logoColor=white)
![Tests](https://img.shields.io/badge/tests-781%2B-brightgreen)

A multi-agent AI assistant — named after [Panini](https://en.wikipedia.org/wiki/P%C4%81%E1%B9%87ini), the ancient Sanskrit scholar who created the first formal rule system.

</div>

---

## Agents

| Agent | Description | Status |
|-------|-------------|--------|
| **Jobsmith** | Search jobs, score matches, generate tailored resumes, track applications | Active |

---

## Download the Desktop App

No Python or Node.js needed. Just download, install, and open.

| Platform | Download | Notes |
|----------|----------|-------|
| **macOS (Apple Silicon)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_aarch64.dmg) | M1 / M2 / M3 / M4 |
| **macOS (Intel)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_x64.dmg) | Older Intel Macs |
| **Windows** | [Panini.msi](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_x64_en-US.msi) | Windows 10+ (64-bit) |
| **Linux** | [panini.deb](https://github.com/jvalin17/house-helper/releases/latest/download/panini_0.1.0_amd64.deb) | Debian/Ubuntu |

### Windows Installation

1. Download `Panini_0.1.0_x64_en-US.msi`
2. Double-click to install (Windows may show "Windows protected your PC" — click **More info** → **Run anyway**)
3. Open **Panini** from the Start menu
4. Go to **Settings** → select an AI provider → enter API key → **Save Provider**
5. You're ready — go to **Superpower Lab** to import your resume

### macOS Installation

1. Download the `.dmg` for your chip
2. Open the DMG and drag Panini to Applications
3. If you see "app is damaged": run `xattr -cr "/Applications/Panini.app"` in Terminal, then open normally

---

## Run from Source

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
# Prerequisites: Python 3.12, Node.js 18+
git clone https://github.com/jvalin17/house-helper.git
cd house-helper
chmod +x setup.sh run.sh
./setup.sh   # installs everything
./run.sh     # starts backend + frontend
```

Open **http://localhost:5173**
</details>

<details>
<summary><strong>Windows (step by step)</strong></summary>

**Prerequisites:**
- [Python 3.12](https://www.python.org/downloads/) — check "Add Python to PATH" during install
- [Node.js 18+](https://nodejs.org/) — LTS version recommended

**Setup (run once in PowerShell):**
```powershell
git clone https://github.com/jvalin17/house-helper.git
cd house-helper

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -e ".[dev]"
pip install fastapi uvicorn python-dotenv httpx anthropic openai
pip install rapidfuzz python-docx PyMuPDF python-multipart
pip install weasyprint markdown beautifulsoup4 trafilatura
pip install pyjwt bcrypt cryptography
pip install "numpy<2" "transformers<5" "sentence-transformers<5"

# Install frontend dependencies
cd frontend
npm install
cd ..

# Create config file
copy .env.example .env
```

**Run (every time):**
```powershell
# Terminal 1 — Backend
cd house-helper
.venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --port 8040 --reload

# Terminal 2 — Frontend
cd house-helper\frontend
npm run dev
```

Open **http://localhost:5173**
</details>

---

## First-Time Setup

1. **Connect an AI provider** — Go to **Settings** → select Claude, OpenAI, DeepSeek, etc. → enter API key → **Save Provider**
2. **Import your resume** — Go to **Superpower Lab** → drag-and-drop your DOCX/PDF/TXT resume
3. **Search for jobs** — Go to **Job Search** → enter job title → **Scout Jobs**

The app works without AI (free algorithmic matching + template generation), but AI adds deeper analysis and better tailoring.

---

## Features

### Knowledge Bank

| Feature | Description |
|---------|-------------|
| **Resume Import** | Drag-and-drop DOCX/PDF/TXT. Extracts experiences, skills, education, projects |
| **DOCX Format Preservation** | Generated resumes keep your original fonts, bold, colors, spacing |
| **Extract from Link** | Paste a URL (GitHub, LinkedIn, portfolio) → extract skills or experiences |
| **Experience Extraction** | AI extracts work experiences and project details from any webpage (requires LLM) |
| **Category Picker** | Save extracted items as: Experience, Project, Volunteering, Education, Certification, or Other |
| **Inline Edit** | Edit any skill, experience, education, or project directly. X button to delete skills |
| **Smart Merge** | Multiple imports merge intelligently — no duplicates |
| **Templates** | Up to 5 resume templates with format preview |

### Job Search

| Feature | Description |
|---------|-------------|
| **Multi-Source Search** | JSearch (LinkedIn/Indeed/Glassdoor), Adzuna, RemoteOK |
| **Custom Sources** | Add your own job board API endpoints (up to 5) |
| **Source Toggles** | Enable/disable individual sources with on/off switches |
| **Algorithmic Matching** | Free scoring: skills overlap, TF-IDF, semantic similarity, experience years |
| **AI Evaluation** | Deep LLM analysis per job (requires AI provider) |
| **Job Filters** | Need sponsorship, Lack clearance, Skip internships |
| **Match Calibration** | Rate jobs to improve scoring — weights adjust to your preferences |

### Resume Generation

| Feature | Description |
|---------|-------------|
| **AI Analysis** | Shows match %, strengths, gaps, suggested improvements |
| **Suggestion Control** | Accept/reject each suggestion. Flag incorrect ones — they won't return |
| **Custom Instructions** | "Focus on backend", "Target mid-level", "Show only 6 years" |
| **DOCX Surgery** | Preserves your exact resume formatting — fonts, colors, bullet styles |
| **Export** | PDF, DOCX, Markdown, Text |
| **Saved Resumes** | Curate up to 5 versions (auto-named `resume_26_v1`) |

### Settings & Budget

| Feature | Description |
|---------|-------------|
| **9 AI Providers** | Claude, OpenAI, DeepSeek, Gemini, Grok, OpenRouter, HuggingFace, Custom, Ollama |
| **Daily Budget Limit** | Set max spend per day. AI pauses with confirmation when limit reached |
| **Cost Tracking** | Real-time: today's spend, all-time spend, per-feature breakdown |
| **Hot Reload** | Change provider/model/key — applied instantly, no restart |
| **Check for Updates** | Built-in update checker in Settings |

---

## AI Providers

| Provider | Model | ~Cost/Resume | Get Key |
|----------|-------|-------------|---------|
| Claude | Sonnet 4 | $0.017 | [console.anthropic.com](https://console.anthropic.com/) |
| OpenAI | GPT-4o | $0.013 | [platform.openai.com](https://platform.openai.com/) |
| DeepSeek | V3 | $0.001 | [platform.deepseek.com](https://platform.deepseek.com/) |
| Gemini | 2.0 Flash | $0.001 | [aistudio.google.com](https://aistudio.google.com/) |
| Grok | Grok-2 | $0.011 | [console.x.ai](https://console.x.ai/) |
| OpenRouter | 100+ models | varies | [openrouter.ai](https://openrouter.ai/) |
| Custom | Any endpoint | varies | Your provider |
| Ollama | Local models | Free | [ollama.com](https://ollama.com/download) |

**No AI mode** — everything works without a provider. Free algorithmic matching + template generation.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12 &bull; FastAPI &bull; SQLite (WAL) |
| Frontend | React 19 &bull; TypeScript &bull; Vite &bull; Tailwind 4 &bull; shadcn/ui |
| Desktop | Tauri 2 (sidecar backend) |
| AI | Claude &bull; OpenAI &bull; DeepSeek &bull; Grok &bull; Gemini &bull; OpenRouter &bull; Ollama |
| Resume | python-docx &bull; WeasyPrint &bull; PyMuPDF |
| Testing | pytest &bull; vitest &bull; GitHub Actions CI |

---

## Testing

```bash
./test.sh                        # all tests
cd backend && python -m pytest   # backend only
cd frontend && npx vitest run    # frontend only
```

**781+ tests** (583 backend + 198 frontend) covering DOCX surgery, knowledge bank, budget enforcement, LLM providers, auth, job filtering, inline editing, category saving, experience extraction, and full workflow integration.

---

## Known Limitations

- **Apply & Track** — not yet functional. Download resume and apply manually.
- **Auto-apply** — search works, browser form-filling (Playwright) not built yet.
- **Ollama** — PDF import only. Too slow for analysis/generation.
- **Cost tracking** — word-count heuristics (~30% margin).

## Roadmap

- [ ] Browser form filling (Playwright auto-apply)
- [ ] Prompt caching (~30% AI cost reduction)
- [ ] Auto-update within the app
- [ ] Docker deployment
- [ ] OAuth (Google/GitHub login)

---

---

## Built With

Developed using [Claude Code](https://claude.ai/code) with [agent-toolkit](https://github.com/jvalin17/agent-toolkit) skills:

| Skill | Purpose |
|-------|---------|
| `/requirements` | Scoped features, user stories, 3-mode capability tables (no LLM / offline / online) |
| `/architecture` | Tech stack decisions, database schema, API design, plugin patterns |
| `/implementation` | TDD cycles (test first → implement → verify), skeleton-then-slabs approach |
| `/evaluate` | Graded output against original prompt, caught gaps before shipping |
| `/precommit` | Quality gate before every commit — test audit, instruction compliance, app verification |
| `/debug` | Hypothesis-driven debugging when features broke |
| `/status` | Project dashboard, progress tracking |
