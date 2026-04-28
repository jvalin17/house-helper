# House Helper — Job Agent

A desktop app that searches for jobs, scores them against your experience, generates tailored resumes and cover letters, and tracks your applications. Works with or without AI.

## What It Does

**Search** — Scout jobs from LinkedIn, Indeed, Glassdoor, Adzuna, and RemoteOK using official APIs. Filter by title, location, keywords, and remote preference. Results auto-sorted by match score.

**Match** — Score every job against your knowledge bank. Algorithmic matching (skill overlap, text similarity, semantic matching, experience years) works offline. Add an LLM for deeper analysis with strengths, gaps, and recommendations.

**Tailor** — Analyze your resume fit before generating. See your current match %, what your knowledge bank could achieve, and pick which improvements to apply. Flag bad suggestions so the LLM never repeats them.

**Generate** — Tailored resume + cover letter per job. Your original DOCX formatting is preserved (fonts, bold, bullet styles, spacing). Export as PDF, DOCX, or Markdown. Cover letters address specific gaps honestly — never fabricate experience.

**Refine** — Type custom instructions on the result page to iterate: "Show 6 years only", "Focus on backend", "Remove projects section". Regenerate without starting over.

**Apply** — The Launchpad runs the full pipeline: search, match, generate, and prepare applications for your top matches. Track every application on a kanban board (Applied / Interview / Offer / Rejected).

**Learn** — Rate matches to calibrate the scoring algorithm. Flag incorrect suggestions. The system learns your preferences over time.

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
cd backend && uvicorn main:app --port 8040 --reload

