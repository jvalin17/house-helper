# Implementation Report: Feedback, Templates, Cost Tracking

| Field | Value |
|-------|-------|
| **Status** | in-progress |
| **Started** | 2026-04-28 |
| **Mode** | backend + frontend |
| **Test Approach** | TDD |
| **Tech Stack** | Python/FastAPI + React/TypeScript, pytest + vitest |

## Blocks

### Block 1: Suggestion Feedback System (#20)
- [ ] Backend: `suggestion_feedback` table + repo
- [ ] Backend: `/knowledge/feedback` endpoint (POST rejected suggestion)
- [ ] Backend: Feed rejected suggestions into analyze_fit prompt
- [ ] Frontend: thumbs-down button on each suggestion in ResumeAnalysis
- [ ] Test: Zillow email bullet flagged → doesn't appear in next analysis

### Block 2: PDF Header Alignment (#21)
- [ ] Fix CSS: name + contact on fewer lines, tighter spacing
- [ ] Test: generated PDF is 1 page for a full resume

### Block 3: Multi-Resume Templates (#22)
- [ ] DB: `resume_templates` table (migration v3)
- [ ] Backend: CRUD endpoints for templates
- [ ] Backend: import creates template entry
- [ ] Backend: generate uses selected template
- [ ] Frontend: template list + default selector in KnowledgeBank
- [ ] Test: import DOCX → template stored, generate uses it

### Block 4: Cost Tracking UI (#23)
- [ ] Backend: accurate cost calculation from token_usage
- [ ] Frontend: show real cost in Settings
- [ ] Test: cost reflects actual API calls
