# House Helper — Job Agent

A desktop app that searches for jobs, scores them against your experience, generates tailored resumes and cover letters, and tracks your applications. Works with or without AI.

## What It Does

**Search** — Scout jobs from LinkedIn, Indeed, Glassdoor, Adzuna, and RemoteOK using official APIs. Filter by title, location, keywords, and remote preference. Results auto-sorted by match score.

**Match** — Score every job against your knowledge bank. Algorithmic matching (skill overlap, text similarity, semantic matching, experience years) works offline. Add an LLM for deeper analysis with strengths, gaps, and recommendations.

**Tailor** — Analyze your resume fit before generating. See your current match %, what your knowledge bank could achieve, and pick which improvements to apply. The LLM returns content decisions; your original resume format is preserved.

**Generate** — Tailored resume + cover letter per job. Export as PDF, DOCX, or Markdown. Cover letters address specific gaps honestly — never fabricate experience.

**Apply** — The Launchpad runs the full pipeline: search, match, generate, and prepare applications for your top matches. Track every application on a kanban board (Applied / Interview / Offer / Rejected).

**Learn** — Rate matches to calibrate the scoring algorithm. The system learns your preferences over time.

## Quick Start

```bash
git clone <repo-url> && cd house-helper
chmod +x setup.sh && ./setup.sh
```

The setup script checks for Python 3.10+ and Node 18+, creates a virtual environment, installs all dependencies (backend + frontend + optional ML), and creates a `.env` file from the template.

Then start the app:

```bash
# Terminal 1 — Backend
source .venv/bin/activate
uvicorn backend.main:app --port 8040 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173**

### API Keys (optional)

Edit `.env` to enable features:

| Key | What it enables | Where to get it |
|-----|----------------|-----------------|
| `ANTHROPIC_API_KEY` | AI resume generation, LLM matching | [console.anthropic.com](https://console.anthropic.com/) |
| `OPENAI_API_KEY` | Alternative AI provider | [platform.openai.com](https://platform.openai.com/) |
| `RAPIDAPI_KEY` | Job search via JSearch (LinkedIn, Indeed, Glassdoor) | [rapidapi.com/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) |

The app works without any API keys — you get algorithmic matching and template-based generation for free. AI features activate when you add a key and select a provider in Settings.

## Workflows

### 1. First-Time Setup

1. Open the app and go to **Superpower Lab**
2. Import your resume (drag-and-drop or click to browse — DOCX, PDF, TXT)
3. Review extracted experiences, skills, education, and projects
4. Optionally add more knowledge manually or extract skills from pasted text

### 2. Search and Tailor

1. Go to **Job Search** tab
2. Enter filters (or leave empty — defaults to your skills + US location)
3. Click **Scout Jobs** to search across connected job boards
4. Click **Match All (local)** to score every result against your knowledge bank
5. Select specific jobs and click **Evaluate Selected (AI)** for deeper LLM analysis
6. Click **Tailor Resume** on any job to start the generation flow:
   - AI analyzes your fit — shows current match, KB potential, strengths, gaps
   - Pick which suggested improvements to apply (checkboxes)
   - AI generates resume + cover letter using your selections
   - Download (PDF/DOCX/MD) and click **Apply & Track**

### 3. Auto-Apply Pipeline (The Launchpad)

1. Set your search filters on the Job Search tab
2. Scroll to **The Launchpad** and click **Do the Magic**
3. The pipeline runs automatically:
   - Searches job boards
   - Scores and ranks results
   - Generates tailored resumes for your top 5 matches
   - Prepares applications
4. Review results and track on the **Dashboard** tab

### 4. Resume Builder (Detailed)

1. Go to **Superpower Lab** and switch to the **Resume Builder** sub-tab
2. Paste a job link or description, or pick from your saved jobs
3. Click **Analyze Fit & Suggest Improvements**
   - See current resume match vs knowledge bank potential
   - Review each suggestion with impact score and source
4. Select improvements, then **Apply & Generate**
5. Download the tailored resume and cover letter

### 5. Track Applications

- **Dashboard** tab shows a kanban board: Applied / Interview / Offer / Rejected
- Click any card to expand timeline, linked resume/cover letter, and status history
- Move cards between columns as your application progresses

### 6. Calibrate Matching

- In job detail views, rate matches (Yes / Somewhat / No)
- Go to **Settings** and click **Recalculate** under Match Calibration
- Future matches improve based on your feedback

## Three LLM Modes

The app works at every level:

| Mode | Matching | Resume Generation | Cost |
|------|----------|-------------------|------|
| **No LLM** | Algorithmic (TF-IDF, skill overlap, semantic) | Template-based from your resume format | Free |
| **Offline LLM** (Ollama) | Local model analysis | Local model generation | Free (requires ~2GB RAM) |
| **Online LLM** (Claude/OpenAI) | Deep semantic analysis with context | AI-tailored content preserving your format | ~$0.006/resume |

Switch between modes in Settings without restarting.

## Features

### Job Sources

| Source | Coverage | Free Tier | API Key |
|--------|----------|-----------|---------|
| JSearch | LinkedIn, Indeed, Glassdoor | 500 req/month | Yes (RapidAPI) |
| Adzuna | Adzuna listings | 250 req/day | Yes |
| RemoteOK | Remote-only jobs | Unlimited | No |

When premium sources are configured, the app prioritizes them over generic sources.

### AI Providers

| Provider | Local | Cost |
|----------|-------|------|
| Claude (Anthropic) | No | ~$0.006/resume |
| OpenAI | No | Variable |
| Ollama | Yes | Free |
| HuggingFace | Both | Free/paid |
| None (free mode) | Yes | $0 |

### Match Scoring

Every job gets a score based on four features:
- **Skills overlap** — fuzzy matching of required skills vs your knowledge bank
- **Text similarity** — TF-IDF comparison of job description vs your experience (pure Python, no sklearn)
- **Semantic similarity** — Sentence Transformers embedding comparison (optional)
- **Experience years** — normalized years from your work history

With an LLM, you get deeper analysis considering context, transferable skills, and career trajectory.

### Resume Generation

The LLM returns JSON content decisions (which bullets to swap, what to emphasize). Your original resume format is preserved — the code assembles the final document from your template.

After generation, you see a clear match progression:

```
55%              →   68%                    →   85%                   →   78%
Algorithmic          LLM analysis               Knowledge bank            Generated resume
                     (current resume)            potential                 (+10%)