# Terminal 2 — Frontend
cd frontend && npm run dev
```

Open **http://localhost:5173**

### Ollama (optional, free local AI)

```bash
brew install ollama && ollama serve
ollama pull mistral
```

Ollama is used automatically for PDF resume import extraction — no configuration needed. Resume analysis and generation require a cloud LLM (see below).

### API Keys (optional)

Edit `.env` to enable features:

| Key | What it enables | Where to get it |
|-----|----------------|-----------------|
| `ANTHROPIC_API_KEY` | AI resume generation, LLM matching | [console.anthropic.com](https://console.anthropic.com/) |
| `OPENAI_API_KEY` | Alternative AI provider | [platform.openai.com](https://platform.openai.com/) |
| `DEEPSEEK_API_KEY` | Budget AI provider (~10x cheaper) | [platform.deepseek.com](https://platform.deepseek.com/) |
| `RAPIDAPI_KEY` | Job search via JSearch (LinkedIn, Indeed, Glassdoor) | [rapidapi.com/jsearch](https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch) |

The app works without any API keys — you get algorithmic matching and template-based generation for free. AI features activate when you add a key and select a provider in Settings.

## Workflows

### 1. First-Time Setup

1. Open the app and go to **Superpower Lab**
2. Import your resume (drag-and-drop or click to browse — DOCX, PDF, TXT)
3. A resume template is created automatically (preserves your DOCX formatting)
4. Skills, experiences, education, and projects are extracted into the Knowledge Bank
5. Import a second resume — both coexist as templates, knowledge bank merges unique bullets

### 2. Search and Tailor

1. Go to **Job Search** tab
2. Enter filters (or leave empty — defaults to your skills + US location)
3. Click **Scout Jobs** to search across connected job boards
4. Click **Match All (local)** to score every result against your knowledge bank
5. Select specific jobs and click **Evaluate Selected (AI)** for deeper LLM analysis
6. Click **Tailor Resume** on any job:
   - AI analyzes your fit — shows algorithmic score, LLM analysis, KB potential
   - Pick which suggested improvements to apply (checkboxes)
   - Flag bad suggestions (they won't appear again)
   - Type custom instructions ("Show 6 years only", "Focus on backend")
   - AI generates resume + cover letter using your selections
   - Review and type adjustments to regenerate without starting over
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
4. Select improvements, add custom instructions, then **Apply & Generate**
5. Download the tailored resume and cover letter

### 5. Add Knowledge

- **Import resume** — DOCX, PDF, or TXT. Skills and experiences extracted automatically.
- **Paste a link** — GitHub, LinkedIn, portfolio site. Page fetched and skills extracted.
- **Paste text** — free text about your experience. Skills extracted with accept/deny toggles.
- **Multiple imports merge** — same company/role merges unique bullets, doesn't duplicate.

### 6. Track Applications

- **Dashboard** tab shows a kanban board: Applied / Interview / Offer / Rejected
- Click any card to expand timeline, linked resume/cover letter, and status history
- Move cards between columns as your application progresses

## LLM Modes

The app uses LLMs for two distinct tasks with different requirements:

### Resume Analysis & Generation (requires strong LLM)

Resume analysis, fit scoring, and tailored generation need a capable model. **Ollama/local models are too slow and unreliable for this.** Use one of:

| Provider | Model | Cost | Quality |
|----------|-------|------|---------|
| **Claude** (Anthropic) | Sonnet 4, Opus 4 | ~$0.006/resume | Best |
| **OpenAI** | GPT-4o, GPT-4.1 | ~$0.005/resume | Great |
| **DeepSeek** | DeepSeek-V3 | ~$0.002/resume | Good (budget pick) |
| **Google** | Gemini 2.0 Flash | ~$0.001/resume | Good |
| **Grok** (xAI) | Grok-2 | ~$0.005/resume | Good |

### PDF Import Extraction (free, local)

When importing a PDF resume, the app automatically uses **Ollama** (if running locally) to extract structured data. Falls back to algorithmic parsing if Ollama isn't available. This costs nothing.

### No LLM Mode

Everything works without any LLM — algorithmic matching (TF-IDF, skill overlap, semantic similarity) and template-based generation are free and offline.

Switch providers in Settings without restarting. API keys persist across model switches.

## Key Features

### DOCX Format Preservation

When you import a DOCX resume, the app stores the original file and builds a paragraph map. During generation, the LLM's content decisions are applied surgically — replacing only the text of specific paragraphs while preserving all formatting (fonts, bold, colors, spacing, bullet styles, centering). The exported DOCX looks like your original resume with only the content changed.

### Multi-Resume Templates

Store up to 5 resume files as generation templates. Each import creates a template entry. Set a default — generation uses that template's format. Switch defaults in the Templates section under My Superpowers.

### Suggestion Feedback

Flag incorrect LLM suggestions (e.g., "Emphasize LLM sentiment analysis" when the work wasn't LLM-related). Flagged suggestions are stored locally and fed back to the LLM prompt so it doesn't repeat them. The filter also catches similar rephrasings.

### Custom Instructions

Type instructions on the analysis screen or the result page:
- "Show only 6 years of experience"
- "Focus on backend, skip frontend work"
- "Target as mid-level role, not senior"
- "Remove projects section"

Instructions are passed directly to the LLM alongside your selected improvements.

### Knowledge Bank Merge

Import multiple resumes — the knowledge bank merges them intelligently. Same company/role/dates = merge unique bullet points. Different companies = add normally. Skills deduplicated by name. Education deduplicated by institution.

### Link Extraction

Paste a GitHub, LinkedIn, or portfolio URL into the "Add Knowledge" section. The app fetches the page, extracts text, and identifies skills. Accept or deny each skill before saving.

### Budget & Cost Tracking

- Set a daily spending limit in Settings
- Real-time cost tracking refreshes automatically (per-feature breakdown)
- Cost-per-resume estimates shown for each model
- AI features pause when the limit is reached

### Match Scoring Progression

After generating, you see a clear progression:

```
55%              →   68%                    →   85%                   →   78%
Algorithmic          LLM analysis               Knowledge bank            Generated resume
                     (current resume)            potential
```

Plus a breakdown of algorithmic features (skills match, experience, text similarity, semantic).

### Export Formats

- **PDF** — one page, professional formatting, bold categories and role headers
- **DOCX** — preserves your original resume's exact formatting via DOCX surgery
- **Markdown** — plain text, version-controllable

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLite (WAL mode) |
| Frontend | React, TypeScript, Vite, shadcn/ui |
| LLM | Claude, OpenAI, DeepSeek, Grok, Gemini, Ollama (hot-reload) |
| ML | Sentence Transformers, spaCy (optional) |
| Resume | python-docx (DOCX surgery), WeasyPrint (PDF), PyMuPDF (PDF parsing) |
| Desktop | Tauri 2.0 (planned) |

All backend HTTP calls are synchronous — async + FastAPI thread pool caused silent failures. This is intentional.

## Testing

```bash
./test.sh    # runs backend + frontend tests + build check
```

368 backend tests, 21 frontend tests. Or individually:

```bash
# Backend
source .venv/bin/activate
python -m pytest tests/ -q -m "not network and not live"

