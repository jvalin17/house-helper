# Panini — Handoff Document

> Last updated: 2026-05-18
> Current version: v1.2.0 (release building)
> Branch: main

---

## What We Are Building

**Panini** is a multi-agent AI desktop app (Python/FastAPI + React/TypeScript + Tauri) with two specialized agents:

1. **Jobsmith** — Autonomous job search + auto-apply agent
2. **NestScout** — Apartment search + premium intelligence + dashboard

The app runs as a desktop app (Tauri sidecar) or locally via dev servers. All data stays local (SQLite). All behavioral data encrypted at rest.

---

## Current State

### What Works

| Feature | Agent | Status | Notes |
|---------|-------|--------|-------|
| Natural language job search | Jobsmith | Working | "remote sdet jobs in austin 120k+" |
| Multi-source search (LinkedIn, Indeed, Adzuna, Google Jobs) | Jobsmith | Working | Cross-search dedup |
| Smart ranking (term-based behavioral learning) | Jobsmith | Working | Encrypted at rest |
| Consultancy/staffing filter (30+ companies) | Jobsmith | Working | |
| Auto-resume generation (DOCX) | Jobsmith | Working | Evidence-based, no fabrication |
| Auto-apply pipeline | Jobsmith | Working | Confirmation-first, no Playwright yet |
| Saved resumes (max 5, curated) | Jobsmith | Working | Named `resume_26_v1` |
| Knowledge bank (import/extract/edit) | Jobsmith | Working | DOCX/PDF/TXT/URL |
| Apartment search | NestScout | Working | RealtyAPI + RentCast + dedup |
| Nest Lab (AI analysis, tags, cost calc) | NestScout | Working | |
| Nest Intel (9-source premium intelligence) | NestScout | Working | Multi-hop pipeline, grid caching |
| Intel visual overhaul | NestScout | Working | Squares grid, plain language, expandable cards |
| Dashboard: funnel + stats + cards | NestScout | Working | 7 slabs built |
| Dashboard: visit notes + observations | NestScout | Working | Auto-save, 800ms debounce |
| Dashboard: photo gallery + AI analysis | NestScout | Working | Upload, lightbox, vision LLM |
| Dashboard: achievements + celebrations | NestScout | Working | CSS confetti, 7 badges |
| Dashboard: budget reality check | NestScout | Working | Compromise explorer |
| Central settings (all API keys) | Shared | Working | Hot reload |
| Master API kill switch | Shared | Working | Toggle all sources on/off |
| Three LLM modes (No/Offline/Online) | Shared | Working | |
| Token budget management | Shared | Working | Per-request + daily |

### What Does NOT Work / Known Issues

| Issue | Severity | Details |
|-------|----------|---------|
| Auto-apply form filling | Not built | Playwright browser automation not integrated |
| macOS Intel desktop build | Dropped | macos-13 runner stuck, macos-14 can't cross-compile PyInstaller x86 |
| First-request 500 on listings | Intermittent | `dict(row)` IndexError on first call after startup, works on retry — likely migration race |
| Ollama for generation | Slow | Works for PDF import only, too slow for analysis |
| Cost tracking accuracy | ~70% | Word-count heuristics, not token-exact |
| v1.2.0 release | **Published** | Windows MSI + macOS ARM DMG + Linux DEB all passed |
| Frontend test path aliases | Broken | 6-8 test files with `@/` imports fail in CI but pass locally |

---

## Reference Documents

### Requirements
| File | What it covers |
|------|---------------|
| `requirements/apartment-finder-agent.md` | NestScout full requirements |
| `requirements/nest-intel.md` | 9-source Intel pipeline requirements |
| `requirements/nestscout-dashboard.md` | Dashboard tab requirements (funnel, cards, photos, achievements, budget) |
| `requirements/smart-ranking.md` | Term-based behavioral learning requirements |
| `requirements/unified-credential-store.md` | Central settings / API key management |

### Architecture
| File | What it covers |
|------|---------------|
| `architecture/apartment-finder-agent.md` | NestScout overall architecture |
| `architecture/nest-intel.md` | Intel pipeline architecture (multi-hop, caching, encryption) |
| `architecture/nestscout-dashboard.md` | Dashboard 7-slab architecture (the most detailed — diagrams, data flow, component tree) |
| `architecture/smart-ranking.md` | Ranking engine architecture |
| `architecture/repo-structure.md` | Project structure decisions |