```

Plus a breakdown of what drives the algorithmic score (skills match, experience, text similarity, semantic match).

### Budget Control

- Set a daily spending limit in Settings
- Real-time cost tracking (today's usage vs limit)
- Cost-per-resume estimates shown for each model
- AI features pause when the limit is reached

### Export Formats

Resumes and cover letters export as:
- **PDF** — ready to upload to job applications
- **DOCX** — editable in Word or Google Docs
- **Markdown** — plain text, version-controllable

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite (WAL mode, 17 tables) |
| Frontend | React, TypeScript, Vite, shadcn/ui |
| LLM | Claude, OpenAI, Ollama, HuggingFace (hot-reload via LazyLLMProvider) |
| ML | Sentence Transformers, spaCy (optional, for offline semantic matching) |
| Desktop | Tauri 2.0 (planned) |

All backend HTTP calls are synchronous — async + FastAPI thread pool caused silent failures. This is intentional.

## Testing

```bash
./test.sh    # runs backend (250 tests) + frontend (21 tests) + build check
```

Or individually:

```bash
# Backend
source .venv/bin/activate
python -m pytest tests/ -q -m "not network and not live"

# Frontend
cd frontend && npx vitest run

# Live API tests (uses real API quota)
python -m pytest tests/ -m live -v
```

## Project Structure

```
house-helper/
  backend/
    main.py                       # FastAPI entry point
    coordinator.py                # Agent orchestrator
    agents/job/
      routes.py                   # All API endpoints
      services/                   # Business logic
        resume.py                 #   Template assembly generation
        auto_search.py            #   Job board search with dedup
        job_matcher.py            #   Algorithmic + LLM scoring
      prompts/                    # LLM prompt templates
        analyze_fit.py            #   Pre-generation analysis
        generate_resume.py        #   Resume content decisions
        match_job.py              #   Deep match analysis
      repositories/               # SQLite data access
    shared/
      db.py                       # 17 tables, auto-migration
      llm/                        # Provider abstraction (lazy-load, hot-reload)
      algorithms/                 # Pure Python TF-IDF, skill matcher, semantic
      job_boards/                 # Plugin system for job sources
      calibration/                # Match weight learning from user ratings
      export/                     # PDF, DOCX, Markdown renderers
      ats_optimizer.py            # ATS rules (updatable JSON file)
  frontend/
    src/
      pages/                      # Home, JobDashboard
      components/
        tabs/                     # JobSearchTab, ResumeBuilderTab
        ErrorBoundary.tsx         # Catches render crashes
        PreviewModal.tsx          # Analyze → select → generate → download
        ApplyPipeline.tsx         # The Launchpad (auto-apply)
        ApplicationTracker.tsx    # Kanban board
        Settings.tsx              # Provider, budget, sources, calibration
        KnowledgeBank.tsx         # Experiences, skills, education, projects
        ResumeAnalysis.tsx        # Fit analysis with selectable improvements
        ResumeResult.tsx          # Generated docs + export
      api/client.ts               # API client with error handling
  setup.sh                        # One-command setup
  test.sh                         # Run all tests
  .env.example                    # API key template
  skills-feedback.md              # 89 battle-tested lessons
```

## Not Yet Built

- **Browser form filling** — Playwright automation to fill and submit job application forms
- **Ollama end-to-end testing** — backend supports it, not tested with real models
- **Local ML matcher** — learns from LLM decisions to reduce API costs (needs 20+ data points)
- **Multiple saved resumes** — select which base resume to use per application
- **Tauri desktop wrapper** — currently runs as a web app
- **Apartment Agent / Recipe Agent** — future House Helper agents

## License

MIT
