# Skills Feedback — Lessons from house-helper

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

18. **Token budget management should be a shared concern.** Any agent using an LLM needs: max tokens per session, priority queue for what gets LLM vs algorithmic processing, never exceed budget without permission. This is not agent-specific — it's a house-helper-wide pattern. /architecture should detect this when multiple LLM-consuming features exist.

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
