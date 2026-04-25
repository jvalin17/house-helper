# Evaluation: Job Agent Requirements

| Field | Value |
|-------|-------|
| **Evaluated** | `requirements/job-agent.md` + `reports/requirements/req_job-agent_ff666395.md` |
| **Against** | /requirements skill specification (standard mode) + user's questionnaire answers |
| **Date** | 2026-04-25 |
| **Overall Grade** | 18 / 20 claims passed (90%) |

## Scorecard

| # | Claim | Status | Evidence |
|---|-------|--------|----------|
| 1 | Header metadata present (date, mode, scope, user level, project state) | :white_check_mark: PASS | `job-agent.md:3-7` — all 5 metadata fields present |
| 2 | Problem Statement captures user's intent | :white_check_mark: PASS | `job-agent.md:11` — covers full pipeline + knowledge bank + local desktop |
| 3 | Core Requirement reflects knowledge-bank-first approach | :white_check_mark: PASS | `job-agent.md:15` — explicitly states "resumes are not static files" and knowledge bank differentiator |
| 4 | Boundaries include all user-stated exclusions | :white_check_mark: PASS | `job-agent.md:19-26` — no payments, no auto-submit, no cloud, quality over speed |
| 5 | User Stories section exists with relevant stories | :white_check_mark: PASS | `job-agent.md:30-34` — 5 user stories covering knowledge bank, resume gen, control, cover letter, learning |
| 6 | Functional requirements grouped by feature area with capability tables | :white_check_mark: PASS | `job-agent.md:38-113` — 6 feature groups, each with structured tables |
| 7 | Knowledge bank matches user description (free-text → AI extraction → structured review → grows) | :white_check_mark: PASS | `job-agent.md:44-50` — free-text dump, structured review/edit, incremental enrichment, skills extraction all present as `must` |
| 8 | Resume generation captures full user control (length, sections, tone, emphasis, layout, highlight/omit) | :white_check_mark: PASS | `job-agent.md:58-66` — all 6 control dimensions present. Length, section, tone, emphasis as `must`; layout, highlight/omit as `should` |
| 9 | Cover letter has generate + edit workflow | :white_check_mark: PASS | `job-agent.md:74-75` — auto-generate + in-UI editing, both `must` |
| 10 | Job input is manual paste-in for MVP, APIs deferred | :white_check_mark: PASS | `job-agent.md:86,91` — paste as `must`, explicit note deferring APIs |
| 11 | Application tracking is basic status tracking | :white_check_mark: PASS | `job-agent.md:99-102` — status tracking + list view as `must`, timeline as `should` |
| 12 | Learning loop captures feedback + outcome tracking | :white_check_mark: PASS | `job-agent.md:110-112` — user feedback `should`, outcome correlation `should`, style refinement `could` |
| 13 | Multiple export formats (PDF, DOCX, text, Markdown) | :white_check_mark: PASS | `job-agent.md:65,77` — both resume and cover letter have multi-format export as `must` |
| 14 | Local-only storage, no encryption | :white_check_mark: PASS | `job-agent.md:123-124` — SQLite + filesystem, OS-level security sufficient |
| 15 | Non-Functional Requirements table present | :white_check_mark: PASS | `job-agent.md:118-129` — 10 NFR entries covering latency, storage, security, privacy, integrity, portability |
| 16 | Data Requirements table present | :white_check_mark: PASS | `job-agent.md:133-142` — 8 data entities with source, storage, sensitivity |
| 17 | Assumptions, Dependencies, Parking Lot sections present | :white_check_mark: PASS | `job-agent.md:146-176` — all three sections populated |
| 18 | Completeness table present | :white_check_mark: PASS | `job-agent.md:180-188` — all sections graded, N/A for scale/infra/cost (correct for standard mode) |
| 19 | Report file created with key decisions and parked items | :white_check_mark: PASS | `req_job-agent_ff666395.md` — 13 key decisions recorded, 6 parked items, key insight documented |
| 20 | Capability tables follow skill template format | :yellow_circle: PARTIAL | Template specifies `Capability | Input | Output | Source | Priority` but output uses `Capability | Input | Output | Priority` — **Source column is missing** from all 6 capability tables |

## Detailed Findings

### :white_check_mark: Passed (18/20)

All core content requirements are met. The document is well-structured, captures the user's knowledge-bank-first vision accurately, and correctly scopes MVP vs post-MVP. Priorities (must/should/could) are well-assigned. The report file documents all decisions with zero assumptions needed — every answer came directly from the user.

Notable strengths:
- The knowledge bank section (`job-agent.md:38-50`) faithfully captures the user's reframing from "parse existing resume" to "build knowledge bank, generate on demand"
- Boundaries (`job-agent.md:19-26`) correctly include auto-submit as excluded even though the user didn't select "No auto-applying" — it was inferred from "prepare materials only" context
- NFRs (`job-agent.md:118-129`) are appropriately light for a local personal app but still cover data integrity and portability

### :yellow_circle: Partial (1/20)

**Claim 20 — Capability table format:** The /requirements skill template specifies tables with a `Source` column (`| Capability | Input | Output | Source | Priority |`). All 6 capability tables in the output omit the `Source` column. This column would indicate where each requirement came from (e.g., "user Q8", "inferred", "from memory"). Minor formatting gap — does not affect content quality.

### :red_circle: Failed (0/20)

None.

### :white_circle: Unable to Verify (1 note)

- **Question count guardrail (G-REQ-1: 15 max):** 14 questions were asked across 4 batches. Within limit. However, the questionnaire skipped the standard Batch 1 Q2 ("Who is this for?") and Q3 ("How technical are you?") — these were correctly inferred from memory (personal use, developer). This is a reasonable optimization, not a violation.

## Recommendations

1. **Add Source column to capability tables** — minor formatting fix to match the skill template. Each row should indicate where the requirement originated (e.g., "user", "inferred", "memory").
2. **No other gaps** — the document is ready to feed into `/architecture job-agent`.
