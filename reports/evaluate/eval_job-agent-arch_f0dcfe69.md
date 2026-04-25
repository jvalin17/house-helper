# Evaluation: Job Agent Architecture

| Field | Value |
|-------|-------|
| **Evaluated** | `architecture/job-agent.md` + `reports/architecture/arch_job-agent_3d74907d.md` |
| **Against** | `requirements/job-agent.md` + /architecture skill specification (standard mode) |
| **Date** | 2026-04-25 |
| **Overall Grade** | 19 / 22 claims passed (86%) |

## Scorecard

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | Knowledge Bank schema and endpoints cover all must-haves | :white_check_mark: PASS | `job-agent.md:98-148` — 5 tables (experiences, skills, achievements, education, projects). Endpoints at lines 345-351 cover extract, CRUD, skills list, import. |
| 2 | Resume Generation with full preference control | :white_check_mark: PASS | `job-agent.md:167-176` — resumes table has `preferences JSON` for length/tone/sections. Endpoints at 360-364 cover generate, list, get, export, feedback. |
| 3 | Cover Letter generate + edit workflow | :white_check_mark: PASS | `job-agent.md:178-188` — cover_letters table with editable content + updated_at. Endpoints at 367-372 include PUT for editing. |
| 4 | Job Input with URL fetching | :white_check_mark: PASS | `job-agent.md:70-71` — httpx + trafilatura in tech stack. Data flow at 411-417 shows URL → fetch → extract → Claude parse. |
| 5 | Application Tracking with status history | :white_check_mark: PASS | `job-agent.md:191-207` — applications table + application_status_history table. Links to resume_id and cover_letter_id. |
| 6 | Learning Loop data captured | :white_check_mark: PASS | `job-agent.md:174,185` — feedback INTEGER columns on resumes and cover_letters. Feedback endpoints at 364, 372. Applications link docs to outcomes. Requirements note says MVP = "store the data" which is covered. |
| 7 | Multi-format export architecture | :white_check_mark: PASS | `job-agent.md:277-283` — dedicated export module with base.py (protocol), pdf.py, docx.py, markdown.py, text.py. Strategy pattern. |
| 8 | Local-only storage | :white_check_mark: PASS | `job-agent.md:65,244-254` — SQLite + `~/.house-helper/` filesystem. No cloud references anywhere. |
| 9 | API key security | :white_check_mark: PASS | `job-agent.md:72` — keyring library for OS keychain. "No plaintext." |
| 10 | Data integrity (WAL mode) | :white_check_mark: PASS | `job-agent.md:65` — "WAL mode for crash safety" in tech stack. `job-agent.md:246` — WAL mode noted in storage layout. |
| 11 | Architecture pattern with reasoning | :white_check_mark: PASS | `job-agent.md:7-9` — Modular Monolith with clear reasoning (single user, local, coordinator for future agents). |
| 12 | Component diagram | :white_check_mark: PASS | `job-agent.md:13-56` — ASCII diagram showing Tauri shell, React frontend, FastAPI backend, Coordinator, Job Agent modules, external deps. |
| 13 | Tech stack table with alternatives | :white_check_mark: PASS | `job-agent.md:60-72` — 12-row table with Choice, Alternative, and Reasoning columns. |
| 14 | Decision log with dependency tracking | :white_check_mark: PASS | `job-agent.md:76-87` — 10 decisions, each with "Depends On" column referencing prior decisions by number. |
| 15 | Data flow diagrams (write, read, error paths) | :white_check_mark: PASS | `job-agent.md:408-461` — Resume Generation flow (write), Knowledge Bank Input flow (read/write), Error Flow. Three distinct paths documented. |
| 16 | Data architecture (schema, migration) | :white_check_mark: PASS | `job-agent.md:91-254` — Full SQL schema (11 tables), migration strategy with PRAGMA user_version, storage layout with directory structure. |
| 17 | API design (endpoints, error format) | :white_check_mark: PASS | `job-agent.md:337-404` — 24 endpoints across 6 resource groups. Structured error format with error codes. |
| 18 | Code structure (layout, patterns, deps) | :white_check_mark: PASS | `job-agent.md:257-335` — Full directory tree, 3 design patterns explained, dependency direction diagram. |
| 19 | Engineering principles check | :white_check_mark: PASS | `job-agent.md:463-474` — 8 principles checked (SOLID + DRY + KISS + YAGNI), all with evidence notes. |
| 20 | Parking lot | :white_check_mark: PASS | `job-agent.md:476-487` — 7 items parked with category and next step. |
| 21 | Report file created and completed | :white_check_mark: PASS | `arch_job-agent_3d74907d.md` — status "completed", all progress steps checked, 10 decisions logged, trade-offs documented. |
| 22 | Local/cheap version section | :yellow_circle: PARTIAL | No dedicated "Local/Cheap Version" section in final doc. Was mentioned verbally during quick architecture ("This already IS the local/cheap version") but omitted from the written document. Template calls for this section. |

