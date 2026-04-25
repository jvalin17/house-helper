# Architecture Report: Job Application Agent

> **Skill:** /architecture
> **Topic:** job-agent
> **Status:** completed
> **Started:** 2026-04-25
> **Completed:** 2026-04-25
> **Based on:** requirements/job-agent.md

## Progress

- [x] Context gathering — read requirements doc
- [x] Quick architecture — modular monolith, component diagram, tech stack, data flow
- [x] Deep dive — Data Architecture (3 decisions)
- [x] Deep dive — Code Structure (3 decisions)
- [x] Deep dive — API Design (4 decisions)
- [x] Engineering principles check — all green
- [x] Generate architecture document

## Skill-Specific Details

### Mode
Standard (quick + deep dives on data, code structure, API design)

### Decisions Made

| # | Decision | Choice | Depends On | Rationale |
|---|----------|--------|-----------|-----------|
| 1 | Knowledge bank schema | Hybrid (typed tables + JSON metadata) | — | Queryable core entities + flexible metadata |
| 2 | Generated docs storage | Content in DB, exports on filesystem | #1 | Markdown queryable, binaries stay as files |
| 3 | Schema migrations | App-level auto-migrate (PRAGMA user_version) | #1, #2 | Desktop app — silent, no CLI, hassle-free |
| 4 | Module organization | By Agent + Shared | — | Matches coordinator pattern, extensible |
| 5 | Design patterns | Strategy + Repository + Coordinator | #4 | Each solves a real problem |
| 6 | Prompt management | Python prompt modules | #4, #5 | Testable, type-safe, clean separation |
| 7 | API style | REST | — | One client, clean resources, FastAPI native |
| 8 | Endpoint design | Resource-based REST (6 groups) | #7 | Maps to feature groups from requirements |
| 9 | Error handling | Structured error responses | #7 | Frontend can differentiate error types |
| 10 | Streaming | No streaming (return complete) | #7 | Simpler, quality over speed |
| 11 | Job matching | Dedicated JobMatcher service (separate from JobParser) | #4, #1 | SRP: parsing ≠ matching. Uses existing repos (knowledge_repo + job_repo), no new repo. Supports future proactive job search. |
| 12 | LLM strategy | Multi-provider with graceful degradation | #4, #5 | LLM abstraction (Strategy pattern) supports Claude, OpenAI, Ollama, HuggingFace, or none. Every AI feature has an algorithmic fallback. |
| 13 | Job matching tech | Hybrid: Sentence Transformers + TF-IDF + RapidFuzz always, LLM on top | #11, #12 | Strong semantic matching offline. LLM adds deep analysis for top matches. |
| 14 | Offline mode | Opt-in with system requirements warning + automated setup | #12, #13 | User warned about ~500MB disk, ~2GB RAM. Models downloaded automatically. |
| 15 | Match calibration | Judgement system: users rate matches to tune scoring weights | #11, #13 | Anonymized calibration data stored locally. Exportable without PII. |

### Decisions Pending
None — all planned decisions made.

### Trade-offs Accepted
- No streaming: user waits 10-30s with loading spinner (acceptable per requirements: quality > speed)
- No encryption at rest: OS-level security sufficient for personal desktop app
- App-level migrations: less powerful than Alembic but hassle-free for end users
- Repository pattern: slight over-abstraction for a single-DB app, but keeps services testable
- Multi-provider LLM: adds abstraction layer complexity but enables free/local LLMs and no-LLM fallback
- Algorithmic fallbacks: template-based resumes won't match AI quality, but app remains functional without any LLM
- Offline models ~500MB disk: acceptable trade-off for full offline capability
- Sentence Transformers for semantic similarity: 80MB model but handles phrase-level meaning that word vectors (spaCy) cannot

### Principles Check

| Principle | Status |
|-----------|--------|
| SOLID | :white_check_mark: |
| DRY | :white_check_mark: |
| KISS | :white_check_mark: |
| YAGNI | :white_check_mark: |

### Output
- Architecture doc: `architecture/job-agent.md`
