# Session 7 — Pick-up Plan

> Date: 2026-04-28
> Previous: Session 6 completed Phase 1 (real data) + Phase 2 (LLM connected)

## What works right now

| Feature | Status |
|---------|--------|
| Scout Jobs (JSearch API) | Working — 30 results, ~3 seconds |
| Import resume (drag-drop) | Working — dedup on education/projects |
| Knowledge bank CRUD | Working |
| Match All (local) | Working — algorithmic, instant, free |
| Evaluate Selected (AI) | Working — Claude deep match on checked jobs |
| Resume generation (Claude) | Working — but uses wrong format (see bugs) |
| Cover letter generation | Working |
| Export PDF/DOCX/MD | Working |
| Settings — provider picker | Working — hot-reload, no restart needed |
| Settings — model picker with pricing | Working |
| Settings — budget limit | Working — $0.50/day default |
| Tab state persistence | Working — search results survive tab switch |
| Application tracker | Working |

## Bugs to fix first (30 min)

- [ ] **Resume format** — Claude generates "Staff Software Engineer" and wrong structure. Should follow user's original resume format. Code fix is in (prompt updated) but needs testing with real data.
- [ ] **Settings UI sometimes blank** — Promise.all was fixed to load independently, but verify after fresh start.
- [ ] **Scout Jobs first search slow** — may need to verify dedup logic isn't scanning full DB on each result.

## Carryover from Session 6

- [ ] **Phase 3: Playwright form filling** — not started. This is the big remaining feature.
  - Install: `pip install playwright && playwright install chromium`
  - Build form detector, field mapper, user confirmation flow
  - Start with ONE simple job site (Greenhouse or Lever hosted)

## New items from Session 6

- [ ] **Resume should follow user's uploaded format** — prompt was updated but not tested. Test: import resume → generate for a job → verify same section order, real name, real titles.
- [ ] **Local ML matcher** — `local_matcher.py` is built, needs training data. After 20+ AI matches, train local model to reduce LLM costs.
- [ ] **Ollama setup** — provider built, detection endpoint ready. Need to install Ollama and test: `brew install ollama && ollama pull llama3.1`
- [ ] **Frontend cleanup** — 6 components over 200 lines, 22 unsafe casts. Don't do during features — schedule as separate cleanup session.

## Priorities for Session 7

### Priority 1: Test resume format fix (15 min)
```bash
cd /Users/jvalin/dev/st5/house-helper && ./restart.sh
# Import resume
curl -s -X POST http://localhost:8040/api/knowledge/import \
  -F "file=@/Users/jvalin/Downloads/resume_26/Resume_Backend_SWE.docx"
# Search for a job
# Go to Superpower Lab → Resume Builder → pick a job → Generate
# Verify: same format as original resume, real name, real titles
```

### Priority 2: Playwright form filling (2-3 hours)
```bash
source .venv/bin/activate
pip install playwright
playwright install chromium
```

Build in order:
1. `backend/shared/form_filler.py` — opens URL, scans for input fields
2. Field mapper — maps knowledge bank to form fields
3. User confirmation — browser stays visible, user handles CAPTCHAs
4. API endpoint — `POST /api/apply/fill-form`
5. Frontend — "Open & Fill" button in pipeline
6. Test with ONE real job application page

### Priority 3: Ollama local LLM (30 min)
```bash
brew install ollama
ollama pull llama3.1  # ~4.7GB download
ollama serve          # runs on localhost:11434
```
Then in Settings: select Ollama → llama3.1 → Save → Generate resume → compare quality.

### Priority 4: Frontend cleanup (if time)
Run /simplify on:
- ApplyPipeline.tsx (362 lines → split)
- Settings.tsx (307 lines → split)
- KnowledgeBank.tsx (298 lines → split)

## Quick test commands

```bash
# Fresh start
cd /Users/jvalin/dev/st5/house-helper && ./reset.sh

# Restart only
./restart.sh

# Import resume
curl -s -X POST http://localhost:8040/api/knowledge/import \
  -F "file=@/Users/jvalin/Downloads/resume_26/Resume_Backend_SWE.docx" | \
  python3 -c "import sys,json; print(json.load(sys.stdin))"

# Test search
curl -s -X POST http://localhost:8040/api/search/run \
  -H "Content-Type: application/json" \
  -d '{"title":"Backend Engineer"}' | \
  python3 -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"jobs\"])} jobs')"

# Check LLM status
curl -s http://localhost:8040/api/settings/llm/status

# Check all systems
curl -s http://localhost:8040/health && echo "" && \
curl -s http://localhost:8040/api/settings/llm/status && echo "" && \
curl -s http://localhost:8040/api/search/sources | \
  python3 -c "import sys,json; [print(f'  {s[\"id\"]}: {s[\"is_available\"]}') for s in json.load(sys.stdin)]"
```

## Notes

- Python 3.12 in venv (sentence-transformers + spaCy work)
- JSearch API key in .env (seeded to DB on startup)
- Claude API key in .env (active as default LLM)
- OpenAI API key in .env (switchable in Settings)
- Resume at: `/Users/jvalin/Downloads/resume_26/Resume_Backend_SWE.docx`
- 250 backend tests, 0 skipped
- REMEMBER: rotate API keys — they were pasted in chat

## Key files changed in Session 6

| File | What changed |
|------|-------------|
| `shared/db.py` | Normalized to 17 tables, profiles added |
| `shared/llm/lazy_provider.py` | NEW — hot-reload LLM without restart |
| `shared/llm/pricing.py` | NEW — model catalog with costs |
| `shared/algorithms/local_matcher.py` | NEW — learns from LLM to reduce costs |
| `agents/job/prompts/generate_resume.py` | Rewritten — follows user's original format |
| `agents/job/services/auto_search.py` | Fixed async, removed auto LLM, dedup |
| `frontend/src/components/Settings.tsx` | Provider status, model picker, budget |
| `frontend/src/components/tabs/JobSearchTab.tsx` | Evaluate Selected, removed Parse slab |