# Frontend
cd frontend && npx vitest run

# With real resume files
TEST_RESUME_PDF=/path/to/resume.pdf TEST_RESUME_DOCX=/path/to/resume.docx \
  python -m pytest tests/test_real_resume_import.py -v -s

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
        resume.py                 #   DOCX surgery + template assembly
        knowledge.py              #   Resume import + KB merge + LLM extraction
        job_matcher.py            #   Algorithmic + LLM scoring
        suggestion_filter.py      #   Filters rejected suggestions
        auto_search.py            #   Job board search with dedup
        cover_letter.py           #   Cover letter generation
      prompts/                    # LLM prompt templates
        analyze_fit.py            #   Pre-generation analysis (with rejections)
        generate_resume.py        #   Resume content decisions (with user instructions)
        parse_resume.py           #   LLM-based resume parsing (for PDFs)
        extract_skills.py         #   Skill extraction with guardrails
        match_job.py              #   Deep match analysis
      repositories/               # SQLite data access
        template_repo.py          #   Resume templates (up to 5)
        feedback_repo.py          #   Suggestion rejections
        knowledge_repo.py         #   Knowledge bank CRUD
        job_repo.py               #   Jobs
        resume_repo.py            #   Generated resumes
    shared/
      db.py                       # SQLite, 3 migrations, auto-migration
      docx_surgery.py             # Paragraph map + format-preserving text replacement
      llm/                        # Provider abstraction (lazy-load, hot-reload)
        claude.py, openai.py      #   Cloud providers
        ollama.py                 #   Local provider (free)
        lazy_provider.py          #   Hot-reload + usage logging
        pricing.py                #   Per-model cost estimation
        factory.py                #   Provider creation from config
      algorithms/                 # Pure Python TF-IDF, skill matcher, semantic
      job_boards/                 # Plugin system (JSearch, Adzuna, RemoteOK)
      export/                     # PDF (WeasyPrint), DOCX (python-docx), Markdown
      scraping/                   # URL fetcher, HTML extractor, resume parser
      calibration/                # Match weight learning from user ratings
  frontend/
    src/
      pages/                      # Home, JobDashboard
      components/
        tabs/                     # JobSearchTab, ResumeBuilderTab
        ErrorBoundary.tsx         # Catches render crashes
        PreviewModal.tsx          # Analyze → select → generate → refine → download
        ResumeAnalysis.tsx        # Fit analysis, suggestions, flag incorrect, instructions
        KnowledgeBank.tsx         # Templates, experiences, skills, link extraction
        ApplyPipeline.tsx         # The Launchpad (auto-apply)
        ApplicationTracker.tsx    # Kanban board
        Settings.tsx              # Provider, budget, sources, calibration
      api/client.ts               # API client with error handling
  tests/                          # 368 backend tests
    test_docx_surgery.py          # 22 tests: paragraph map, text replacement, formatting
    test_knowledge_merge.py       # 7 tests: bullet merge, skill dedup, education dedup
    test_suggestion_feedback.py   # 9 tests: rejection storage, filtering, Zillow scenario
    test_resume_templates.py      # 9 tests: CRUD, max 5, auto-default, delete promotion
    test_template_integration.py  # 8 tests: import→template, generate uses template, switch
    test_user_instructions.py     # 5 tests: instructions in prompt, empty handling
    test_pdf_parsing.py           # 25 tests: bullet joining, date handling, HTML conversion
    test_llm_providers.py         # 19 tests: factory, pricing, all providers
    test_real_resume_import.py    # 11 tests: real DOCX/PDF import (env var paths)
  setup.sh                        # One-command setup
  test.sh                         # Run all tests
  .env.example                    # API key template
  skills-feedback.md              # 89+ battle-tested lessons
```

## Not Yet Built

- **Browser form filling** — Playwright automation to fill and submit job application forms
- **Prompt caching** — Anthropic cache for knowledge bank (saves ~30% on input tokens)
- **Local ML matcher** — learns from LLM decisions to reduce API costs (needs 20+ data points)
- **Tauri desktop wrapper** — currently runs as a web app
- **Apartment Agent / Recipe Agent** — future House Helper agents

## License

MIT
