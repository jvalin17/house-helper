# Session 6 — Pick-up Plan

> Date: 2026-04-26
> Goal: Test with real data, connect LLM, start Playwright form filling

## Pre-flight (5 min)

- [ ] Start app: `./start.sh`
- [ ] Open http://localhost:5173
- [ ] Verify clean session (no stale jobs from previous sessions)

## Phase 1: Real Data Test (30 min)

### 1a. Import resume
- [ ] Go to Superpower Lab → My Superpowers
- [ ] Drag-drop `/Users/jvalin/Downloads/resume_26/Resume_Backend_SWE.docx`
- [ ] Verify: experiences (Zillow, Dematic), skills (Java, Python, etc.), education (UTA, Pune)
- [ ] If parsing issues → fix `resume_parser.py`

### 1b. Search real jobs
- [ ] Go to Job Search tab
- [ ] Fill filters: Title="Backend Engineer", Location="Austin, TX", Remote=checked
- [ ] Click "Scout Jobs" → should hit RemoteOK (works without key)
- [ ] Verify: real jobs appear in results
- [ ] Optional: sign up for free JSearch key at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch → set `RAPIDAPI_KEY` env var → retry search

### 1c. Run the pipeline
- [ ] Click "Do the Magic"
- [ ] Verify: pipeline animates through all 6 stages
- [ ] Verify: match percentages reflect your actual skills (Python/Java should match high)
- [ ] Verify: generated resume contains YOUR experience, not template placeholder
- [ ] Check: resume on Resume Builder tab shows content

### 1d. Export and review
- [ ] Generate a resume for a specific job on Resume Builder tab
- [ ] Export as PDF → open and review
- [ ] Export as DOCX → open and review
- [ ] Is the content accurate? Any fabrication? Missing sections?

## Phase 2: Connect Claude (15 min)

- [ ] Go to Settings tab
- [ ] Select Claude provider
- [ ] Enter API key (or set `ANTHROPIC_API_KEY` env var and restart)
- [ ] Save
- [ ] Restart backend: `lsof -ti:8040 | xargs kill -9; cd backend && uvicorn main:app --reload --port 8040`
- [ ] Go to Resume Builder → generate for same job as Phase 1
- [ ] Compare: template resume vs Claude-generated resume
- [ ] Compare: template cover letter vs Claude-generated cover letter
- [ ] Check token budget: Settings should show usage

## Phase 3: Playwright Form Filling (2-3 hours)

### 3a. Setup (10 min)
```bash
source .venv/bin/activate
pip install playwright
playwright install chromium
```

### 3b. Build form detector (45 min)
- [ ] New file: `backend/shared/form_filler.py`
- [ ] Playwright opens a URL
- [ ] Scans page for input fields: name, email, phone, resume upload, cover letter, LinkedIn URL
- [ ] Returns list of detected fields with selectors
- [ ] Test with one real job application page

### 3c. Build field mapper (30 min)
- [ ] Map knowledge bank → form fields
  - name → name input
  - email → email input
  - phone → phone input
  - resume PDF → file upload input
  - LinkedIn URL → LinkedIn input
- [ ] Fill detected fields with mapped data
- [ ] Don't click submit — just fill

### 3d. User confirmation flow (30 min)
- [ ] Browser stays visible (headful mode, not headless)
- [ ] After filling: pause and wait for user
- [ ] User reviews filled form
- [ ] User handles CAPTCHAs manually
- [ ] User clicks submit themselves
- [ ] After submit: mark as applied in tracker

### 3e. Wire to API (30 min)
- [ ] New endpoint: `POST /api/apply/fill-form` with job_id
- [ ] Opens Playwright browser
- [ ] Fills form
- [ ] Returns status
- [ ] Frontend: "Open & Fill" button in pipeline, replaces "Open Application"

### 3f. Test with ONE real job
- [ ] Find a simple single-page application form (not LinkedIn, not Workday)
- [ ] Run form filler
- [ ] Verify fields get filled correctly
- [ ] Manually submit if everything looks right

## Phase 3 Target Site

Pick ONE of these (simplest forms):
- A direct company career page (greenhouse.io hosted)
- Lever.co hosted pages
- Simple "email your resume" jobs

**Avoid for now:**
- LinkedIn Easy Apply (needs login session)
- Workday (multi-page wizard)
- Taleo (legacy, complex)

## Success Criteria

By end of session 6:
- [ ] Real resume imported, real jobs found, real match scores
- [ ] Claude-generated resume that's genuinely good
- [ ] Can open ONE job site, form pre-filled with your data, you click submit
- [ ] At least 1 real application submitted using the tool

## If time runs out

Priority order (do as far as you get):
1. Phase 1 (real data test) — must do
2. Phase 2 (connect Claude) — should do
3. Phase 3a-3b (Playwright setup + detector) — start if possible
4. Phase 3c-3f (mapper + UI + real test) — session 7

## Notes from previous sessions

- Backend port: 8040
- Frontend port: 5173
- Python 3.12 in venv (sentence-transformers + spaCy work)
- JSearch API connected (RapidAPI key in .env)
- Resume at: `/Users/jvalin/Downloads/resume_26/Resume_Backend_SWE.docx`
- Sample job URLs tested: Snowflake, Meta (both work with JSON-LD extraction)

## Future: Frontend Cleanup Session

Run /simplify or /code-reviewer on frontend. Issues found:
- 6 components over 200 lines (split into sub-components)
- 22 `as unknown as` casts (replace with runtime type guards)
- State variable naming inconsistencies
- ApplyPipeline.tsx (362 lines) — break into PipelineStages + PipelineBatch + PipelineSummary
- Settings.tsx (307 lines) — break into ProviderSettings + BudgetSettings + SourceSettings
- KnowledgeBank.tsx (298 lines) — break into ExperienceList + SkillList + EducationList