### Reports
| File | What it covers | Status |
|------|---------------|--------|
| `reports/evaluate/eval_nestscout_dashboard_b2e4f91a.md` | Dashboard evaluation — post quality fixes | Current |
| `reports/evaluate/eval_nestscout_dashboard_c8a19f42.md` | Dashboard evaluation — mid-build | Stale |
| `reports/evaluate/eval_nestscout_dashboard_d5f72e31.md` | Dashboard evaluation — pre-implementation (design phase) | Stale |
| `reports/reviewer/review_nestscout_dashboard_a7f3c8d1.md` | Dashboard code review (22 findings, all resolved) | Stale — pre-implementation |

### Other
| File | What it covers | Status |
|------|---------------|--------|
| `DECISIONS.md` | Cross-cutting architectural decisions | **Stale** — last updated Apr 30, predates Intel/Dashboard/ranking |
| `skills-feedback.md` | Feedback on Claude Code skills for future improvement | Current |
| `README.md` | User-facing docs, download links, feature list | Current |

### Stale Docs That Need Updating
- **`DECISIONS.md`** — Missing decisions for: Intel pipeline, smart ranking, dashboard, API kill switch, place caching, encryption approach
- **`architecture/apartment-finder-agent.md`** — Only 129 lines. Doesn't cover Intel, Dashboard, or any shared intelligence modules. Needs rewrite to reflect current 50+ endpoint, 18-service architecture
- **`reports/evaluate/` and `reports/reviewer/`** — All pre-implementation. Need a fresh `/evaluate` and `/reviewer` run against the built code

---

## Skills Used

These agent-toolkit skills drive the development workflow:

| Skill | When to use |
|-------|-------------|
| `/requirements` | Before building any new feature — scopes capabilities, user stories, priorities |
| `/architecture` | After requirements — tech decisions, data flow, component design, slab breakdown |
| `/implementation` | Build phase — TDD cycles, one slab at a time, verify before commit |
| `/evaluate` | After implementation — scores completeness, code quality, security, tests, efficiency |
| `/precommit` | Before every commit — instruction compliance, test audit, standards check |
| `/assess` | Architecture health check — anti-patterns, scale thresholds, refactoring plan |
| `/reviewer` | Deep code review — quality, tests, runtime, accessibility, dependencies |

**Quality gates:** Never commit unless `/evaluate` scores 95%+ or user explicitly approves. Always run `/precommit` before committing.

---

## What We Are Working On Now

### Completed this session:
1. Intel quality fixes (N+1 queries, batch inserts, coordinate validation, visual polish)
2. Master API kill switch (toggle all sources on/off from Settings)
3. NestScout Dashboard — all 7 slabs:
   - Slab 1: DB migration v12, PhotoRepository, DashboardService
   - Slab 2: 15 API endpoints (funnel, stats, advance, notes, photos, archive)
   - Slab 3: Frontend types, API client, dashboard tab skeleton
   - Slab 4: Expanded cards, visit notes, observation toggles, cost summary
   - Slab 5: Photo gallery, AI vision analysis, photo analyzer
   - Slab 6: HuntFunnel SVG, stats strip, achievement badges, celebration overlay
   - Slab 7: CompromiseService, SearchProfileCard, CompromiseExplorer
   - Quality fixes: split oversized components, lightbox, photo limit, test gaps
4. CI fixes (unused TS variables, macOS runner migration)
5. README fixes (no versioned download URLs)