## Detailed Findings

### :white_check_mark: Passed (19/22)

Strong coverage across all requirements and template sections. Notable strengths:

- **Requirements traceability is excellent.** Every functional requirement group from requirements/job-agent.md maps to schema tables, API endpoints, and services in the architecture. The 6 feature groups → 6 API endpoint groups → 6 service files → corresponding tables is clean 1:1 mapping.

- **User's mid-session clarification was incorporated.** The URL-fetching requirement (user said "I will paste links of job postings") was added to tech stack (httpx + trafilatura), data flow, and the jobs/parse endpoint — not just noted but fully integrated.

- **Decision dependencies are well-tracked.** Decision log shows clear chains (e.g., decisions 7→8→9→10 for API design). Report documents trade-offs accepted.

### :yellow_circle: Partial (1/22)

**Claim 22 — Local/Cheap Version section:** The /architecture skill template specifies a "Local/Cheap Version" section showing the same architecture with free/local alternatives. During the interactive session, this was addressed verbally ("This already IS the local/cheap version") which is accurate — but the final document doesn't include this as a section. A one-line note in the doc would suffice.

### :red_circle: Failed (0/22)

None.

### :white_circle: Unable to Verify (2 notes)

- **Portability:** Requirements specify "User can backup/restore by copying the data directory." The storage layout (`~/.house-helper/`) implicitly supports this, but there's no explicit mention of portability or backup strategy in the architecture doc. Not a claim failure since it's an NFR, not an architecture decision — but worth noting.

- **Learning loop flow:** The data model stores all the signals (feedback columns, application status, linked docs), but there's no service or data flow described for *querying* correlations during future generation. Requirements say MVP = "store the data" so this is fine, but when it becomes a real feature, it'll need its own architecture section.

## User Observations

The user provided significant UI/UX requirements not covered by the backend-focused architecture (which explicitly parked frontend architecture). These should feed into a future `/requirements` or design phase for the frontend:

1. **Agent selector landing page** — page 1 is "pick your agent," each agent has its own flow
2. **Batch job link input** — accept multiple URLs at once, not one at a time
3. **Three input modes** — paste links | paste description | preference-based search (future API mode)
4. **Light, uplifting color scheme** — lighter colors, not depressing
5. **Preview before apply** — show resume + cover letter previews before confirming application
6. **Apply confirmation UX** — "Thank you for applying to [Company]" message after tracking
7. **Application tracker dashboard** — visual job application tracker

**Impact on architecture:** These don't invalidate any backend decisions. The batch URL input means `/api/jobs/parse` should accept a list of URLs (minor endpoint tweak). The preview flow is already supported by existing GET endpoints. The tracker dashboard is a frontend concern.

## Recommendations

1. **Add a one-line "Local/Cheap Version" note** to the architecture doc: "This is inherently a local/cheap architecture — SQLite (free), filesystem storage, OS keychain. The only external cost is Claude API usage."

2. **Consider adding a portability note** to the Storage Layout section: "Backup by copying `~/.house-helper/`. Restore by placing it back."

3. **No blockers** — the architecture is ready to feed into `/implementation job-agent`.
