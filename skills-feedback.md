# Skills Feedback — Lessons from panini

> Maintained based on real experience building the job-agent.
> These are generalized improvements for agent-toolkit skills.

## /requirements

1. **File operations must specify UX pattern.** When a capability says "import file" or "upload," require: drag-and-drop, file picker, paste, or clipboard. Default to drag-and-drop + file picker. We shipped a text input for file paths — unusable.

2. **Trace the core flow for priority validation.** "Resume import" was marked "should" but the app was broken without it (can't generate resume from empty knowledge bank). Any capability on the critical user path must be "must."

3. **Multi-input features need explicit modes.** "Add a job" actually means: paste URL, paste text, drag-and-drop file, or type. Each mode needs its own spec line. Don't collapse them into one row.

4. **Requirements drift tracking.** We added 5 major features during architecture (multi-LLM, offline, calibration, JSON-LD, Sentence Transformers) that were never formally in requirements. Skill should detect drift and prompt to formalize.

## /architecture

5. **Always include minimal frontend architecture when UI is in scope.** We designed 15 backend decisions but said "frontend: decide later." Result: no component hierarchy, no state management plan, inconsistent page structure.

6. **Threading/concurrency must be addressed for every DB + framework combo.** SQLite + FastAPI worker threads crashed the app. This is a known issue the architecture should flag automatically.

7. **Primary user flow diagram is mandatory.** Not just data flow — the actual user journey (open app → import resume → paste job → match → generate → preview → apply). This catches gaps like "what happens if knowledge bank is empty?"

## /implementation

8. **File uploads must use multipart + drag-and-drop, never file paths.** File paths are a dev shortcut. First implementation used `{"file_path": "/Users/..."}` — only works locally, terrible UX. Enforce: user-facing file input = multipart upload + drag-and-drop UI.

9. **At least one end-to-end integration test with real data.** We had 190+ unit tests but the first real URL crashed the app (parser didn't fetch URLs). Require one test that simulates the actual user journey.

10. **Check runtime version compatibility early.** Python 3.14 was too new for sentence-transformers and spaCy (15 tests skipped). Skill should check version against dependency requirements before writing code.

11. **Port management.** Default to non-standard port (8040 not 8000), make it configurable via env var. Two projects fighting for port 8000 blocked the user.

12. **Feature completeness on the page it belongs to.** Resume import UI was initially on the Knowledge Bank tab only, but users expect it on the main page too. The extracted data should flow to the right place (knowledge bank) while the action (upload) lives where users first land.

## /evaluate

13. **Add a smoke test step.** Evaluate checked files and structure but couldn't catch that the app crashes when you paste a URL, or that resume generation produces empty output. Starting the app and trying the primary action would catch these.

## General

14. **"Import" is always multi-modal.** Any import feature should support at minimum: drag-and-drop, file picker (browse button), and paste text. These are not three features — they're one feature with three entry points.

15. **Empty state handling.** Every "generate from data" feature needs an empty state check with a helpful message and action link. "Knowledge bank is empty → go import your resume" was missing until the user hit a blank preview.

16. **Resume/document parsing is a standalone, reusable module.** Don't couple it to any specific service. We built it in `shared/scraping/resume_parser.py` — it's used by the knowledge service, the import endpoint, and could be used by future agents.

## Critical Gaps Found (Session 2)

17. **"Auto" features get lost in requirements.** User said "auto apply" early on, it was parked as "excluded" in requirements, then the entire app was built as a manual tool. The /requirements skill should flag when a user's core intent is parked. If the user says "I want X" and X ends up in the parking lot, that's a red flag.

18. **Token budget management should be a shared concern.** Any agent using an LLM needs: max tokens per session, priority queue for what gets LLM vs algorithmic processing, never exceed budget without permission. This is not agent-specific — it's a panini-wide pattern. /architecture should detect this when multiple LLM-consuming features exist.

19. **Three LLM modes must be first-class in /requirements.** Not "works without LLM" as a fallback — but explicitly: "What does each feature do in no-LLM, offline-LLM, and online-LLM mode?" Every capability table should have three columns. We discovered this too late.

20. **Auto-apply changes the entire architecture.** A manual "paste and click" app is CRUD + generation. An auto-apply agent needs: job board API integration, search scheduling, application queue, confirmation workflow, audit trail. /architecture should detect this scope difference from the requirements and flag it: "Your requirements describe an autonomous agent, not a manual tool. This needs: [queue, scheduler, API integrations, confirmation flow]."

21. **Resume builder guardrails need a dedicated skill.** "Never fabricate, evidence-based, log user additions separately, research seniority-specific formats." This is domain knowledge that should be a reusable reference, not inline in one prompt template.

22. **Frontend was built before the core flow was clear.** We built UI for a manual tool, now it needs to be an autonomous agent dashboard. /implementation should not build frontend until the core automation flow is validated end-to-end in the backend.

## Session 2 — Full Cycle Assessment

### What worked well

- **TDD caught real bugs.** SQLite threading crash, URL not being fetched, empty knowledge bank — all caught by tests before or shortly after user hit them. The 255-test suite gives real confidence.
- **Backend architecture held up perfectly.** All v1 code was 100% reusable for v2. Modular monolith + repos + services pattern meant adding auto-search, auto-apply, and token budget was additive — zero rewrites.
- **Plugin architecture for job boards was the right call.** JSearch API + LinkedIn/Indeed scrapers all behind one protocol. Easy to add more.
- **Evaluate skill caught real gaps.** Source column missing, Local/Cheap section missing — caught before implementation.
- **v2 requirements fixed v1's core mistake** (auto-apply was the goal, not manual paste-and-click).

### What did NOT work — new feedback

23. **/requirements doesn't ask "what does your day look like?"** We never asked the user how they currently apply to jobs. If we had, "auto-apply" would have been requirement #1, not a parking lot item. Add to intake: "Walk me through how you do this today. What's painful?"

24. **Frontend redesign happened 3 times.** First: 4 tabs (Jobs/Tracker/Knowledge/Settings). Second: added 22 missing UI pieces. Third: complete restructure to 4 new tabs (Search/Superpower Lab/Dashboard/Settings). Each time the user said "I don't see X" or "where is Y?" The skill should produce a mockup/wireframe BEFORE coding and get explicit approval.

25. **/implementation should never say "implementation complete" for a feature the user hasn't tried.** We declared resume import "done" but the user couldn't use it (file path input, not drag-and-drop). We declared cover letter service "done" but it was buried in a modal nobody found. Rule: feature isn't done until user has tried it.

26. **Naming matters more than expected.** "Knowledge Bank" → "My Superpowers" → "Superpower Lab" — the user cared about naming and it changed the feel of the app. Skills should ask about naming/branding for user-facing features, not just technical capabilities.

27. **Tab ordering reveals priority.** The user's tab order (Job Search → Superpower Lab → Dashboard → Settings) is the actual user journey. /architecture should derive frontend navigation from the user flow diagram, not from feature grouping.

28. **"I don't see any changes" is a dev workflow problem.** User couldn't see frontend updates because they didn't restart the dev server or hard-refresh. /implementation should include a "how to see your changes" note when modifying frontend code. Trivial but blocked the user.

29. **Apply pipeline was invisible.** The auto-apply queue was hidden at the bottom of the Job Search tab, only appearing after selecting jobs. The user asked "where is auto-apply?" — it should be always visible with empty state guidance. Core features must never be hidden behind conditional rendering.

30. **Skill didn't detect the scope change magnitude.** Going from "manual paste tool" to "autonomous agent with auto-search, auto-apply, and token budgets" is not a feature addition — it's a different product. /requirements should flag: "This changes the core interaction model from [manual] to [autonomous]. Recommend re-running /architecture."

31. **Sub-tabs within tabs work well for related features.** "Superpower Lab" with sub-tabs (My Superpowers | Resume Builder) keeps the top-level navigation clean while grouping related features. This pattern should be in the frontend architecture guide.

### Skill scorecard for this session

| Skill | Grade | Why |
|-------|-------|-----|
| /requirements v1 | C | Missed the core intent (auto-apply). Parked the main feature. |
| /requirements v2 | A | Fixed it. 3-mode tables, proper scoping, auto-apply front and center. |
| /architecture v1 | B+ | Solid backend. Missed frontend entirely. |
| /architecture v2 | A | Clean additions, plugin system, queue design, budget manager. |
| /implementation backend | A | 255 tests, everything works, clean TDD. |
| /implementation frontend | C+ | Built wrong UI twice, user couldn't see changes, features buried. |
| /evaluate | B | Caught doc gaps but couldn't catch runtime issues. |
| Overall toolkit | B | The skills work — but they let the wrong thing get built first. The feedback loop from user to requirements was too slow. |

### Top 3 improvements to prioritize

1. **/requirements must ask "how do you do this today?"** — prevents building the wrong product entirely.
2. **/implementation must get user approval on UI mockup before coding** — prevents 3x frontend rewrites.
3. **Core features must never be conditionally hidden** — always show with empty state guidance.

## Session 3 — Competitive Analysis & Honest Assessment

32. **Compare with existing tools early in /requirements.** We built for 2 sessions before asking "is this useful compared to what exists?" /requirements should include: "What existing tools do this? How is yours different?" This prevents building something the market already solved better.

33. **"Auto-apply" means different things.** We said "auto-apply" but built "open URL in browser." The market (Simplify, LazyApply) means "fill the form and click submit." /requirements should disambiguate: "When you say auto-apply, do you mean: (a) prepare everything and open the page, (b) fill the form but user clicks submit, (c) fully automated submission?"

34. **Domain knowledge should be a local updatable file, not hardcoded.** ATS rules change over time. We built ats_rules.json as a periodically updatable file — this pattern should be standard for any domain-specific knowledge. /architecture should recommend: "Is this domain knowledge static or evolving? If evolving, store as updatable config, not code."

35. **Browser automation ≠ Chrome extension.** The user explicitly said "I don't want to share data via Chrome extension." Playwright runs a real browser locally — data never leaves the machine. This distinction matters for privacy-conscious users. /architecture should present local automation vs extension as separate options with privacy tradeoffs.

36. **Legal compliance check for integrations.** We built LinkedIn and Indeed scrapers, then had to remove them (violates ToS). /architecture should flag: "Is scraping this site legal? Check ToS before building." We lost time building and then deleting illegal scrapers.

37. **Demo mode is valuable.** The horizontal pipeline animation ("Do the Magic") demos the vision even before real APIs are connected. /implementation should support "demo with simulated data" for features that need external APIs — lets the user validate the UX without waiting for API setup.

38. **"Thank you for applying" was a lie.** We showed a success message before the user actually applied. /implementation guardrail: never show success confirmation for an action that hasn't actually happened. Show "page opened, confirm when you've applied" instead.

### Updated scorecard (end of session 3)

| Skill | Grade | Change | Why |
|-------|-------|--------|-----|
| /requirements v2 | A | — | Properly scoped auto-apply, 3-mode tables |
| /architecture v2 | A- | — | Plugin system, queue design, token budget. Missed legal check on scrapers. |
| /implementation backend | A | — | 234 tests, clean architecture, everything works |
| /implementation frontend | B- | ↑ from C+ | Pipeline visual is good. Still too many iterations to get right. |
| /evaluate | B | — | Still can't verify runtime |
| skills-feedback | A | NEW | This file is the most valuable output of the project |

## Session 4 — Weight, Polish, Missing Skills

### New feedback

39. **Dependency weight auditing should be automatic.** scipy (101MB) + sklearn (45MB) + numpy (36MB) = 182MB just for TF-IDF — which we replaced with 100 lines of pure Python. /implementation should audit: "Package X adds Y MB. Is there a lighter alternative?" before adding any dependency.

40. **HTML entities don't work in JSX.** We used `&#9989;` for emojis — rendered as literal text. JSX needs `{"\u2705"}` or actual Unicode characters. This is a basic React gotcha that /implementation should catch when writing frontend code.

41. **Accessibility is not an afterthought.** User flagged weak eyesight — we had to increase all pipeline fonts from 10px to 14px and add blue/green color coding for loading/done states. /implementation should check: "Can someone with reduced vision use this?" before declaring UI complete.

42. **Naming shapes user perception more than features.** "Apply Pipeline" → "Apply Superpowers" → "The Launchpad." "Search Only" → "Scout Jobs." "Forging Resume" → "Prepping Power Resume." The user cared deeply about naming — it changes how the product feels. Add to /requirements: "What should this feature be called? Name it before building it."

43. **Honest status for every button.** User asked "is every button working?" — many were placeholders. /implementation should maintain a live status table: button → works/placeholder/broken. Never ship a button without documenting whether it actually does something.

44. **"Do the Magic" as a pattern.** One-click orchestration that runs multiple stages visually is a powerful UX pattern. The user loved it. This should be a reusable component pattern in /implementation frontend guide: "For multi-step automation, build a visual pipeline with stage indicators."

45. **Blue for loading, green for done — universal.** The color language (blue=active, green=complete, gray=waiting) worked immediately for everyone. This should be a standard in the frontend guide — not ad-hoc color choices per component.

46. **Show results inline, don't redirect.** Initially "Do the Magic" redirected to Dashboard tab. User said "don't open dashboard, show summary here." /implementation rule: automation results should appear where the action was triggered, not on a different page.

### Proposed new skills

47. **/design** — UI wireframes before code. Show mockups, get approval. Would have prevented 3 frontend rewrites. Generates ASCII or markdown wireframes, asks "does this look right?" before /implementation touches any component.

48. **/slim** — Dependency auditing. Scan pyproject.toml / package.json, flag packages over 10MB, suggest lighter alternatives or pure implementations. We saved 182MB with one replacement.

49. **/demo** — Generate demo mode with simulated data. When features need external APIs (job boards, LLM), create a demo path that shows the UX with fake data. Validates the user experience without waiting for API setup.

50. **/legal-check** — Verify ToS compliance before building integrations. "Is scraping LinkedIn legal?" → No, use their API or an aggregator. We wasted time building then deleting illegal scrapers.

51. **/accessibility** — Audit UI for minimum font sizes (14px body, 16px headers), color contrast ratios (WCAG AA), keyboard navigation, screen reader labels. Should run after any frontend implementation.

52. **/status** — Honest feature status report. For every user-facing button/action: works / placeholder / broken / needs-API-key. Show this to the user proactively, not when they ask "does this work?"

### Final scorecard (end of session 4)

| Skill | Grade | Trajectory | Notes |
|-------|-------|-----------|-------|
| /requirements v1 | C | — | Parked the main feature. Fatal for product direction. |
| /requirements v2 | A | — | Fixed everything. 3-mode tables, auto-apply as core. |
| /architecture v1 | B+ | — | Solid backend, missed frontend. |
| /architecture v2 | A- | — | Plugin system, queue, budget. Missed legal check. |
| /implementation backend | A+ | ↑ | 234 tests, pure Python TF-IDF, 182MB saved. Clean. |
| /implementation frontend | B | ↑ from B- | Pipeline visual is great. Emoji fix was embarrassing. Still iterative. |
| /evaluate | B | — | Catches doc gaps, misses runtime. Needs smoke test. |
| skills-feedback.md | A+ | — | 52 items. Most valuable artifact of the entire project. |
| **Overall toolkit** | **B+** | ↑ from B | Backend is excellent. Frontend workflow needs /design skill. Missing skills (/slim, /legal-check, /accessibility) would have saved hours. |

### What the toolkit got right (overall)

- **TDD saved us repeatedly** — threading bugs, URL fetching, empty states all caught by tests
- **Backend architecture was rock solid** — all v1 code reused for v2, zero rewrites across 4 sessions
- **Plugin patterns worked** — job boards, LLM providers, exporters all behind protocols
- **Modular monolith was the right call** — easy to add features, easy to test, easy to understand
- **The 3-mode requirement tables** (no LLM / offline / online) are genuinely novel and useful

### What the toolkit got wrong (overall)

- **Built the wrong product first** — manual tool instead of auto-apply agent (session 1-2)
- **Frontend rebuilt 3+ times** — no /design skill, no mockup approval step
- **Illegal scrapers built and deleted** — no /legal-check skill
- **Heavy dependencies not caught** — 182MB of sklearn for 100 lines of math
- **Emoji rendering broken** — basic React knowledge gap
- **Buttons shipped as placeholders** — no /status skill to track what actually works
- **Success messages lied** — "Thank you for applying" before user actually applied

### If I could restart this project with updated skills

1. Run `/requirements` with "how do you do this today?" question → auto-apply would be requirement #1
2. Run `/legal-check` before any API integration plan
3. Run `/architecture` with frontend tab structure included
4. Run `/design` with wireframes for each tab → get approval
5. Run `/implementation` backend first, validate with real data
6. Run `/slim` before adding any heavy dependency
7. Run `/implementation` frontend with approved wireframes
8. Run `/accessibility` after frontend is built
9. Run `/status` to publish what works vs doesn't
10. Run `/evaluate` with smoke test (actually start the app)

Total estimated time saved: **~40% of the frontend iterations** (sessions 3-4 were mostly frontend rework that /design would have prevented).

## Session 6 — Async Hell, Live Tests, API Keys

### New feedback

61. **Never use async HTTP in FastAPI sync endpoints.** We wasted 45+ minutes debugging why job search returned 0 results. The cause: `async with httpx.AsyncClient()` inside a sync FastAPI endpoint running in a thread pool creates event loop conflicts that fail SILENTLY. **Rule: if your FastAPI endpoint is sync (`def` not `async def`), use `httpx.get()` (sync), never `httpx.AsyncClient()`.** This should be a guardrail in /implementation.

62. **ThreadPoolExecutor + asyncio.run = silent failures.** The combination of `ThreadPoolExecutor` + `asyncio.new_event_loop()` + `run_until_complete()` appeared to work in unit tests but failed silently in FastAPI's request context. The solution was trivial: switch to sync HTTP calls. /implementation should flag any pattern that combines thread pools with async event loops.

63. **API keys need `.env` file, not just env vars.** We restarted the server 5+ times and the API key was lost each time because it was set in the shell, not persisted. `.env` file loaded by `python-dotenv` on startup is the correct pattern. /implementation should auto-create `.env.example` when any `os.environ.get("KEY")` is detected.

64. **Live API tests must exist but not in regression.** Created `@pytest.mark.live` tests that hit real JSearch API — 2 tests that verify search works end-to-end. These catch the exact bug we just fixed (silent failures) but don't run in `pytest` default (only with `-m live`). **Rule: every external integration needs at least 1 live test with its own marker.** Don't mix with unit tests.

65. **Quality over quantity in search results.** RemoteOK returned 30 generic results that diluted 10 relevant JSearch results. We added logic: if a premium source (JSearch) is available, skip free generic sources. **Rule: when multiple data sources exist, prioritize quality. Don't merge noisy results with precise ones.**

66. **"Available" doesn't mean "working".** JSearch showed `is_available: true` (API key present) but returned 0 results due to async bug. Availability check should include a health check / test query, not just "key exists."

67. **Pin dependency versions BEFORE starting.** PyTorch 2.2 needs numpy <2 and transformers <5. We discovered this after installing, with cryptic errors like "\_ARRAY\_API not found" and "name 'nn' not defined." /implementation should check known version constraints before pip install.

68. **Document dependency constraints in a local file.** We created DECISIONS.md with every package, version, size, and why it's there. This is invaluable when debugging "why did X break?" — should be standard practice for any project with 10+ dependencies.

69. **Clarify pricing notation in UI.** "$3/M" means "$3 per million tokens" but users don't know that. Always write it out: "$3 per 1M input tokens." Show estimated cost per action ("~$0.006 per resume") not just per-token pricing.

70. **Set a sensible default budget.** We defaulted to no limit — users could accidentally spend $20 in one session. Default to $0.50/day (enough for ~30 resumes). User can always increase.

71. **Provider change should not require restart.** We load the LLM provider once at startup and inject it into services. Changing in Settings saves to DB but services keep the old provider. Fix: lazy-load from DB per request, or reload services on save. This is a known anti-pattern in dependency injection.

72. **Pre-load APIs for the developer.** If the developer's .env has API keys, they should work immediately without manual configuration in Settings. We do this with `_seed_api_keys_from_env()` — good pattern for any app where the developer IS the first user.

73. **Promise.all is a single point of failure for UI loading.** Settings page loaded 7 API endpoints in Promise.all — one failure killed ALL of them. Provider badges, job sources, models all disappeared silently. **Rule: load independent data sources independently.** Never use Promise.all for display data from multiple endpoints.

74. **Need a /ui-check skill or agent.** After every frontend change: (1) verify all API endpoints return data, (2) verify all components render, (3) check that buttons/badges/cards are populated. We shipped a blank Settings page 3 times because of silent loading failures.

75. **Frontend coding standards checklist for /implementation.** After any frontend change, verify: (1) no component over 200 lines — split it, (2) no `as unknown as` casts — use runtime type guards, (3) state variables have clear descriptive names, (4) every API call has error handling with user-visible message, (5) no Promise.all for independent data, (6) loading/error/empty states for every data-dependent view. We had 22 unsafe casts and 6 oversized components.

76. **Clean up AFTER features stabilize, not during.** We kept patching the frontend mid-feature (add button, remove button, rename state, add another button). Each patch made the code messier. Better: finish the feature, test it, THEN run /simplify to clean up.

## Session 5 — Tone, Interlinking, Lightweight UI

### New feedback

53. **Tone matters as much as functionality.** The user said "applying for jobs isn't exciting, it should be comforting." We had rocket emojis, party emojis, "Do the Magic ✨" — all too hyped. Changed to "One step at a time," removed tab emojis, softened colors. /design skill should ask: "What emotional tone should this app have? Exciting / professional / calming / playful?"

54. **Emojis are risky in professional tools.** We added emojis to tabs, pipeline stages, buttons — user flagged them as "not great" and "school project-ish." Rule: use emojis sparingly, only where they add genuine clarity (🚀 for auto-launched apps on tracker is fine — it's informational, not decorative). Never on navigation or headers.

55. **Green = school project, blue/white = professional.** User explicitly said green makes it look unprofessional. Blue shades with white convey competence and calm. This is a subjective but strong signal — default to blue/white palette for any productivity tool.

56. **Overflow breaks layouts.** "Prepping Resume_Backend_Engineer_Senior_Level_04-26.pdf" overflowed the pipeline box. Always use `truncate` + `overflow-hidden` + `max-w` on any text that comes from dynamic data. /implementation should audit all dynamic text for overflow.

### Should skills be interlinked?

57. **Yes — skills need a shared state file.** Right now skills are completely isolated. Each reads from filesystem but doesn't know what other skills decided. This caused cascading failures:

**Problem chain we experienced:**
```
/requirements parked "auto-apply"
  → /architecture didn't question it (didn't know it was parked)
    → /implementation built a manual tool (followed architecture)
      → User said "where is auto-apply?" (3 sessions wasted)
```

**What a shared state would have caught:**
```
/requirements writes: PARKED: auto-apply (user's stated core intent)
  → /architecture reads parking lot, flags: "WARNING: 'auto-apply'
     was the user's core intent but it's parked. Confirm before proceeding."
  → Problem caught in session 1, not session 3
```

**Proposed: `project-state.md` — a shared file all skills read/write:**

```markdown
# Project State (auto-maintained by skills)

## Last Skill Run
- Skill: /implementation
- Date: 2026-04-25
- Status: 234 tests passing

## Key Decisions
- Core intent: auto-apply pipeline (from /requirements v2)
- Architecture: modular monolith, plugin pattern (from /architecture v2)
- Frontend: 4 tabs, blue/white palette (from /implementation)

## Parking Lot (cross-skill)
| Item | Parked By | Is Core Intent? | Status |
|------|-----------|-----------------|--------|
| Auto-apply | /requirements v1 | YES — user's stated goal | RESOLVED in v2 |
| Browser form filling | /architecture v2 | No | Still parked |

## Active Warnings
- Frontend rebuilt 3x — run /design before next frontend change
- Emojis cause rendering issues in JSX — use Unicode escapes

## What Works / What Doesn't
| Feature | Status | Last Verified |
|---------|--------|--------------|
| Resume import (drag-drop) | works | 2026-04-25 |
| Auto-search (RemoteOK) | works | 2026-04-25 |
| Auto-search (JSearch) | needs API key | — |
| Pipeline animation | works (demo) | 2026-04-25 |
| Actual form filling | not built | — |
| Offline models | placeholder | — |
```

**How skills would use it:**

| Skill | Reads | Writes |
|-------|-------|--------|
| /requirements | Previous decisions, parking lot | New requirements, parked items, core intent |
| /architecture | Requirements, core intent, warnings | Decisions, new warnings |
| /implementation | Architecture decisions, warnings, what works | Feature status, new warnings |
| /evaluate | What should work | What actually works/fails |
| /design | Current tab structure, tone preference | Approved wireframes |
| /status | Everything | Generates summary |

58. **Skills should challenge the parking lot.** If a skill parks something that matches the user's stated core intent, it should flag: "You said you want X, but I'm parking it. Are you sure?" This single check would have saved 2 entire sessions.

59. **Each skill should read the previous skill's output before starting.** /architecture should refuse to run without requirements. /implementation should refuse without architecture. This is loosely enforced now (skills check for files) but should be stricter — and should READ the content, not just check existence.

60. **Skill handoff summaries.** When /requirements finishes, it should write a 3-line summary for /architecture: "Core: X. Must-haves: Y. Watch out for: Z." Same from /architecture to /implementation. Currently each skill generates a full report but the next skill has to re-parse everything.

### Final final scorecard (end of session 5)

| Skill | Grade | Trajectory | Notes |
|-------|-------|-----------|-------|
| /requirements v1 | C | — | Parked core intent |
| /requirements v2 | A | — | Fixed. 3-mode tables, auto-apply centered. |
| /architecture v1 | B+ | — | Solid backend, no frontend |
| /architecture v2 | A- | — | Plugin system, queue. Missed legal. |
| /implementation backend | A+ | — | 234 tests, pure Python TF-IDF, clean |
| /implementation frontend | B+ | ↑ from B | Tone right, layout right. Still too many iterations. |
| /evaluate | B | — | Needs smoke test + runtime check |
| skills-feedback.md | A+ | — | 60 items. The playbook for the next project. |
| **Overall toolkit** | **B+** | Stable | Backend excellent. Frontend needs /design. Skills need interlinking via shared state. |

### The single biggest improvement

If I could add ONE thing to the toolkit: **`project-state.md` that all skills read and write.** It would have prevented the auto-apply miss (session 1-3), caught the frontend tone mismatch earlier, and stopped placeholder buttons from shipping without disclosure. Every other improvement is incremental — this one is structural.

## Session 7 — Defensive Frontend Coding (25 bugs in one audit)

### New feedback — general patterns, not app-specific

77. **ErrorBoundary is day-1 infrastructure, not a polish step.** Without one, ANY unhandled throw in ANY component blanks the entire screen. /implementation should add an ErrorBoundary wrapping routes as the FIRST frontend task, before writing any component. It takes 50 lines and prevents every Tier-1 crash from being user-visible. This is as fundamental as adding a try/catch to `main()`.

78. **Never trust API response shape — always Array.isArray().** APIs return envelopes (`{jobs: [...]}`), error objects (`{detail: "..."}`), or change shape between versions. Casting `as SomeType[]` and calling `.map()` without `Array.isArray()` crashes on anything unexpected. **Rule: every `setStateVar(apiResponse)` that expects an array must guard with `Array.isArray()`.** This is the frontend equivalent of null-checking database results.

79. **JSON.parse on external data always needs try/catch.** `JSON.parse("")` throws. `JSON.parse("null")` returns null, then `.property` throws. Any JSON stored in a DB column or returned from an API can be malformed. **Rule: wrap every JSON.parse of external data in a helper that returns a safe fallback.** We wrote `safeJsonParse()` — should be a standard utility in every frontend project.

80. **`setLoading(true)` without `finally { setLoading(false) }` is a stuck-state bug.** If ANY await between set-true and set-false throws, the button stays disabled forever, the spinner spins forever, and the user has no way to recover without refreshing. **Rule: every loading flag must be wrapped in try/finally.** No exceptions. This was the #1 category of bugs (6 instances across 4 components).

81. **`fetch()` doesn't throw on 4xx/5xx — only on network errors.** `await fetch(url)` returns a Response with `ok: false` for server errors, but the code after it runs normally. The `api.request()` helper threw on non-ok, but every direct `fetch()` call silently succeeded. **Rule: never use raw `fetch()` without checking `response.ok`. Build a checked wrapper and use it everywhere.** We added `fetchChecked()` for export endpoints.

82. **Never show success before verifying the response.** Settings showed "Saved and active." and cleared the API key field regardless of whether the server returned 200 or 500. If the save failed, the user lost their typed key AND thought it was saved. **Rule: check `response.ok` BEFORE any success message, state clear, or UI update.** This is a "silent lie" — the most insidious bug category because users blame themselves, not the app.

83. **Shared state across list items causes flash/bleed bugs.** A single `history` state variable shared across all expandable application cards meant: expand card A → load history → expand card B → card B briefly shows card A's history until its own loads. **Rule: when multiple instances of a component each have async-loaded sub-data, use a map (`Record<id, data>`) not a single variable.** Same applies to: accordion panels, expandable rows, detail modals.

84. **N+1 fetches in frontend loops are as bad as N+1 SQL queries.** `for (const app of apps) { await api.getJob(app.job_id) }` runs sequentially — 10 apps = 10 round trips = 2-5 seconds of loading. **Rule: use `Promise.all()` for independent fetches in loops.** Or better, build a batch endpoint on the backend.

85. **Every file input needs TWO validations: click path AND drag-drop path.** The `<input accept=".docx,.pdf">` only filters the file picker dialog. Drag-and-drop bypasses it entirely — any file type goes through. **Rule: validate file extension/MIME in the drop handler too, not just the input element.** This is a security boundary, not just UX.

86. **User-provided URLs need scheme validation against XSS.** `<a href={userUrl}>` with no validation allows `javascript:alert(1)` — same-origin XSS from imported data (resume, job posting). **Rule: validate URL scheme (`/^https?:\/\//`) before rendering any user-provided URL as a clickable link.** This applies to: project URLs, company URLs, any URL from imported documents.

87. **Dead code from conditional short-circuits.** `const hasInput = true; if (!hasInput) return` — the branch is unreachable, the variable is pointless, but the disabled-condition on the button references it, making it look like there's validation when there isn't. **Rule: when simplifying conditional logic, trace all references.** Don't leave dead variables that give a false sense of safety.

88. **Content-Type header on GET/DELETE requests is technically wrong.** Setting `Content-Type: application/json` on requests with no body triggers unnecessary CORS preflights and is pedantically incorrect per HTTP spec. **Rule: only set Content-Type when the request has a body.** Small, but multiplied across every API call it adds latency.

89. **A single bug audit session is more valuable than incremental fixes.** We fixed 25 bugs in one systematic pass, organized by severity tier (crash → stuck → lies → hygiene). Doing this ONCE after features stabilize is far more effective than sprinkling defensive code throughout implementation. **/implementation should include a "hardening pass" as a formal step after features are complete** — not mixed into feature work.

### Updated /implementation frontend checklist

Based on session 7, add to the frontend post-implementation checklist:

```
## Frontend Hardening Checklist (run ONCE after features stabilize)

### Crash prevention
- [ ] ErrorBoundary wraps all routes
- [ ] Every JSON.parse has try/catch with safe fallback
- [ ] Every API response cast to array has Array.isArray() guard
- [ ] Every `.map()` / `for...of` on API data is guarded

### State stuck prevention
- [ ] Every setLoading(true) has a matching finally { setLoading(false) }
- [ ] Every async handler is wrapped in try/catch (or try/finally)
- [ ] No raw await without error handling in event handlers

### Silent lie prevention
- [ ] Every raw fetch() checks response.ok before success path
- [ ] No success message shown before verifying the response
- [ ] No state cleared (setApiKey("")) before confirming save succeeded
- [ ] parseFloat/parseInt results checked with isNaN() before display

### Security
- [ ] User-provided URLs validated for scheme (https?://)
- [ ] File drop handlers enforce same extensions as <input accept>
- [ ] No dangerouslySetInnerHTML on user data

### Hygiene
- [ ] No Content-Type on GET/DELETE requests
- [ ] Shared sub-data uses per-item map, not single state variable
- [ ] N+1 fetches in loops replaced with Promise.all or batch endpoint
- [ ] Dead code / unreachable branches removed
```

## Session 9 — Frontend Streamline (Prevention Rules)

### New feedback — rules to prevent future frontend refactoring

90. **Create types/index.ts on day 1 of any frontend project.** Every interface must live in a shared types file, never inline in components. We had 3 duplicate `Job` interfaces, 2 duplicate `Suggestion` interfaces, and 9 `Props` interfaces with `Record<string, unknown>` instead of proper types. This caused 18 `as unknown as` casts that were the #1 source of type-safety bugs. **Rule for /implementation: when creating a new component, import types from `types/index.ts`. If the type doesn't exist, add it there first.**

91. **Create a typed API client before the first component.** Every API call goes through one file with typed returns. We had 6 files using raw `fetch()` with different error handling patterns. Settings had 8 direct fetch calls. Home had 3. All inconsistent. **Rule: `api/client.ts` must exist before any component that calls an API. All returns must be typed. No raw `fetch()` in components.**

92. **Create `useAsync` hook before the first data-loading component.** The fetch+loading+error pattern was duplicated 6x identically. A 40-line hook replaces all of them. **Rule: if you see `const [loading, setLoading] = useState(false)` + `try { await ... } catch { } finally { setLoading(false) }`, use the hook instead.**

93. **Install toast notifications on day 1.** We had 24 `catch { /* silent */ }` blocks. Users got zero feedback when operations failed. Adding sonner (3KB) + replacing catches with `toast.error()` took 20 minutes but transformed the UX. **Rule: install `sonner` (or equivalent) in the first commit. Every user-facing catch must show a toast.**

94. **Component max size is 200 lines. Enforce before shipping.** KnowledgeBank grew to 489 lines because nobody checked. It should have been split when it crossed 200. **Rule for /implementation: after completing a component, run `wc -l`. If over 200 lines, split before committing.** The split pattern: orchestrator (state + handlers) → presentational sub-components (props + render).

95. **No `as unknown as` casts in production code.** Every cast is a bug waiting to happen. If you need a cast, the API client's return type is wrong — fix the client, not the component. The 7 debug `__dbg` casts are acceptable (dev tooling), but API response casts are never OK.

96. **Shared components must exist before the second copy-paste.** We had the modal overlay pattern pasted 4x, stats card pattern 5x, error display 6x. Creating `Modal.tsx` (24 lines) and `StatCard.tsx` (16 lines) after the fact took more effort than creating them on first use. **Rule: the second time you copy a pattern, extract it to `components/shared/`.**

97. **Direct fetch calls are a code smell.** If `api/client.ts` exists, every fetch should go through it. Direct `fetch()` in components means inconsistent error handling, no request logging, and duplicated URL construction. We found 6 files with direct fetches after the client was already built. **Rule: grep for `fetch(` in components during code review. If found, move to client.**

98. **Frontend tests should cover rendering, not just snapshots.** We started with 21 tests (all rendering tests). After the streamline we have 34. The new tests (useAsync hook, Modal dialog role, StatCard rendering) caught real issues. **Rule: every shared component and custom hook needs at least 2 tests: renders correctly + handles the primary interaction.**

### Frontend Architecture Checklist (run at project start)

Before writing the first component:
- [ ] `types/index.ts` exists with domain model interfaces
- [ ] `api/client.ts` exists with typed returns for all endpoints
- [ ] `hooks/useAsync.ts` exists for data loading
- [ ] Toast library installed and Toaster in App.tsx
- [ ] `components/shared/` directory exists for reusable components
- [ ] ErrorBoundary wraps all routes
- [ ] `.gitignore` includes `node_modules/`, `.env*`, `dist/`

Before merging any component:
- [ ] Under 200 lines (or justified reason for exception)
- [ ] No `as unknown as` casts (except dev tooling)
- [ ] No raw `fetch()` calls (use api client)
- [ ] No `catch { /* silent */ }` (use toast.error)
- [ ] Uses types from `types/index.ts` (not inline interfaces)
- [ ] Has at least 1 render test if shared/reusable

## Session 10 — Desktop App, CI/CD, Cross-Platform Builds

### New feedback

99. **A `/debug-desktop` skill would be valuable.** When the desktop app has issues (blank page, backend not starting, settings empty), there's no easy way to diagnose. A dedicated skill that checks backend health (port 8040 reachable?), reads sidecar logs, verifies DB state (`PRAGMA user_version`, table row counts), and tests API endpoints would save significant debugging time. **Not built yet — focus on core features first, then add this when desktop users report issues.** The skill should: (1) `curl localhost:8040/health`, (2) check `~/.panini/` for DB file, (3) verify schema version matches code, (4) list settings keys, (5) test one endpoint per category (KB, jobs, resumes, settings).

100. **Frontend must have built-in defaults for backend-provided data.** Settings page showed zero providers/models/sources when backend was unreachable — completely empty and unusable. Fix: hardcode known providers, models, and job sources as frontend fallback defaults. Backend values override when available. **Rule: any UI that depends on a config/discovery endpoint must have frontend-side defaults so it's never blank.**

101. **Cross-platform CI is a one-time pain.** First release took 4 tag attempts due to: `npm ci` vs `npm install` (Tauri optional deps), macOS Intel runners queued 30+ min, Linux Rust compilation took 45+ min on free runners. Once fixed, future releases are `git tag && git push` — fully automatic. **Rule: budget an entire session for CI setup. It's boring but it's infrastructure that pays for itself.**

102. **PyInstaller binary needs `sys.frozen` check.** `uvicorn.run(reload=True)` crashes in a PyInstaller frozen binary because the reloader tries to reimport from a temp directory. Always check `getattr(sys, "frozen", False)` and disable reload when frozen. **Rule for /implementation: any Python entry point that could be frozen by PyInstaller must handle the frozen case.**

103. **Tauri sidecar pattern is the right call for Python backends.** Pure Tauri IPC would require rewriting every `fetch("/api/...")` to `invoke("command")` + Rust wrappers for every Python function — months of work. HTTP on localhost:8040 means zero frontend code changes. Slack, VS Code, Notion all use this pattern. **Rule for /architecture: when wrapping an existing web app in a desktop shell, always evaluate sidecar (local HTTP server) vs IPC. Sidecar wins unless startup time is critical.**

104. **Desktop users need `~/.appname/.env` as a config location.** Frozen binaries can't find `.env` relative to `__file__` (points to temp extraction dir). Always add `Path.home() / ".appname" / ".env"` as a dotenv search path. **Rule: any app that supports both dev and desktop modes needs at least 3 dotenv paths: home dir, project root, cwd.**

## Session 11 — Desktop Release, Naming Audit, Budget Enforcement

### New feedback

105. **Variable naming must be enforced by /implementation, not caught in review.** We wrote 109 poorly-named variables across 37 files (single-letter `r`, `cl`, `s`, `p`, `m` and abbreviations `svc`, `repo`, `conn`, `prefs`, `buf`). A codebase-wide rename took an entire agent session. **Rule for /implementation: BEFORE writing any code, the skill must state: "All variables use full descriptive names. No single-letter variables except i/j/k in loops and e in exceptions. No abbreviations." And then ENFORCE it in every code block written.** This is the #1 readability issue across all sessions.

106. **DMG files from CI were corrupted due to double-compression.** `actions/upload-artifact@v4` compresses by default. DMG files are already compressed. Double-compression produces an unreadable file. **Rule: when uploading pre-compressed artifacts (DMG, ZIP, MSI), set `compression-level: 0` in the upload step.** We shipped 3 broken releases before discovering this.

107. **Tauri shell plugin config changed between versions.** We used `"scope"` in `plugins.shell` which was valid in Tauri 1 but causes a panic in Tauri 2 (`unknown field 'scope', expected 'open'`). The app launched but immediately crashed with no visible error. **Rule: when using Tauri plugins, always check the current version's config schema. Tauri 2 uses capabilities files for permissions, not plugin config scope.**

108. **macOS Gatekeeper blocks unsigned apps with "damaged" error.** Users cannot open the app without running `xattr -cr /Applications/AppName.app`. This MUST be documented in the README download section, not discovered by users. **Rule: if shipping unsigned macOS apps, add the xattr workaround prominently in install instructions.** Long-term fix: Apple Developer certificate ($99/year) for code signing.

109. **Budget enforcement belongs in the provider wrapper, not in individual services.** We initially considered adding budget checks to each service (resume, cover letter, analysis, matching — 6 places). Instead, we added `_check_budget()` to `LazyLLMProvider.complete()` — one place, catches ALL LLM calls. **Rule for /architecture: when a cross-cutting concern (budget, auth, logging) needs to intercept all calls of a type, put it in the wrapper/middleware, not in each caller.**

110. **`force_override` pattern for budget/limit dialogs.** When budget is exceeded, the backend returns 429 with details. Frontend shows a confirmation dialog. If user clicks "proceed", the same request is retried with `force_override: true` which bypasses the check. **Rule: any "soft limit" (budget, rate limit, warning threshold) should follow this pattern: check → reject with details → frontend confirms → retry with override flag.** Never silently block or silently allow.

111. **Naming conventions should be a shared reference file, not inline in each skill.** We have naming rules in /implementation's coding standards, in skills-feedback (items 90-98), and now 109 violations found in review. The rules exist but aren't enforced because they're scattered. **Proposed: `references/naming-conventions.md` that ALL skills read before writing code.** One source of truth, consistently enforced.

### Updated scorecard

| Metric | Before | After |
|--------|--------|-------|
| Largest component | 489 lines | 354 lines |
| `as unknown as` casts | 18 | 7 (debug only) |
| Silent catches | 24 | 0 |
| Duplicate patterns | 6x fetch, 4x modal, 5x stats | 0 (extracted to hooks/shared) |
| Direct fetch calls | 6 files | 0 (all through api client) |
| Shared types file | No | Yes (20 interfaces) |
| Custom hooks | 0 | 1 (useAsync) |
| Reusable components | 0 | 2 (Modal, StatCard) |
| Frontend tests | 21 | 34 |
