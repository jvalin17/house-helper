# Requirements Report: Job Application Agent

> **Skill:** /requirements
> **Topic:** job-agent
> **Status:** completed
> **Started:** 2026-04-24
> **Completed:** 2026-04-25

## Progress

- [x] Intake questionnaire (Batch 1: What & Who)
- [x] Intake questionnaire (Batch 2: Scope & Core)
- [x] Mode detection → Standard
- [x] Functional requirements — Knowledge Bank
- [x] Functional requirements — Resume Generation
- [x] Functional requirements — Cover Letter Generation
- [x] Functional requirements — Job Input
- [x] Functional requirements — Application Tracking
- [x] Functional requirements — Learning Loop
- [x] Non-functional requirements
- [x] Data requirements
- [x] Generate requirements document

## Skill-Specific Details

### Mode
**Standard** — detected because: building a feature/agent for personal use (developer, Level 3), but with 4+ capabilities (UI + internet + storage + file uploads) and a full end-to-end pipeline.

### User Level
**3 (developer)** — Python-primary, Java secondary, learning TypeScript for frontend.

### Key Decisions

| Question | User's Answer | Assumption? |
|----------|-------------|-------------|
| What are you building? | Feature/agent within house-helper app | No |
| Who is this for? | Personal use | No |
| Core value | End-to-end automation | No |
| Resume handling | Knowledge bank approach (free-text dump → AI extraction → structured review → on-demand tailored generation) | No |
| Resume preferences | Full control (length, sections, tone, emphasis, layout, ordering, highlight/omit) | No |
| Job source (MVP) | Manual paste only, APIs post-MVP | No |
| Cover letter | Generate + edit in UI | No |
| Application tracking | Basic status tracking | No |
| Learning loop | Feedback + outcome tracking (which resumes led to interviews) | No |
| Output formats | PDF, DOCX, plain text, Markdown | No |
| Data storage | Local SQLite, no encryption, local filesystem | No |
| Response style | Quality over speed, either streaming or wait is fine | No |
| Exclusions | No payment features | No |

### Key Insight: Knowledge Bank Architecture

The user reframed resume handling from "parse and tweak existing resume" to a **knowledge-bank-first model**:
1. Users dump all experience as free text
2. Claude extracts and structures it
3. User reviews/edits structured data
4. Resumes are generated fresh each time from the knowledge bank, tailored per job
5. Knowledge bank grows richer over time
6. Learning loop tracks which approaches led to interviews

This is the core differentiator and should drive the architecture.

### Items Parked

| Item | Category | Next Step |
|------|----------|-----------|
| Job board API integrations | feature | Future /requirements |
| Auto-apply to jobs | feature | Evaluate feasibility separately |
| ML-powered learning loop | feature | Post-MVP |
| Interview prep agent | feature | Separate agent |
| Architecture decisions | architecture | /architecture job-agent |
| UI/UX design | design | Design phase |

### Output
- Requirements doc: `requirements/job-agent.md`
