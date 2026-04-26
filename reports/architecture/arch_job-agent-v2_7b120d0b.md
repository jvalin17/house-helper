# Architecture Report: Job Agent v2

> **Skill:** /architecture
> **Topic:** job-agent-v2
> **Status:** completed
> **Started:** 2026-04-25
> **Completed:** 2026-04-25
> **Based on:** requirements/job-agent-v2.md
> **Previous:** reports/architecture/arch_job-agent_3d74907d.md (v1)

## Progress

- [x] Context gathering — read v2 requirements + v1 architecture
- [x] Quick architecture — component diagram, new modules, data flow
- [x] Deep dive — Job board API strategy (Decision 1-2)
- [x] Deep dive — Auto-apply queue design (Decision 3-4)
- [x] Deep dive — Frontend page structure (Decision 6)
- [x] Token budget manager design (Decision 5)
- [x] Engineering principles check — all green
- [x] Generate architecture document

## Skill-Specific Details

### Mode
Standard — expanding existing architecture with automation pipeline.

### Decisions Made

| # | Decision | Choice | Depends On | Rationale |
|---|----------|--------|-----------|-----------|
| 1 | Job board access | APIs + scraping, both as plugins | — | User wants both. Plugin interface supports either. |
| 2 | Plugin architecture | JobBoardPlugin protocol | #1 | OCP — add boards without touching existing code |
| 3 | Auto-apply flow | Queue with state machine | — | pending → generating → ready → reviewing → confirmed → applied |
| 4 | Apply method | Email (mailto:) + browser + manual | #3 | No Selenium for MVP. User confirms each. |
| 5 | Token budget | BudgetManager wrapping LLMProvider | — | Per-feature tracking, priority queue, never exceed |
| 6 | Frontend tabs | 4 tabs: Search → Builder/Superpowers → Dashboard/Tracker → Settings | — | User's explicit ordering |
| 7 | Scheduler | APScheduler (in-process) | — | Lightweight, desktop-appropriate |
| 8 | Resume guardrails | Evidence validation layer | — | Never fabricate, log user additions |
| 9 | Evidence logging | evidence_log table | #8 | Source-track all knowledge bank entries |

### Trade-offs Accepted
- Email apply uses mailto: links (no SMTP) — user sends manually
- Browser apply opens URL only — no form-filling automation
- Scheduled search only runs while app is open
- Job board scrapers may break when site layouts change

### Principles Check

| Principle | Status |
|-----------|--------|
| SOLID | :white_check_mark: |
| DRY | :white_check_mark: |
| KISS | :white_check_mark: |
| YAGNI | :white_check_mark: |

### Output
- Architecture doc: `architecture/job-agent-v2.md`
