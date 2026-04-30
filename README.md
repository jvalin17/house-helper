<div align="center">

# Panini

[![Tests](https://github.com/jvalin17/house-helper/actions/workflows/test.yml/badge.svg)](https://github.com/jvalin17/house-helper/actions/workflows/test.yml)
[![Download](https://img.shields.io/badge/download-v0.6.0-7b2ff7?style=flat&logo=github)](https://github.com/jvalin17/house-helper/releases/latest)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![Tauri](https://img.shields.io/badge/Tauri-2-24C8D8?logo=tauri&logoColor=white)
![Tests](https://img.shields.io/badge/tests-695%2B-brightgreen)

A multi-agent AI assistant — named after [Pāṇini](https://en.wikipedia.org/wiki/P%C4%81%E1%B9%87ini), the ancient Sanskrit scholar who created the first formal rule system.

</div>

---

## Agents

| Agent | Description | Status |
|-------|-------------|--------|
| **Jobsmith** | Search jobs, score matches, generate tailored resumes, track applications | Active |
| **Apartment Agent** | Search and compare apartments, track applications | Coming soon |
| **Recipe Agent** | Find recipes based on ingredients you have | Coming soon |
| **Travel Agent** | Plan trips, find deals, manage itineraries | Coming soon |

---

## Quick Start

### Option 1: Download the Desktop App

| Platform | Download | Notes |
|----------|----------|-------|
| **macOS (Apple Silicon)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_aarch64.dmg) | M1 / M2 / M3 / M4 |
| **macOS (Intel)** | [Panini.dmg](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_x64.dmg) | Older Intel Macs |
| **Windows** | [Panini.msi](https://github.com/jvalin17/house-helper/releases/latest/download/Panini_0.1.0_x64_en-US.msi) | Windows 10+ |
| **Linux (Debian/Ubuntu)** | [panini.deb](https://github.com/jvalin17/house-helper/releases/latest/download/panini_0.1.0_amd64.deb) | .deb package |

> No Python or Node.js needed. The desktop app bundles everything — just download, install, and open.

<details>
<summary><strong>macOS: "app is damaged" fix</strong></summary>

If you see "app is damaged and can't be opened", run this in Terminal:
```bash
xattr -cr "/Applications/Panini.app"
```
Then open the app normally. This happens because the app isn't signed with an Apple Developer certificate yet. Alternatively, right-click the app and choose "Open" to bypass the warning.
</details>

### Option 2: Run from Source

#### Prerequisites

- **Python 3.12** (not 3.14 — PyTorch requires 3.12) — [python.org/downloads](https://www.python.org/downloads/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)

Works on macOS, Linux, and Windows.

#### Install

```bash
git clone https://github.com/jvalin17/house-helper.git
cd house-helper
```

<details>
<summary><strong>macOS / Linux</strong></summary>

```bash
chmod +x setup.sh run.sh
./setup.sh
```
</details>

<details>
<summary><strong>Windows (PowerShell)</strong></summary>

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pip install fastapi uvicorn python-dotenv httpx anthropic openai rapidfuzz python-docx PyMuPDF python-multipart weasyprint markdown beautifulsoup4 pyjwt bcrypt cryptography "numpy<2" "transformers<5" "sentence-transformers<5"
cd frontend
npm install
cd ..
copy .env.example .env
```
</details>

The setup script checks Python 3.12 and Node 18+, creates a virtual environment, installs all dependencies, and creates `.env` from template.

#### Run

**macOS / Linux:**
```bash
./run.sh
```

**Windows (two terminals):**
```powershell
# Terminal 1 — Backend
.venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --port 8040 --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** — backend runs on port 8040, frontend on 5173. Press Ctrl+C to stop.

---

## Connect an AI Provider

Go to **Settings** in the app:

1. Select a provider (Claude, OpenAI, DeepSeek, Gemini, Grok, OpenRouter, HuggingFace, Custom, or Ollama)
2. Enter your API key
3. Pick a model — each shows speed, quality rating, and cost per resume
4. Click **Save Provider**

The key persists across sessions and model switches. You only enter it once. Settings are hot-reloaded — no restart needed when switching providers.

> Without an AI provider, the app still works — algorithmic matching and template-based generation are free. AI adds deeper analysis, better tailoring, and smart suggestions.

---

## How to Use

### Step 1: Import Your Resume

1. Go to **Superpower Lab** tab
2. Drag-and-drop your resume (DOCX, PDF, or TXT) into the import area
3. The app extracts your experiences, skills, education, and projects into the **Knowledge Bank**
4. If it's a DOCX, the original formatting is stored as a template — generated resumes will match your exact format

You can import multiple resumes (up to 5). Each becomes a template. The knowledge bank merges them — same company/role gets unique bullets merged, not duplicated.

### Step 2: Search for Jobs

1. Go to **Job Search** tab
2. Enter a job title, location, keywords — or leave empty (defaults to your skills)
3. Toggle filters: Need sponsorship, Lack clearance, Skip internships
4. Click **Scout Jobs** to search across connected job boards
5. Results appear sorted by match score

### Step 3: Score Jobs

- Click **Match All (local)** to score every result using algorithmic matching (free, instant)
- Select specific jobs and click **Evaluate Selected (AI)** for deeper LLM analysis (requires AI provider)
- Click any job to see the full detail: match score breakdown, required skills, description

### Step 4: Tailor Your Resume

1. Click **Tailor Resume** on any job
2. The AI analyzes your resume fit:
   - Shows your current resume match %, knowledge bank potential, and the gap
   - Lists suggested improvements with checkboxes and expected impact
   - Each suggestion shows its source (knowledge bank, same experience better framing, etc.)
3. **Accept or reject** each suggestion:
   - Check/uncheck to select what to apply
   - Click **Flag incorrect** on bad suggestions — they won't appear again
4. **Add custom instructions** (optional):
   - "Show only recent experience"
   - "Focus on backend, skip frontend work"
   - "Target as mid-level role"
   - "Skip a specific role entirely"
5. Click **Apply Changes & Generate Resume**
6. Review the generated resume and cover letter
7. **Save this version** — explicitly save up to 5 resumes (named `resume_26_v1`, etc.)
8. **Refine** — type adjustments and click Regenerate without starting over
9. **Download** as PDF, DOCX, Markdown, or plain text

### Step 5: Track Applications

- **Dashboard** tab shows application cards: Applied, Interview, Offer, Rejected
- Click any card to see timeline, linked resume/cover letter, status history
- Update status as your application progresses
- **Reset Dashboard** clears all jobs and applications (preserves your Knowledge Bank and saved resumes)

---

## Adding Knowledge

Beyond importing resumes, you can add knowledge from:

| Method | How It Works |
|--------|-------------|
| **Links** | Paste a GitHub, LinkedIn, or portfolio URL. The app fetches the page and extracts skills. You review and accept/deny each skill before saving. |
| **Text** | Paste any text about your experience. Skills are extracted with accept/deny toggles. |
| **Manual** | Add experiences, edit bullets, delete entries directly in the Knowledge Bank. |

**Smart merge:** Same company + role + dates → unique bullets appended (not duplicated). Same skill name → skipped. Same institution → skipped. Different entries → added normally.

---

## AI Providers & Cost

### Providers Supported

| Provider | Model | Cost per Resume | How to Get Key |
|----------|-------|----------------|----------------|
| **Claude** (Anthropic) | Claude Sonnet 4 | ~$0.017 | [console.anthropic.com](https://console.anthropic.com/) |
| **OpenAI** | GPT-4o | ~$0.013 | [platform.openai.com](https://platform.openai.com/) |
| **DeepSeek** | DeepSeek V3 | ~$0.001 | [platform.deepseek.com](https://platform.deepseek.com/) |
| **Google** | Gemini 2.0 Flash | ~$0.001 | [aistudio.google.com](https://aistudio.google.com/) |
| **Grok** (xAI) | Grok 2 | ~$0.011 | [console.x.ai](https://console.x.ai/) |
| **OpenRouter** | 100+ models | varies | [openrouter.ai](https://openrouter.ai/) |
| **HuggingFace** | Inference API models | varies | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) |
| **Custom** | Any provider with an API | varies | Your provider's dashboard |

**OpenRouter** gives you access to 100+ models (Claude, GPT-4o, Gemini, Llama, DeepSeek, and more) through a single API key. Great for trying different models without multiple accounts.

**Custom provider** lets you connect any provider that exposes an API endpoint — Together AI, SiliconFlow, Groq, Fireworks, local vLLM/TGI servers, or any other service. Just provide the base URL, API key, and model name.

### Ollama (Free, Local)

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install ollama
ollama serve
ollama pull mistral
```
</details>

<details>
<summary><strong>Windows</strong></summary>

1. Download the installer from [ollama.com/download](https://ollama.com/download)
2. Run the installer — Ollama runs as a background service automatically
3. Open PowerShell and pull a model:
```powershell
ollama pull mistral
```
</details>

<details>
<summary><strong>Linux</strong></summary>

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
ollama pull mistral
```
</details>

Ollama runs on your machine — no API key, no cost, no data leaves your computer. The app uses it **automatically for PDF resume import** (extracting structured data from messy PDF text). The Settings page includes Ollama setup instructions and a model browser.

> Ollama is too slow for resume analysis and generation. Use a cloud provider for those features.

### No AI Mode

Everything works without any AI provider:

| Feature | How It Works Without AI | Cost |
|---------|------------------------|------|
| **Matching** | Algorithmic scoring (skill overlap, TF-IDF, semantic similarity, experience years) | $0 |
| **Generation** | Template-based assembly from your knowledge bank | $0 |
| **Import** | DOCX/TXT parsed locally, PDF needs Ollama for best results | $0 |

### Budget Enforcement

Set a daily spending limit in **Settings** to control AI costs:

- **Daily cost limit** — set a max dollar amount per day (e.g., $0.50). Every LLM call checks the budget before running.
- **Per-feature breakdown** — see exactly how much each feature costs (resume generation, job search, cover letters, extraction)
- **Today's spend & all-time spend** — real-time tracking in the Settings page
- **Over-budget confirmation** — when you hit your limit, the app pauses AI features and asks for confirmation before spending more. You're never charged without knowing.
- **Cost estimates** — shown per model when selecting a provider, so you can compare before committing

### Job Board Sources

| Source | What You Get | Free Tier | API Key |
|--------|-------------|-----------|---------|
| **JSearch** | LinkedIn, Indeed, Glassdoor jobs | 500 requests/month | [rapidapi.com/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) |
| **Adzuna** | Adzuna job listings | 250 requests/day | [developer.adzuna.com](https://developer.adzuna.com/) |
| **RemoteOK** | Remote-only jobs | Unlimited | None needed |

RemoteOK works immediately with no setup. Add JSearch for broader coverage.

**Source toggling** — enable or disable individual job sources from Settings. Connection status badges show which sources are active.

---

## Key Features

### DOCX Format Preservation

When you import a DOCX resume, the app stores the original file and maps every paragraph (name, contact, summary, each bullet point). During generation, the LLM decides what content to change, and the code surgically replaces only the text — preserving your fonts, bold, colors, spacing, bullet styles, and centering. The exported DOCX is your original resume with only the content updated.

### Saved Resumes (Max 5)

Generated resumes are ephemeral until you explicitly save them. Click **Save this version** on the result page to add it to your curated collection (named `resume_26_v1`, `resume_26_v2`, etc.). Max 5 saved at a time. Unsaved resumes are cleaned up after 24 hours.

### Resume Templates

Store up to 5 resume files. Each import creates a template. Set a default in the **Templates** section under My Superpowers. Generation always uses the default template's format. Switch defaults to generate with a different format.

### Suggestion Feedback

Bad LLM suggestion? Click **Flag incorrect**. The suggestion dims and is stored locally. Next time you analyze a job:
- The LLM prompt includes your rejected suggestions with "do NOT suggest these again"
- A filter catches similar rephrasings even if the LLM ignores the instruction

### Custom Instructions

On the analysis page and the result page, type instructions to control generation:
- "Show only recent experience"
- "Skip a specific role entirely"
- "Focus on backend architecture, not frontend"
- "Target as mid-level, not senior"

Instructions are passed directly to the LLM alongside your selected improvements.

### Match Scoring

Every job gets a composite score from:
- **Skills overlap** — fuzzy matching of required skills vs your resume
- **Text similarity** — TF-IDF comparison (pure Python, no heavy dependencies)
- **Semantic similarity** — Sentence Transformers embedding comparison (optional)
- **Experience years** — normalized from your work history

With an AI provider, you get deeper analysis: strengths, gaps, transferable skills, career strategy advice.

Match calibration weights are adjustable in Settings — rate a few jobs and the scoring algorithm recalibrates to your preferences.

### Export Formats

| Format | Details |
|--------|---------|
| **PDF** | One page, professional formatting, bold categories, centered header |
| **DOCX** | Preserves your original resume formatting exactly |
| **Markdown** | Plain text for version control |
| **Text** | Plain text format |

### Job Filters

- **Need sponsorship** — hides jobs that require existing work authorization (you need visa sponsorship)
- **Lack clearance** — hides jobs that require security clearance
- **Skip internships** — hides internship-level positions

---

## Testing

```bash
# All tests (backend + frontend)
./test.sh

# Backend only
cd backend && python -m pytest

# Frontend only
cd frontend && npx vitest run
```

**710+ tests** across 32 frontend test files and full backend coverage.

Covering: DOCX surgery, knowledge bank merge, suggestion feedback, resume templates, user instructions, PDF parsing, LLM providers, budget enforcement, auth system, job filtering, cost tracking, match calibration, and full workflow integration tests.

CI runs automatically on every push to main via GitHub Actions.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite (WAL mode) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui |
| Desktop | Tauri 2 (native wrapper, sidecar backend) |
| LLM | Claude, OpenAI, DeepSeek, Grok, Gemini, OpenRouter, HuggingFace, Custom, Ollama |
| Resume | python-docx (DOCX surgery), WeasyPrint (PDF), PyMuPDF (PDF parsing) |
| ML | Sentence Transformers, spaCy (optional) |
| Testing | pytest (backend), vitest (frontend), GitHub Actions CI |

---

## Multi-User Mode

<details>
<summary><strong>Built in, disabled by default — click to expand</strong></summary>

The app has a complete auth system but is **disabled by default**. In the default `local` mode, there's no login — it works as a single-user desktop app.

To enable multi-user mode for hosted deployment:

```bash
# Add to .env
AUTH_MODE=multi
JWT_SECRET=your-random-secret-key-at-least-32-chars
ENCRYPTION_KEY=   # auto-generated on first run if not set
```

**What multi-user mode does:**
- Shows login/signup pages (email + password)
- Each user gets an isolated SQLite database (`~/.panini/users/{id}/data.db`)
- All data is completely separated — users can't see each other's jobs, resumes, or settings
- API keys encrypted with AES-256-GCM at rest
- JWT tokens (24h expiry) for session management
- Passwords hashed with bcrypt (cost 12)
</details>

---

## Building the Desktop App

<details>
<summary><strong>Click to expand build instructions</strong></summary>

### Prerequisites

- **Rust** — `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Tauri CLI** — `npm install -g @tauri-apps/cli@latest`
- **PyInstaller** — `pip install pyinstaller` (for bundling the Python backend)

### Build

```bash
# Build the backend binary (PyInstaller)
cd backend && pyinstaller --onefile main.py --name panini-backend

# Build the desktop app (Tauri)
cd frontend && npx tauri build
```

Output:
- **macOS:** `frontend/src-tauri/target/release/bundle/dmg/Panini.dmg`
- **Windows:** `frontend/src-tauri/target/release/bundle/msi/Panini.msi`
</details>

---

## Known Limitations

- **Apply & Track** — The button on the result page is not yet functional. Download your resume and apply manually for now.
- **Auto-apply** — Search and matching work, but browser form-filling (Playwright) is not yet built.
- **Ollama** — Only useful for PDF import extraction. Too slow for analysis/generation.
- **Token estimation** — Cost tracking uses word-count heuristics (~30% margin). Close enough for budgeting.
- **PDF parsing** — Best with Ollama. Without it, the algorithmic parser handles simple formats but may miss experiences in complex layouts.

## Roadmap

- Browser form filling (Playwright auto-apply)
- Prompt caching (Anthropic cache for ~30% cost reduction)
- Plugin system for apartment/recipe/travel agents
- Docker deployment for hosted multi-user mode
- Auto-update within the app
- OAuth (Google/GitHub login)