### Release status: v1.2.0 PUBLISHED
- Windows MSI: **PASSED** — `Panini_1.2.0_x64_en-US.msi`
- macOS ARM DMG: **PASSED** — `Panini_1.2.0_aarch64.dmg`
- Linux DEB: **PASSED** — `Panini_1.2.0_amd64.deb`
- macOS Intel: **Dropped** (macos-13 runner unavailable, macos-14 can't cross-compile)
- Download: https://github.com/jvalin17/house-helper/releases/tag/v1.2.0

---

## What To Build Next

### Immediate (high priority)
1. **Fix intermittent first-request 500** — `listing_repo.list_listings()` IndexError on startup. Investigate migration race or stale connection.
2. **Commute Grid feature** — Highway-based pre-computed commute data (see `memory/project_commute_grid.md`). Needs `/requirements` first. Design: sample MoPac/I-35/183/360/290 corridors, hourly toll vs non-toll, interpolate for any property within 5-7mi.
3. **Auto-apply Playwright integration** — Requirements paused (5 questions pending in `memory/project_playwright_pending.md`). This is the MAIN GOAL of Jobsmith.

### Medium priority
4. **Intel visual improvements** — User wants more visualization, less raw data. Commute should come from LLM insights, not a "workplace" setting.
5. **Interactive map** — Show nearby places on a map with distance rings.
6. **PDF export for Intel reports** — Generate shareable property report.
7. **LLM gap analysis** — "You want X roles but lack Y — here's your action plan."

### Low priority / Future
8. **Travel agent** — Reuse `shared/intelligence/` modules (place discovery, caching, distance calc) for a travel planning agent.
9. **Docker deployment** — For non-desktop users.
10. **macOS Intel build** — Need a workaround for PyInstaller cross-compilation.

---

## Test Coverage

| Suite | Count | Command |
|-------|-------|---------|
| Backend (pytest) | 1381 passed, 29 skipped | `.venv/bin/python -m pytest tests/ -x -q` |
| Frontend (vitest) | 280 passed | `cd frontend && npx vitest run` |
| **Total** | **1661** | `./test.sh` |

---

## Key Technical Details

### Database
- SQLite with WAL mode, 12 migrations (v1-v12)
- Migrations run automatically on startup in `shared/db.py`
- Key tables: apartment_listings, apartment_notes, apartment_cost, apartment_intel, apartment_visit_photos, place_cache, ranking_interactions, api_credentials

### Backend Architecture
- `backend/main.py` → FastAPI app with lifespan, Coordinator pattern
- `backend/coordinator.py` → Routes requests to job/apartment agents
- `backend/agents/job/` → Jobsmith (93 endpoints)
- `backend/agents/apartment/` → NestScout (~50 endpoints)
- `backend/shared/` → LLM providers, ranking engine, intelligence modules, credentials

### Frontend Architecture
- `frontend/src/pages/` → Home, JobDashboard, ApartmentDashboard, GlobalSettings
- `frontend/src/components/apartment/` → tabs/ (Search, Lab, Dashboard, Settings), dashboard/ (14 components), lab/ (Intel, Badge, helpers)
- `frontend/src/api/client.ts` → Typed API client (all backend communication)
- `frontend/src/types/index.ts` → Shared TypeScript interfaces

### Shared Intelligence Modules (reusable across agents)
- `shared/intelligence/place_discovery.py` — Google Nearby Search with grid caching
- `shared/intelligence/place_deep_dive.py` — Fetch reviews per place, newest 20%
- `shared/intelligence/place_cache.py` — Grid-based geographic cache, encrypted reviews
- `shared/intelligence/distance_calculator.py` — Haversine distance, radius bucketing

### User Preferences (from memory)
- Python-primary dev, Java secondary, new to TypeScript
- Light colors, indigo theme, preview-before-action UX
- No single-letter variables, no abbreviations — full descriptive names always
- Privacy-first: all behavioral data encrypted, zero developer access
- Quality bar: no gaps, 95%+ on evaluate before committing
- One feature at a time, design before building, use skills properly

---

## How To Start Development

```bash
# Backend
cd house-helper
.venv/bin/uvicorn main:app --port 8040 --reload --app-dir backend

# Frontend (separate terminal)
cd house-helper/frontend
npm run dev

# Open http://localhost:5173
```

### Running tests
```bash
.venv/bin/python -m pytest tests/ -x -q     # backend
cd frontend && npx vitest run                 # frontend
```

### Creating a release
```bash
git tag -a v1.X.0 -m "v1.X.0: description"
git push origin v1.X.0
# GitHub Actions builds Windows MSI + macOS DMG + Linux DEB
```

---

## Memory System

Persistent memory across conversations at:
`~/.claude/projects/-Users-jvalin-dev-st5-house-helper/memory/`

Key memory files:
- `user_smart_ideas.md` — 28 design insights for interview stories
- `project_commute_grid.md` — Highway-based commute estimation design
- `feedback_readme_no_versioned_urls.md` — Never put versioned URLs in README
- `feedback_never_commit_without_eval.md` — 95%+ evaluate before commit
- `feedback_security_approach.md` — Floodgate validation pattern, no new deps
- `feedback_privacy_first.md` — All behavioral data encrypted at rest

See `MEMORY.md` for the full index.
