<div align="center">

# Panini

[![Tests](https://github.com/jvalin17/house-helper/actions/workflows/test.yml/badge.svg)](https://github.com/jvalin17/house-helper/actions/workflows/test.yml)
[![Download](https://img.shields.io/badge/download-latest-7b2ff7?style=flat&logo=github)](https://github.com/jvalin17/house-helper/releases/latest)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Tauri](https://img.shields.io/badge/Tauri-2-24C8D8?logo=tauri&logoColor=white)
![Tests](https://img.shields.io/badge/tests-1335%2B-brightgreen)

A multi-agent AI desktop app — job search with smart ranking, apartment hunting with premium intelligence, resume generation, and application tracking.

</div>

---

## Agents

| Agent | Description | Status |
|-------|-------------|--------|
| **Jobsmith** | Search jobs, smart ranking, generate tailored resumes, track applications | Active |
| **NestScout** | Search apartments, Nest Lab deep analysis, Nest Intel premium verified data | Active |

---

## Download the Desktop App

No Python or Node.js needed. Just download, install, and open.

| Platform | Download | Notes |
|----------|----------|-------|
| **macOS (Apple Silicon)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.2.0_aarch64.dmg) | M1 / M2 / M3 / M4 |
| **macOS (Intel)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.2.0_x64.dmg) | Older Intel Macs |
| **Windows** | [Panini.msi](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.2.0_x64_en-US.msi) | Windows 10+ (64-bit) |
| **Linux** | [panini.deb](https://github.com/jvalin17/house-helper/releases/latest/download/panini_0.2.0_amd64.deb) | Debian/Ubuntu |

### Windows Installation

1. Download `Panini_0.2.0_x64_en-US.msi`
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

1. **Connect APIs** — Go to **Settings** (gear icon) → enter API keys for AI provider + data sources
2. **For Jobsmith** — Import your resume in **Superpower Lab** → search jobs with natural language
3. **For NestScout** — Search apartments by city/zip → nest favorites → analyze in Lab → get Intel

Works without AI (free algorithmic matching + search), but AI adds deeper analysis and smarter results.

---

## Features

### Centralized Settings

One page manages all API keys and preferences across both agents.

| Feature | Description |
|---------|-------------|
| **AI Providers** | Claude, OpenAI, DeepSeek, Gemini, Grok, OpenRouter, HuggingFace, Custom, Ollama — pick per agent |
| **Shared Data Sources** | Google Maps (distances, reviews), Walk Score (walkability) — used by both agents |
| **Jobsmith Sources** | RapidAPI/JSearch (LinkedIn, Indeed, Glassdoor), Adzuna (App ID + App Key) |
| **NestScout Sources** | RealtyAPI (Zillow images + listings), RentCast (market data) |
| **Budget Controls** | Daily spend limit, real-time cost tracking, per-feature breakdown |
| **Hot Reload** | Change any key or provider — applied instantly, no restart |

### Jobsmith (Job Search Agent)

| Feature | Description |
|---------|-------------|
| **Smart Search** | Natural language: "senior backend python Austin remote $150k+ no clearance" |
| **Multi-Source Search** | JSearch (LinkedIn/Indeed/Glassdoor), Adzuna, RemoteOK with auto-failover |
| **Smart Ranking** | Learns from your clicks and saves — results improve over time, encrypted at rest |
| **Consultancy Filter** | Auto-filters 30+ staffing agencies (Infosys, Wipro, TCS, Cognizant...) |
| **5 Exclusion Toggles** | Sponsorship, clearance, citizenship, internship, consultancy — defaults that make sense |
| **Cross-Search Dedup** | Same job on LinkedIn + Indeed shown once (URL + title+company matching) |
| **Algorithmic Matching** | Skills overlap, TF-IDF, semantic similarity, experience years |
| **AI Evaluation** | Deep LLM analysis per job — desire fit + qualification fit (requires AI provider) |
| **Match Calibration** | Rate jobs good/partial/poor → weights adjust to your preferences |
| **Resume Generation** | AI-tailored resumes with DOCX format preservation, suggestion control, custom instructions |
| **Saved Resumes** | Curate up to 5 versions (auto-named `resume_26_v1`), export PDF/DOCX/MD/TXT |
| **Knowledge Bank** | Import resume (DOCX/PDF/TXT), extract from URLs, inline edit, smart merge |

### NestScout (Apartment Search Agent)

| Feature | Description |
|---------|-------------|
| **Multi-Source Search** | RealtyAPI (Zillow photos + listings) + RentCast (market data) with failover |
| **Smart Ranking** | Learns which apartments you prefer from clicks and saves — zero developer access |
| **55+ Community Filter** | Auto-filters age-restricted communities |
| **Bedroom-Specific Pricing** | Shows 2BR price when you search for 2BR, not the studio minimum |
| **Nest Lab — AI Analysis** | Deep property analysis for shortlisted homes: |
| | AI overview (streamed), 3-state feature tags (must-have / deal-breaker / neutral) |
| | Price intelligence (area median, percentile, comparables), cost calculator with concession math |
| | Photo gallery with lightbox, AI Q&A ("Is this near good schools?") |
| **Nest Intel — Premium Data** | Verified data from connected APIs (user opts in, sees cost first): |
| | Unit availability with exact prices per floor plan (RealtyAPI) |
| | Walk / Transit / Bike scores (Walk Score API) |
| | Airport distance + commute time (Google Distance Matrix) |
| | Floor plan vision analysis — livability score, furniture fit, WFH suitability (Vision LLM) |
| | Concession + fee extraction from listing URL (LLM) — auto-fills cost calculator |
| | Resident review mining with sentiment themes (Google Places + LLM) |
| | Lease policy extraction — pet rules, subletting, parking, utilities (LLM) |
| **Compare View** | Side-by-side 2-3 listings with preference-weighted scoring + Intel data |
| **Intel Badge** | Listings with gathered Intel marked on search cards, Lab picker, and compare view |

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

**1116+ tests** covering job search, apartment search, ranking engine, Intel pipeline, DOCX surgery, knowledge bank, budget enforcement, LLM providers, and full workflow integration.

---

## Project Structure

```
house-helper/
├── backend/                  # Python FastAPI server
│   ├── main.py               # App entry point (port 8040)
│   ├── agents/job/           # Jobsmith: search, matching, resume gen, applications
│   ├── agents/apartment/     # NestScout: search, Nest Lab, Nest Intel
│   ├── shared/               # LLM providers, ranking engine, algorithms, pipeline
│   └── auth/                 # Multi-user auth (disabled by default)
├── frontend/                 # React + TypeScript + Vite
│   ├── src/components/       # UI components (tabs, knowledge bank, settings, modals)
│   ├── src/api/client.ts     # Typed API client — all backend communication
│   ├── src/types/index.ts    # Shared TypeScript interfaces
│   ├── src/hooks/            # Custom hooks (useAuth, useAsync)
│   ├── src/test/workflows/   # Integration tests (35+ workflow test files)
│   └── src-tauri/            # Tauri desktop app config + sidecar
├── tests/                    # Backend tests (pytest)
├── docs/                     # RUNBOOK, skills feedback
├── scripts/                  # Dev scripts (Tauri setup, app build)
├── requirements/             # Feature requirement docs
├── architecture/             # Architecture decision docs
├── setup.sh                  # One-command install (macOS/Linux)
├── run.sh                    # Start backend + frontend
└── test.sh                   # Run all tests
```

---

## Known Limitations

- **Apply & Track** — not yet functional. Download resume and apply manually.
- **Auto-apply** — search works, browser form-filling (Playwright) not built yet.
- **Ollama** — PDF import only. Too slow for analysis/generation.
- **Cost tracking** — word-count heuristics (~30% margin).

## Roadmap

- [ ] LLM gap analysis ("You want X roles but lack Y — here's your action plan")
- [ ] Ideal job/apartment profile (permanent ranking boost)
- [ ] Favorite company career page monitoring
- [ ] Browser form filling (Playwright auto-apply)
- [ ] Google Places nearby search (POIs around listings)
- [ ] Interactive map with commute visualization
- [ ] PDF export for Intel reports
- [ ] Docker deployment

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
