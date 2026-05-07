# Skills Feedback — From Real-World Usage on Panini (house-helper)

Used all skills extensively over 3 days building NestScout, Nest Intel, Jobsmith enhancements, and Smart Ranking. Here's what works, what's broken, and specific improvements.

---

## Critical: No Auto-Update Mechanism

The skills are installed as local files with **no connection to the source repo** (`jvalin17/agent-toolkit`). There is no mechanism to:
- Check if newer versions exist
- Pull updates from the repo
- Sync the `shared/` directory (which was missing entirely from local install)

The `/updater` skill audits content freshness (links, versions, standards) but does NOT pull code updates.

**Impact:** Users run stale skills indefinitely. Bug fixes and improvements in the repo never reach installed copies. The `shared/` directory (guardrails, report format, project state template) was missing from local install — every skill silently failed to load its safety rules.

**Fix options:**
1. **Self-update command:** Add `/update-skills` that runs `git pull` from the source repo into `~/.claude/skills/`. Simple, explicit, user-controlled.
2. **Version check on startup:** Skills check a version file against the repo. If outdated, show "Skills update available — run `/update-skills`". No auto-update (respects G-UPD-1).
3. **Install script:** The initial installation should use `git clone` (not file copy) so the user can `cd ~/.claude/skills && git pull` manually.

**Root cause of the `shared/` directory missing:** Installation likely copied `skills/*` but not `shared/*` because `shared/` is at the repo root alongside `skills/`, not inside it.

---

## Previously Critical (now fixed): Missing Shared Files

**Status: FIXED** — The `shared/` directory was missing from local install but exists in the repo. Copied manually on 2026-05-07.

**Every single skill** was referencing files that didn't exist locally:

| Referenced File | Referenced By | Exists? |
|----------------|--------------|---------|
| `shared/guardrails-quick.md` | ALL skills (requirements, architecture, implementation, assess, reviewer, evaluate, precommit, setup, updater) | NO |
| `shared/guardrails.md` | ALL skills | NO |
| `shared/report-format.md` | requirements, architecture, implementation, reviewer, setup | NO |
| `project-state.md` | ALL skills (read at start, write at end) | NO — never gets created because no skill creates it first |

**Impact:** Every skill starts by silently failing to read guardrails and report format. The guardrail system (G-REQ-1, G-IMPL-1, G-ARCH-1, etc.) is referenced 50+ times but the actual rules are never loaded. Skills operate without the safety nets they're designed to have.

**Fix:** Either:
1. Create these files with the actual content (guardrails, report format template)
2. Or inline the critical guardrails directly into each SKILL.md (since the agent can't read files that don't exist)

**For `project-state.md`:** Every skill says "read at start, write at end" but none actually creates it on first run. The explore skill says "create if doesn't exist" but the others don't. First skill to run should create it.

---

## Skill-by-Skill Feedback

### `/requirements` — Grade: B

**What works well:**
- Draft-early principle is great — produces usable docs fast
- FEATURE mode (detecting existing app) correctly skips greenfield questions
- Q1-Q7 intake is well-structured

**Issues:**
- **Too many questions upfront.** The skill says "draft early" but the intake asks 7 questions before drafting. In practice I skipped Q2-Q3 and went straight to drafting. The skill should draft after Q1+Q4 (what + one thing it must do), then deepen on demand.
- **"Read `references/template.md`"** — this file exists but the skill never explicitly reads it. It just writes a freeform doc. The template should be enforced or removed.
- **Mode detection is manual.** Skill says "FEATURE if Q1 = existing app" but the agent already knows it's an existing app from context. Should auto-detect from CLAUDE.md / git history.

### `/architecture` — Grade: B+

**What works well:**
- Feature add-on mode (Step 1b) correctly avoids redesigning the whole system
- Decision table format is excellent for tracking choices
- Risk register catches real issues

**Issues:**
- **Explore menu is never used.** Every time I wrote the architecture doc directly without navigating the sub-skill menu (frontend.md, backend-data.md, etc.). The menu adds ceremony without value — the agent already knows what to design.
- **"Read Codebase Index"** — this doesn't exist. The skill should build it by running explore, not expect it to already exist.
- **Concurrency check is mentioned but never enforced.** SQLite + FastAPI concurrency issues are real but the skill doesn't check for them unless I remember to.

### `/implementation` — Grade: A-

**What works well:**
- Slab-by-slab discipline is the BEST feature. Prevents feature coupling.
- "Stop between slabs" rule catches bugs early
- TDD enforcement produces real tests (not afterthoughts)

**Issues:**
- **"Read `project-state.md` at start"** — file never exists (see above), so this always silently fails.
- **Mode detection should be automatic.** I had to mentally determine "this is Feature mode" every time. The skill has enough context to auto-detect.
- **Sub-mode files (backend.md, frontend.md, etc.) are referenced but never read.** I never once needed to read `backend.md` to build backend code. Either the sub-modes need to contain actionable checklists (not just guidelines), or remove the indirection.
- **No codebase awareness.** The skill says "read Codebase Index" but doesn't build one. It should auto-discover: what tables exist, what services exist, what patterns are used. I had to manually read files every time.

### `/precommit` — Grade: A

**What works well:**
- Caught sloppy mock tests (testing mocks, not real behavior)
- Instruction compliance check found real gaps
- Naming/standards enforcement is thorough

