<div align="center">

# Panini

**Your personal AI assistant — named after the ancient Sanskrit scholar who created the first formal rule system.**

[![Tests](https://github.com/jvalin17/house-helper/actions/workflows/test.yml/badge.svg)](https://github.com/jvalin17/house-helper/actions/workflows/test.yml)
[![Release](https://img.shields.io/github/v/release/jvalin17/house-helper?label=latest&color=7b2ff7)](https://github.com/jvalin17/house-helper/releases/latest)
[![Tests](https://img.shields.io/badge/tests-695%2B-brightgreen)](https://github.com/jvalin17/house-helper/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/react-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![Tauri](https://img.shields.io/badge/tauri-2-FFC131?logo=tauri&logoColor=white)](https://tauri.app)

[Download](#-download) &nbsp; | &nbsp; [Quick Start](#-quick-start) &nbsp; | &nbsp; [Features](#-key-features) &nbsp; | &nbsp; [AI Providers](#-ai-providers--cost) &nbsp; | &nbsp; [Contributing](#-contributing)

</div>

---

## Agents

| Agent | Status | Description |
|-------|--------|-------------|
| **Jobsmith** | Available | Search jobs, generate tailored resumes & cover letters, track applications |
| **Apartment Agent** | Coming soon | Search and compare apartments |
| **Recipe Agent** | Coming soon | Find recipes based on ingredients you have |
| **Travel Agent** | Coming soon | Plan trips, find deals, manage itineraries |

---

## Download

> The desktop app bundles everything. No Python or Node.js needed.

| Platform | Download | Notes |
|----------|----------|-------|
| **macOS (Apple Silicon)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_aarch64.dmg) | M1 / M2 / M3 / M4 |
| **Windows 10+** | [Panini.msi](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_x64_en-US.msi) | 64-bit |

<details>
<summary><strong>macOS: "app is damaged" fix</strong></summary>

macOS blocks unsigned apps. After installing, run in Terminal:
```bash
xattr -cr "/Applications/Panini.app"
```
Then open normally. Or right-click the app and choose **Open**.
</details>

---

## Quick Start

### From Source

**Prerequisites:** Python 3.12 &bull; Node.js 18+

```bash
git clone https://github.com/jvalin17/house-helper.git
cd house-helper
./setup.sh    # installs everything
./run.sh      # starts backend + frontend
```

Open **http://localhost:5173**

<details>
<summary><strong>Windows setup</strong></summary>

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pip install fastapi uvicorn python-dotenv httpx anthropic openai rapidfuzz python-docx PyMuPDF python-multipart weasyprint markdown beautifulsoup4 pyjwt bcrypt cryptography "numpy<2" "transformers<5" "sentence-transformers<5"
cd frontend; npm install; cd ..
copy .env.example .env

# Terminal 1: cd backend && uvicorn main:app --port 8040 --reload
# Terminal 2: cd frontend && npm run dev
```
</details>

### Connect an AI Provider

**Settings** tab in the app:

1. Select a provider (Claude, OpenAI, DeepSeek, Gemini, Grok, OpenRouter, or Ollama)
2. Enter your API key
3. Pick a model
4. Click **Save Provider**

Works without AI too — algorithmic matching and template-based generation are free.

---

## How to Use

### 1. Import Your Resume

Go to **Superpower Lab** &rarr; drag-and-drop your resume (DOCX, PDF, or TXT). The app extracts experiences, skills, education, and projects into the Knowledge Bank. DOCX formatting is preserved for generation.

Import up to 5 resumes. The knowledge bank merges them intelligently.

### 2. Search for Jobs

Go to **Job Search** &rarr; enter job title, location, keywords &rarr; **Scout Jobs**. Toggle filters for sponsorship, clearance, internships.

### 3. Score & Evaluate

- **Match All** — free algorithmic scoring (instant)
- **Evaluate Selected (AI)** — deep LLM analysis per job

### 4. Tailor Your Resume

Click **Tailor Resume** on any job:

1. AI analyzes your fit: match %, strengths, gaps, suggested improvements
2. Select which suggestions to apply, flag incorrect ones
3. Add custom instructions (e.g., "focus on backend", "target mid-level")
4. **Generate** &rarr; review resume + cover letter
5. **Download** as PDF, DOCX, or Markdown
6. **Save** up to 5 curated versions

### 5. Track Applications

**Dashboard** tab shows application cards by status. Update as you progress.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **DOCX Surgery** | Generates resumes by surgically replacing text in your original DOCX — preserves fonts, bold, colors, spacing |
| **9 AI Providers** | Claude, OpenAI, DeepSeek, Gemini, Grok, OpenRouter, HuggingFace, Custom, Ollama |
| **Budget Control** | Daily spend limit with per-feature breakdown. Over-budget confirmation before spending |
| **Smart Matching** | Skills overlap + TF-IDF + semantic similarity + experience years |
| **Suggestion Feedback** | Flag bad suggestions — they're excluded from future prompts |
| **Custom Instructions** | Direct the AI with natural language ("skip frontend roles", "show 6 years") |
| **Source Toggles** | Enable/disable job sources. Smart routing prioritizes premium sources |
| **Format Preservation** | PDF, DOCX, Markdown, Text export. DOCX keeps your exact formatting |
| **Saved Resumes** | Curate up to 5 versions with auto-naming (`resume_26_v1`) |
| **Hot Reload** | Change AI provider/model/key — applied instantly, no restart |
| **Multi-User Auth** | Optional email+password auth with per-user isolated databases |

---

## AI Providers & Cost

| Provider | Model | ~Cost/Resume | Get Key |
|----------|-------|-------------|---------|
| Claude | Sonnet 4 | $0.017 | [console.anthropic.com](https://console.anthropic.com/) |
| OpenAI | GPT-4o | $0.013 | [platform.openai.com](https://platform.openai.com/) |
| DeepSeek | V3 | $0.001 | [platform.deepseek.com](https://platform.deepseek.com/) |
| Gemini | 2.0 Flash | $0.001 | [aistudio.google.com](https://aistudio.google.com/) |
| Grok | Grok-2 | $0.011 | [console.x.ai](https://console.x.ai/) |
| OpenRouter | 100+ models | varies | [openrouter.ai](https://openrouter.ai/) |
| HuggingFace | Inference API | varies | [huggingface.co](https://huggingface.co/settings/tokens) |
| Custom | Any endpoint | varies | Your provider |
| Ollama | Local models | Free | [ollama.com](https://ollama.com/download) |

**OpenRouter** — one API key for Claude, GPT-4o, Gemini, Llama, DeepSeek, and 100+ more models.

**Custom** — connect any OpenAI-compatible API: Together AI, SiliconFlow, Groq, Fireworks, local vLLM servers.

**No AI** — everything works without a provider. Free algorithmic matching + template generation.

### Job Board Sources

| Source | Coverage | Free Tier |
|--------|----------|-----------|
| [JSearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) | LinkedIn, Indeed, Glassdoor | 500 req/month |
| [Adzuna](https://developer.adzuna.com) | Adzuna listings | 250 req/day |
| RemoteOK | Remote-only jobs | Unlimited, no key |

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

**695+ tests** (538 backend + 157 frontend) covering DOCX surgery, knowledge bank merge, budget enforcement, LLM providers, auth, job filtering, cost tracking, and full workflow integration.

---

## Multi-User Mode

Disabled by default (single-user desktop). Enable for hosted deployment:

```bash
# .env
AUTH_MODE=multi
JWT_SECRET=your-random-secret-key-at-least-32-chars
```

Each user gets an isolated SQLite database. API keys encrypted with AES-256-GCM. JWT sessions with bcrypt password hashing.

---

## Building the Desktop App

```bash
# Prerequisites: Rust, Tauri CLI, PyInstaller
cd backend && pyinstaller --onefile main.py --name panini-backend
cd frontend && npx tauri build
```

Or just push a version tag — GitHub Actions builds for macOS + Windows automatically:

```bash
git tag v1.0.0 && git push origin v1.0.0
```

---

## Known Limitations

- **Apply & Track** — not yet functional. Download resume and apply manually.
- **Auto-apply** — job search works, browser form-filling (Playwright) not built yet.
- **Ollama** — PDF import only. Too slow for analysis/generation.
- **Cost tracking** — word-count heuristics (~30% margin).

## Roadmap

- [ ] Browser form filling (Playwright auto-apply)
- [ ] Prompt caching (reduce AI cost ~30%)
- [ ] Auto-update within the app
- [ ] Plugin system for new agents
- [ ] Docker deployment
- [ ] OAuth (Google/GitHub login)

---

## Contributing

Found a bug or want a new agent? [Open an issue](https://github.com/jvalin17/house-helper/issues/new).

---

<div align="center">

**Panini** &mdash; named after [Panini](https://en.wikipedia.org/wiki/P%C4%81%E1%B9%87ini), the ancient Sanskrit grammarian who formalized language with rules. This app formalizes your job search with AI.

</div>
