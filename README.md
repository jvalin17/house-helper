# House Helper — Job Agent

An AI-powered job application assistant. Search for jobs, get scored matches against your experience, generate tailored resumes that preserve your exact formatting, and track applications — all from one app.

## Quick Start

### Option 1: Download the Desktop App

Download the latest release for your platform:

| Platform | Download | Notes |
|----------|----------|-------|
| **macOS (Apple Silicon)** | [House Helper.dmg](https://github.com/jvalin17/house-helper/releases/latest) | M1/M2/M3/M4 chips |
| **macOS (Intel)** | [House Helper.dmg](https://github.com/jvalin17/house-helper/releases/latest) | Older Intel Macs |
| **Windows** | [House Helper.msi](https://github.com/jvalin17/house-helper/releases/latest) | Windows 10+ |
| **Linux (Debian/Ubuntu)** | [house-helper.deb](https://github.com/jvalin17/house-helper/releases/latest) | .deb package |
| **Linux (AppImage)** | [House-Helper.AppImage](https://github.com/jvalin17/house-helper/releases/latest) | Universal Linux |

> **Note:** The desktop app bundles the Python backend as a sidecar. No Python or Node.js installation needed. Just download, install, and open.

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

**macOS / Linux:**
```bash
chmod +x setup.sh run.sh
./setup.sh
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pip install fastapi uvicorn python-dotenv httpx anthropic openai rapidfuzz python-docx PyMuPDF python-multipart weasyprint markdown beautifulsoup4 "numpy<2" "transformers<5" "sentence-transformers<5"
cd frontend; npm install; cd ..
copy .env.example .env
```

The setup script checks Python 3.12 and Node 18+, creates a virtual environment, installs all dependencies, and creates `.env` from template.

#### Run

**macOS / Linux (one command):**
```bash
./run.sh
```

This starts both backend (port 8040) and frontend (port 5173). Press Ctrl+C to stop both.

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

Open **http://localhost:5173**

### Connect an AI Provider

Go to **Settings** in the app:

1. Select a provider (Claude, OpenAI, DeepSeek, Gemini, Grok, Ollama)
2. Enter your API key
3. Pick a model
4. Click **Save Provider**

The key persists across sessions and model switches. You only enter it once.

Without an AI provider, the app still works — algorithmic matching and template-based generation are free. AI adds deeper analysis, better tailoring, and smart suggestions.

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
   - "Show only 6 years of experience"
   - "Focus on backend, skip frontend work"
   - "Target as mid-level role"
5. Click **Apply Changes & Generate Resume**
6. Review the generated resume and cover letter
7. **Save this version** — explicitly save up to 5 resumes (named `resume_26_v1`, etc.)
8. **Refine** — type adjustments and click Regenerate without starting over
9. **Download** as PDF, DOCX, or Markdown
10. Click **Apply & Track** to log the application

### Step 5: Track Applications

- **Dashboard** tab shows application cards: Applied, Interview, Offer, Rejected
- Click any card to see timeline, linked resume/cover letter, status history
- Update status as your application progresses
- **Reset Dashboard** clears all jobs and applications (preserves your Knowledge Bank and saved resumes)

## Adding Knowledge

Beyond importing resumes, you can add knowledge from:

- **Links** — Paste a GitHub, LinkedIn, or portfolio URL. The app fetches the page and extracts skills. You review and accept/deny each skill before saving.
- **Text** — Paste any text about your experience. Skills are extracted with accept/deny toggles.
- **Manual** — Add experiences, edit bullets, delete entries directly in the Knowledge Bank.

Multiple imports merge intelligently:
- Same company + role + dates -> unique bullets are appended (not duplicated)
- Same skill name -> skipped (already exists)
- Same institution -> skipped
- Different entries -> added normally

## AI Providers & Cost

### Providers for Resume Analysis & Generation

Resume analysis, fit scoring, and tailored generation need a capable cloud model:

| Provider | Model | Cost per Resume | How to Get Key |
|----------|-------|----------------|----------------|
| **Claude** (Anthropic) | Sonnet 4 | ~$0.017 | [console.anthropic.com](https://console.anthropic.com/) |
| **OpenAI** | GPT-4o | ~$0.013 | [platform.openai.com](https://platform.openai.com/) |
| **DeepSeek** | DeepSeek-V3 | ~$0.001 | [platform.deepseek.com](https://platform.deepseek.com/) |
| **Google** | Gemini 2.0 Flash | ~$0.001 | [aistudio.google.com](https://aistudio.google.com/) |
| **Grok** (xAI) | Grok-2 | ~$0.011 | [console.x.ai](https://console.x.ai/) |

### Ollama (Free, Local)

```bash
brew install ollama        # macOS
# See ollama.com for Linux/Windows
ollama serve
ollama pull mistral
```

Ollama runs on your machine — no API key, no cost, no data leaves your computer. The app uses it **automatically for PDF resume import** (extracting structured data from messy PDF text).

**Important:** Ollama is too slow for resume analysis and generation. Use a cloud provider for those features. Ollama is only for PDF import extraction.

### No AI Mode

Everything works without any AI provider:
- **Matching:** Algorithmic scoring (skill overlap, TF-IDF text similarity, semantic matching, experience years)
- **Generation:** Template-based assembly from your knowledge bank
- **Cost:** $0

### Cost Tracking

In **Settings -> AI Usage**:
- See **real-time cost tracking**: today's spend and all-time spend broken down by provider
- Cost estimates shown per model when selecting a provider
- Every LLM call logs tokens used and estimated cost

### Job Board API Keys

| Source | What You Get | Free Tier | API Key |
|--------|-------------|-----------|---------|
| **JSearch** | LinkedIn, Indeed, Glassdoor jobs | 500 requests/month | [rapidapi.com/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) |
| **Adzuna** | Adzuna job listings | 250 requests/day | [developer.adzuna.com](https://developer.adzuna.com/) |
| **RemoteOK** | Remote-only jobs | Unlimited | None needed |

RemoteOK works immediately with no setup. Add JSearch for broader coverage.

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
- "Show only 6 years of experience"
- "Skip the Dematic role entirely"
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

### Export Formats

- **PDF** — one page, professional formatting, bold categories, centered header
- **DOCX** — preserves your original resume formatting exactly
- **Markdown** — plain text for version control

### Job Filters

- **Need sponsorship** — hides jobs that require existing work authorization (you need visa sponsorship)
- **Lack clearance** — hides jobs that require security clearance
- **Skip internships** — hides internship-level positions

## Testing

```bash
# All tests (backend + frontend)
./test.sh

# Backend only
cd backend && python -m pytest

# Frontend only
cd frontend && npx vitest run

# Frontend watch mode
cd frontend && npx vitest
```

**617+ tests total:**
- 527+ backend tests (pytest)
- 90+ frontend tests (vitest)

Covering: DOCX surgery, knowledge bank merge, suggestion feedback, resume templates, user instructions, PDF parsing, LLM providers, auth system, job filtering, cost tracking, full workflow integration tests.

CI runs automatically on every push to main via GitHub Actions.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite (WAL mode) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, shadcn/ui |
| Desktop | Tauri 2 (native wrapper, sidecar backend) |
| LLM | Claude, OpenAI, DeepSeek, Grok, Gemini, Ollama |
| Resume | python-docx (DOCX surgery), WeasyPrint (PDF), PyMuPDF (PDF parsing) |
| ML | Sentence Transformers, spaCy (optional) |
| Testing | pytest (backend), vitest (frontend), GitHub Actions CI |

## Multi-User Mode (Built, Disabled by Default)

The app has a complete auth system built in but **disabled by default**. In the default `local` mode, there's no login — it works as a single-user desktop app.

To enable multi-user mode for hosted deployment:

```bash
# Add to .env
AUTH_MODE=multi
JWT_SECRET=your-random-secret-key-at-least-32-chars
ENCRYPTION_KEY=   # auto-generated on first run if not set
```

**What multi-user mode does:**
- Shows login/signup pages (email + password)
- Each user gets an isolated SQLite database (`~/.house-helper/users/{id}/data.db`)
- All data is completely separated — users can't see each other's jobs, resumes, or settings
- API keys encrypted with AES-256-GCM at rest
- JWT tokens (24h expiry) for session management
- Passwords hashed with bcrypt (cost 12)

## Building the Desktop App

### Prerequisites

- **Rust** — `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Tauri CLI** — `npm install -g @tauri-apps/cli@latest`
- **PyInstaller** — `pip install pyinstaller` (for bundling the Python backend)

### Build

```bash
# Build the backend binary (PyInstaller)
cd backend && pyinstaller --onefile main.py --name house-helper-backend

# Build the desktop app (Tauri)
cd frontend && npx tauri build
```

Output:
- **macOS:** `frontend/src-tauri/target/release/bundle/dmg/House Helper.dmg`
- **Windows:** `frontend/src-tauri/target/release/bundle/msi/House Helper.msi`
- **Linux:** `frontend/src-tauri/target/release/bundle/deb/house-helper.deb`

## Known Limitations

- **Auto-apply pipeline** — Search and matching stages work, but browser form-filling automation (Playwright) is not yet built. Use the manual "Tailor Resume" -> download -> apply workflow.
- **Ollama** — Only useful for PDF import extraction. Too slow for analysis/generation.
- **Token estimation** — Cost tracking uses word-count heuristics (~30% margin). Not exact, but close enough for budgeting.
- **PDF parsing** — Best with Ollama for extraction. Without it, the algorithmic parser handles simple formats but may miss experiences in complex PDF layouts.

## Not Yet Built

- **Browser form filling** — Playwright automation to actually fill and submit job application forms
- **Prompt caching** — Anthropic cache for knowledge bank to reduce input token cost ~30%
- **Plugin system** — Architecture designed for apartment/recipe agents as separate plugins
- **Docker deployment** — Containerized hosting with multi-user auth enabled
- **Auto-update** — Check for and install software updates within the app
- **Email verification** — Verify email on signup
- **Forgot password** — Email-based password reset
- **OAuth** — Google/GitHub login as alternative to email+password