**Issues:**
- **Step 3 says "invoke /evaluate"** — this creates circular dependency. Precommit should be self-contained; evaluate is a separate gate.
- **Step 5 says "run rules-indexer agent"** — this agent doesn't exist. Should just grep CLAUDE.md.
- **Too slow for minor changes.** 6 steps for a 2-line bugfix is overkill. Should have a "quick mode" for small changes.

### `/assess` — Grade: A

**What works well:**
- Found the frontend N+1 API call pattern (loadIntelIds)
- Found the IntelRepository-in-loop code smell in compare
- Scale thresholds are well-calibrated (don't suggest Redis for 100 rows)

**Issues:**
- **No issues.** Best-calibrated skill. Worked perfectly in parallel with reviewer + evaluate.

### `/reviewer` — Grade: A+

**What works well:**
- Found the 2 critical EventSource bugs (stale closure + unmount leak)
- Found the DRY violation in step-building (tripled logic)
- Found the duplicate page fetch (concessions + policies)
- Security checks are thorough (SSRF, SQL, XSS)

**Issues:**
- **None.** This is the best skill. The stale closure finding was genuinely hard to spot. Keep this exactly as-is.

### `/evaluate` — Grade: A

**What works well:**
- 7/7 scorecard with clear PASS/FAIL per feature
- Caught the missing `POST /intel/{id}/floor-plan` endpoint
- Caught the missing `intel_gathered` column (correctly noted the query-based approach is better)

**Issues:**
- **Doesn't check test counts against architecture targets.** Architecture said "10-12 tests" for slab 1, evaluate didn't verify we hit that number.
- **Doesn't run tests.** Should actually execute the test suite and report pass/fail, not just read test files.

---

## Cross-Cutting Issues

### 1. Skills Don't Talk to Each Other
Requirements writes a doc → Architecture reads it → Implementation reads both. But:
- Requirements doesn't know what architecture decided
- Implementation doesn't know what evaluate found
- Precommit doesn't know what reviewer flagged

**Fix:** `project-state.md` was supposed to solve this, but it's never created. Either enforce its creation in the FIRST skill that runs, or use a different persistence mechanism.

### 2. No Codebase Discovery
Every skill says "understand the codebase" but none actually build an index. I spent significant time manually reading files before each skill could do its job.

**Fix:** Add a `codebase-index` step that all skills can call: scan for tables, services, repos, routes, and cache the result. The `/explore` skill is closest to this but it's a separate invocation, not integrated.

### 3. Reuse Detection is Missing
The Smart Ranking case exposed this badly. I was about to build 5 new files when 95% of the code already existed (`scorer.py`, `skill_matcher.py`, `entity_extractor.py`, `local_matcher.py`). No skill prompted me to check what's reusable before designing new components.

**Fix:** Add a reuse check step to `/architecture`:
> "Before designing new components, search for existing code that does similar things. List what can be reused, what needs adaptation, and what's genuinely new."

This single step would have saved hours on the Smart Ranking feature.

### 4. Report Files Are Never Created
Every skill says "write report to `reports/<skill>/report_<slug>_<uuid>.md`" but:
- The `reports/` directory doesn't exist
- Reports are never actually written (the skill outputs findings inline, which is fine)
- The report format file doesn't exist

**Fix:** Either create the reporting infrastructure, or remove the reporting instructions and accept that inline output IS the report.

### 5. Guardrails Are Theoretical
50+ references to G-REQ-1, G-IMPL-1, G-ARCH-1, etc. but the guardrail definitions don't exist in any file. The agent can't enforce rules it can't read.

**Fix:** Inline the top 5 most important guardrails directly into each SKILL.md. Don't rely on external files for critical safety rules.

---

## Suggested Priority Fixes

| # | Fix | Impact | Effort |
|---|-----|--------|--------|
| 0 | **Add auto-update mechanism** — `/update-skills` command or version check | CRITICAL — users run stale skills forever | 2 hrs |
| 0b | **Fix installer** — ensure `shared/` directory is included in installation | CRITICAL — guardrails never loaded without it | 30 min |
| 1 | ~~Create `shared/guardrails-quick.md`~~ EXISTS in repo, was missing locally — fixed | ~~HIGH~~ DONE | — |
| 2 | Add reuse-check step to `/architecture` — "what existing code does this already?" | HIGH — prevents rebuilding | 10 min |
| 3 | Create `project-state.md` in first skill that runs | MEDIUM — cross-skill communication | 10 min |
| 4 | Auto-detect mode in `/implementation` (Feature vs Build vs Fix) | MEDIUM — less ceremony | 15 min |
| 5 | Add "quick mode" to `/precommit` for small changes | MEDIUM — speed | 15 min |
| 6 | Remove report-format references OR create the file — EXISTS in repo, was missing locally | ~~LOW~~ DONE | — |
| 7 | Inline top guardrails into each SKILL.md as fallback | LOW — redundancy but reliable if shared/ missing | 20 min |

---

## What's Working Great — Don't Change

1. **Slab-by-slab discipline** in `/implementation` — best feature across all skills
2. **Parallel execution** of `/assess` + `/reviewer` + `/evaluate` — catches different issues
3. **TDD enforcement** — every slab has real tests with specific assertions
4. **Decision tables** in `/architecture` — easy to track and reference
5. **The reviewer skill** — genuinely finds bugs that would ship to production
