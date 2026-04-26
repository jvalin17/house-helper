# Requirements Report: Job Agent v2

> **Skill:** /requirements
> **Topic:** job-agent-v2
> **Status:** completed
> **Started:** 2026-04-25
> **Completed:** 2026-04-25
> **Previous:** reports/requirements/req_job-agent_ff666395.md (v1)

## Progress

- [x] Context from v1 + user's expanded vision notes
- [x] Clarifications: auto-apply method, job boards, token budget, search frequency, resume templates
- [x] Functional requirements — 8 feature groups with 3-mode specs
- [x] Non-functional requirements
- [x] Data requirements
- [x] Reusability assessment of existing codebase
- [x] Generate requirements document

## Skill-Specific Details

### Mode
Standard — expanding existing personal app with major new automation features.

### User Level
3 (developer) — Python-primary, building with existing codebase.

### Key Decisions

| Question | User's Answer | Assumption? |
|----------|-------------|-------------|
| Auto-apply method | Both email + browser, manual fallback | No |
| Job boards | LinkedIn + Indeed | No |
| Token budget | User-configured, adaptive over time, ask on first use | No |
| Search frequency | User sets schedule (every X hours/days) | No |
| Resume templates | User picks from 3-4 templates | No |
| Auto-apply was excluded in v1 | User corrected: auto-apply is the MAIN GOAL | This was a critical miss in v1 |

### What Changed from v1

| Area | v1 | v2 |
|------|----|----|
| Core purpose | Manual paste + generate | Autonomous auto-apply pipeline |
| Job input | Paste URLs only | Auto-search (LinkedIn, Indeed) + paste |
| Apply | Manual (track only) | Auto-apply with confirmation (email + browser) |
| LLM modes | Claude optional | Three first-class modes with per-feature specs |
| Token management | None | Budget system with priority queue |
| Resume builder | One template, basic | Multiple templates, seniority-aware, guardrailed |
| Tracking | Basic status | Full audit trail (method, features used, docs linked) |

### Items Parked

| Item | Category | Next Step |
|------|----------|-----------|
| Browser form-filling (Selenium) | feature | Post-MVP |
| Background search daemon | feature | Post-MVP |
| Resume A/B testing | feature | Post-MVP |

### Output
- Requirements doc: `requirements/job-agent-v2.md`
