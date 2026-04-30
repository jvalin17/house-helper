# SahAIy — Runbook & Architecture Reference

> Last updated: 2026-04-27

---

## Table of Contents

1. [Frontend Architecture](#1-frontend-architecture)
2. [Design Patterns](#2-design-patterns)
3. [Component Reference](#3-component-reference)
4. [API Client](#4-api-client)
5. [Database Schema](#5-database-schema)
6. [Table Relationships](#6-table-relationships)
7. [What Can Break & How to Fix It](#7-what-can-break--how-to-fix-it)
8. [Test Suite](#8-test-suite)

---

## 1. Frontend Architecture

### Tech Stack

| Layer | Choice | Version |
|-------|--------|---------|
| Framework | React | 19 |
| Language | TypeScript | 5.x |
| Build | Vite | 8 |
| Styling | Tailwind CSS | 4 |
| Components | shadcn/ui (base-ui) | latest |
| Routing | react-router-dom | 7 |
| Testing | vitest + @testing-library/react | 4.1 |
| Toasts | sonner | latest |
| Desktop | Tauri | 2 |

### Directory Structure

```
frontend/src/
├── api/
│   └── client.ts              # Single API client — ALL backend communication
├── assets/                    # Static assets
├── components/
│   ├── ui/                    # shadcn/ui primitives (Button, Card, Input, etc.)
│   ├── shared/                # Reusable components (Modal, StatCard)
│   ├── tabs/                  # Top-level tab containers
│   │   ├── JobSearchTab.tsx   # Search, match, evaluate, tailor
│   │   ├── ResumeBuilderTab.tsx  # Knowledge bank + resume builder
│   │   ├── DashboardTab.tsx   # Stats, applications, saved resumes
│   │   └── SettingsTab.tsx    # LLM config, budget, sources
│   ├── knowledge/             # Knowledge bank sub-components
│   │   ├── TemplateManager.tsx
│   │   ├── ExperienceList.tsx
│   │   ├── EducationList.tsx
│   │   ├── ProjectList.tsx
│   │   └── SkillsDisplay.tsx
│   ├── settings/              # Settings sub-components
│   │   ├── ProviderCard.tsx
│   │   └── BudgetCard.tsx
│   ├── resume/
│   │   └── MatchProgression.tsx  # Score visualization
│   ├── PreviewModal.tsx       # 6-step resume generation wizard
│   ├── ResumeAnalysis.tsx     # Analysis step with selectable suggestions
│   ├── ResumeResult.tsx       # Result step with export buttons
│   ├── JobInput.tsx           # Parse jobs from text/URL
│   ├── JobList.tsx            # Job results table
│   ├── JobDetail.tsx          # Single job detail dialog
│   ├── ResumeUpload.tsx       # Drag-drop resume import
│   ├── ApplyPipeline.tsx      # Multi-stage application pipeline
│   ├── ApplicationTracker.tsx # Track application statuses
│   ├── SavedResumes.tsx       # Manage saved resumes (max 5)
│   ├── KnowledgeBank.tsx      # KB container (experiences, skills, education, projects)
│   ├── Settings.tsx           # Settings container
│   ├── GenerationPrefs.tsx    # Resume generation preferences
│   └── ErrorBoundary.tsx      # React error boundary
├── hooks/
│   ├── useAuth.ts             # JWT token management + auth mode
│   └── useAsync.ts            # Generic async state (data/error/loading)
├── pages/
│   ├── Home.tsx               # Landing page with agent cards
│   ├── JobDashboard.tsx       # Main app — 4-tab layout
│   ├── Login.tsx              # Multi-user login form
│   └── Signup.tsx             # Multi-user registration form
├── types/
│   └── index.ts               # ALL shared TypeScript interfaces
├── lib/
│   └── utils.ts               # cn() utility (Tailwind class merging)
├── test/
│   ├── setup.ts               # Vitest config (jest-dom matchers)
│   ├── components.test.tsx    # Component unit tests
│   ├── hooks.test.tsx         # Hook unit tests
│   ├── pages.test.tsx         # Page tests
│   ├── shared.test.tsx        # Shared utilities tests
│   └── workflows/             # 27 integration test files
├── App.tsx                    # Router + AuthGuard + ErrorBoundary + Toaster
├── App.css                    # App styles
├── index.css                  # Global Tailwind styles
└── main.tsx                   # React entry point
```

### Data Flow

```
User action
    │
    ▼
Component (local useState)
    │
    ├── calls api.xxx() from api/client.ts
    │       │
    │       ├── attaches JWT token (from useAuth/getAuthToken)
    │       ├── sends fetch() to backend
    │       └── parses response or throws typed error
    │
    ├── updates local state
    │
    ├── shows toast (sonner) on success/failure
    │
    └── calls parent callback if needed (onApplied, onClose, etc.)
```

**There is NO global state management.** No Redux, no Context, no Zustand. Components manage their own state via `useState` and communicate via props/callbacks. This is deliberate — the app is a CRUD tool where each tab is self-contained.

---

## 2. Design Patterns

### 2.1 Auth Guard Pattern (`App.tsx`)

```
App.tsx
├── ErrorBoundary (catches all render errors)
├── Toaster (global toast notifications)
└── BrowserRouter
    ├── /login, /signup  (only in multi-user mode)
    ├── / → AuthGuard → Home
    └── /job → AuthGuard → JobDashboard
```

**AuthGuard** checks `authMode`:
- `local` mode: always renders children (no login needed)
- `multi` mode: redirects to `/login` if no JWT token

**What breaks it:** If `/api/auth/config` endpoint is down, the guard shows infinite loading. The guard defaults to `local` if the fetch fails.

### 2.2 Keep-Alive Tabs (`JobDashboard.tsx`)

Tabs are **never unmounted**. Active tab is shown, others get `className="hidden"`.

```tsx
<div className={activeTab === "search" ? "" : "hidden"}>
  <JobSearchTab />
</div>
<div className={activeTab === "lab" ? "" : "hidden"}>
  <ResumeBuilderTab />
</div>
```

**Why:** Switching tabs preserves search results, form state, scroll position. No re-fetching.

**What breaks it:** If a tab throws during render, the ErrorBoundary catches it for the whole page, not just the tab.

### 2.3 Step-Based Wizard (`PreviewModal.tsx`)

The resume generation flow is a state machine:

```
"checking" ──→ "empty-kb" (if no KB data)
    │
    ▼
"analyzing" ──→ "analysis" (show suggestions)
                    │
                    ▼
              "generating" ──→ "result" (resume + cover letter)
                                  │
                                  ▼
                              "applied" (tracked)
```

Each step renders different UI via conditional rendering. State is managed with ~10 `useState` hooks.

**What breaks it:** If `api.analyzeResumeFit()` returns an error field, it stays on "checking" with an error banner and "Try Again" button. If `api.generateResume()` fails, it bounces back to "analysis" step with the error shown.

### 2.4 Centralized API Client (`api/client.ts`)

Single file with all backend communication. Pattern:

```typescript
async function request<T>(path: string, options?: RequestInit): Promise<T> {
  // 1. Get JWT token from localStorage
  // 2. Attach to Authorization header
  // 3. Fetch
  // 4. Parse error from response.detail (nested extraction)
  // 5. Return typed result
}

// Three variants:
request<T>()     // Throws on error (normal API calls)
fetchChecked()   // Returns raw Response (for blob downloads)
safeFetch<T>()   // Returns fallback value on error (settings, non-critical)
```

**Error extraction priority:**
1. `error.detail.error.message`
2. `error.detail.message`
3. `error.detail` (string)
4. HTTP status text

**What breaks it:** If the backend changes a response shape, TypeScript types won't catch it at runtime. Always check `types/index.ts` matches backend Pydantic models.

### 2.5 shadcn/ui Component Pattern

UI components use:
- `@base-ui/react` for accessibility (ARIA, keyboard handling)
- CVA (Class Variance Authority) for variant styles
- Tailwind CSS for visual styling
- `cn()` (clsx + twMerge) for conditional classes

```typescript
// Example: Button variants
const buttonVariants = cva("base classes", {
  variants: {
    variant: { default: "...", outline: "...", ghost: "...", destructive: "..." },
    size: { sm: "...", default: "...", lg: "...", icon: "..." }
  }
})
```

### 2.6 Toast Pattern (sonner)

```tsx
// In App.tsx root:
<Toaster position="bottom-right" richColors closeButton />

// In any component:
import { toast } from "sonner"
toast.success("Saved!")
toast.error("Failed: " + error.message)
```

No state management needed. Imperative API, called from anywhere.

---

## 3. Component Reference

### Pages

| Component | Route | Purpose |
|-----------|-------|---------|
| `Home` | `/` | Landing page, shows agent cards (Job Agent active, others "coming soon") |
| `JobDashboard` | `/job` | Main app with 4 tabs |
| `Login` | `/login` | Email+password login (multi-user mode only) |
| `Signup` | `/signup` | Registration form (multi-user mode only) |

### Tab Components

| Component | Tab | Manages |
|-----------|-----|---------|
| `JobSearchTab` | Search | Search form, job results, filters, selection, AI evaluate, detail, preview modal |
| `ResumeBuilderTab` | Superpower Lab | Sub-tabs: Knowledge Bank, Resume Builder (step flow) |
| `DashboardTab` | Dashboard | Stats, application tracker, saved resumes, reset |
| `SettingsTab` | Settings | LLM provider, budget, calibration |

### Key Components

| Component | What it does | Key states |
|-----------|-------------|------------|
| `PreviewModal` | 6-step resume generation wizard | step, analysis, resume, coverLetter, error |
| `ResumeAnalysis` | Shows suggestions with checkboxes + revision note | selectedSuggestions, revisionNote |
| `ResumeResult` | Export buttons (PDF/DOCX/MD), save, apply & track | savedName, exportLoading |
| `KnowledgeBank` | CRUD for experiences, skills, education, projects | activeSection, entries |
| `JobDetail` | Job info dialog with rating buttons | rating |
| `ApplicationTracker` | Status cards with update dropdown | applications, statusHistory |
| `SavedResumes` | List of explicitly saved resumes (max 5) | resumes |
| `Settings` | Provider picker, API key input, cost display | config, providers, models |
| `ErrorBoundary` | Catches render errors, shows fallback UI | hasError, error |

### Shared Types (`types/index.ts`)

| Type | Fields | Used By |
|------|--------|---------|
| `Job` | id, title, company, match_score, parsed_data, match_breakdown, url | JobSearchTab, JobList, JobDetail |
| `Application` | id, job_id, status, resume_id, cover_letter_id, created_at | ApplicationTracker, DashboardTab |
| `AnalysisData` | current_resume_match, knowledge_bank_match, strengths, gaps, suggested_improvements | PreviewModal, ResumeAnalysis |
| `Suggestion` | type, description, impact, source | ResumeAnalysis |
| `SavedResume` | id, job_title, job_company, save_name, is_saved, feedback | SavedResumes |
| `ResumeTemplate` | id, name, filename, format, is_default | TemplateManager |
| `Experience` | id, title, company, start_date, end_date, description | ExperienceList |
| `Skill` | id, name, category | SkillsDisplay |

---

## 4. API Client

### All Endpoints (`api/client.ts`)

#### Knowledge Bank
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `extractSkills(text)` | POST | `/api/kb/extract-skills` | skills array |
| `listEntries()` | GET | `/api/kb/entries` | {experiences, skills, education, projects} |
| `createEntry(entry)` | POST | `/api/kb/entries` | created entry |
| `updateEntry(id, entry)` | PUT | `/api/kb/entries/{id}` | updated entry |
| `deleteEntry(id)` | DELETE | `/api/kb/entries/{id}` | void |
| `deleteEducation(id)` | DELETE | `/api/kb/education/{id}` | void |
| `deleteProject(id)` | DELETE | `/api/kb/projects/{id}` | void |
| `importResume(file)` | POST | `/api/kb/import-resume` | parsed data |

#### Templates
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `listTemplates()` | GET | `/api/kb/templates` | template array |
| `uploadTemplate(file)` | POST | `/api/kb/templates` | template |
| `deleteTemplate(id)` | DELETE | `/api/kb/templates/{id}` | void |
| `setDefaultTemplate(id)` | PUT | `/api/kb/templates/{id}/default` | void |

#### Jobs
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `searchJobs(filters)` | POST | `/api/jobs/search` | {jobs} |
| `parseJobs(inputs)` | POST | `/api/jobs/parse` | parsed jobs |
| `listJobs()` | GET | `/api/jobs` | jobs array |
| `getJob(id)` | GET | `/api/jobs/{id}` | job |
| `deleteJob(id)` | DELETE | `/api/jobs/{id}` | void |

#### Matching
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `matchJob(jobId, resumeId?)` | POST | `/api/jobs/{id}/match` | {score} |
| `matchBatch(jobIds, resumeId?)` | POST | `/api/jobs/match-batch` | {scores} |

#### Resumes
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `analyzeResumeFit(jobId)` | POST | `/api/resumes/analyze` | AnalysisData |
| `generateResume(jobId, prefs)` | POST | `/api/resumes/generate` | GeneratedResume |
| `exportResume(id, format)` | GET | `/api/resumes/{id}/export?format=` | Response (blob) |
| `saveResumeExplicit(id)` | POST | `/api/resumes/{id}/save` | {saved, name} |
| `unsaveResume(id)` | POST | `/api/resumes/{id}/unsave` | void |
| `listSavedResumes()` | GET | `/api/resumes/saved` | SavedResume[] |
| `getSavedCount()` | GET | `/api/resumes/saved/count` | {count, max} |

#### Cover Letters
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `generateCoverLetter(jobId, prefs)` | POST | `/api/cover-letters/generate` | GeneratedCoverLetter |
| `exportCoverLetter(id, format)` | GET | `/api/cover-letters/{id}/export?format=` | Response (blob) |

#### Applications
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `createApplication(jobId, resumeId?, coverLetterId?)` | POST | `/api/applications` | {id} |
| `listApplications()` | GET | `/api/applications` | Application[] |
| `updateApplicationStatus(id, status)` | PUT | `/api/applications/{id}/status` | void |
| `getApplicationHistory(id)` | GET | `/api/applications/{id}/history` | StatusEntry[] |

#### Settings
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `getLLMConfig()` | GET | `/api/settings/llm` | config |
| `saveLLM(config)` | PUT | `/api/settings/llm` | void |
| `getBudget()` | GET | `/api/settings/budget` | budget info |
| `getLLMProviders()` | GET | `/api/settings/llm/providers` | provider list |
| `getLLMModels()` | GET | `/api/settings/llm/models` | model list |

#### Dashboard
| Function | Method | Endpoint | Returns |
|----------|--------|----------|---------|
| `getStats()` | GET | `/api/stats` | AppStats |
| `resetDashboard()` | POST | `/api/dashboard/reset` | {deleted} |

---

## 5. Database Schema

### Overview

- **Engine:** SQLite with WAL mode
- **Location:** `~/.sahaiy/sahaiy.db` (local mode)
- **Multi-user:** `~/.sahaiy/users/{id}/data.db` (per user)
- **Auth DB:** `~/.sahaiy/auth.db` (multi-user mode only)
- **Migration system:** `PRAGMA user_version` (current: v4)
- **Schema file:** `backend/shared/db.py`

### All Tables (20 total)

#### profiles
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| name | TEXT | NOT NULL |
| type | TEXT | DEFAULT 'focus' |
| description | TEXT | |
| search_title | TEXT | |
| search_keywords | TEXT | |
| search_location | TEXT | |
| search_remote | INTEGER | DEFAULT 0 |
| resume_preferences | JSON | |
| is_active | INTEGER | DEFAULT 0 |
| created_at | TEXT | DEFAULT datetime('now') |

Default profile (id=1) always exists.

#### experiences
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| type | TEXT | NOT NULL |
| title | TEXT | NOT NULL |
| company | TEXT | |
| start_date | TEXT | |
| end_date | TEXT | |
| description | TEXT | |
| metadata | JSON | |
| created_at | TEXT | DEFAULT datetime('now') |
| updated_at | TEXT | DEFAULT datetime('now') |

#### skills
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| name | TEXT | NOT NULL |
| category | TEXT | NOT NULL |
| proficiency | TEXT | |
| source_experience_id | INTEGER | FK → experiences(id) |
| created_at | TEXT | DEFAULT datetime('now') |

UNIQUE constraint on (name, profile_id).

#### achievements
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| experience_id | INTEGER | FK → experiences(id) |
| description | TEXT | NOT NULL |
| metric | TEXT | |
| impact | TEXT | |
| metadata | JSON | |
| created_at | TEXT | DEFAULT datetime('now') |

#### education
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| institution | TEXT | NOT NULL |
| degree | TEXT | |
| field | TEXT | |
| start_date | TEXT | |
| end_date | TEXT | |
| metadata | JSON | |
| created_at | TEXT | DEFAULT datetime('now') |

#### projects
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| name | TEXT | NOT NULL |
| description | TEXT | |
| tech_stack | JSON | |
| url | TEXT | |
| metadata | JSON | |
| created_at | TEXT | DEFAULT datetime('now') |

#### jobs
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| title | TEXT | NOT NULL |
| company | TEXT | |
| source_url | TEXT | |
| source_text | TEXT | |
| parsed_data | JSON | NOT NULL |
| match_score | REAL | |
| match_breakdown | JSON | |
| status | TEXT | DEFAULT 'saved' |
| created_at | TEXT | DEFAULT datetime('now') |

#### resumes
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| job_id | INTEGER | FK → jobs(id) |
| content | TEXT | NOT NULL |
| preferences | JSON | NOT NULL |
| export_path | TEXT | |
| export_format | TEXT | |
| feedback | INTEGER | |
| created_at | TEXT | DEFAULT datetime('now') |
| docx_binary | BLOB | (migration v2) |
| is_saved | INTEGER | DEFAULT 0 (migration v4) |
| save_name | TEXT | (migration v4) |

Two-tier system: ephemeral (is_saved=0, auto-cleaned after 24h) and curated (is_saved=1, max 5).

#### cover_letters
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| job_id | INTEGER | FK → jobs(id) |
| content | TEXT | NOT NULL |
| preferences | JSON | |
| export_path | TEXT | |
| export_format | TEXT | |
| feedback | INTEGER | |
| created_at | TEXT | DEFAULT datetime('now') |
| updated_at | TEXT | DEFAULT datetime('now') |

#### applications
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| job_id | INTEGER | FK → jobs(id) | NOT NULL |
| resume_id | INTEGER | FK → resumes(id) |
| cover_letter_id | INTEGER | FK → cover_letters(id) |
| status | TEXT | NOT NULL, DEFAULT 'applied' |
| notes | TEXT | |
| created_at | TEXT | DEFAULT datetime('now') |
| updated_at | TEXT | DEFAULT datetime('now') |

#### application_status_history
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| application_id | INTEGER | FK → applications(id), NOT NULL |
| status | TEXT | NOT NULL |
| changed_at | TEXT | DEFAULT datetime('now') |

Audit trail — every status change creates a new row.

#### search_filters
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| name | TEXT | NOT NULL |
| filters | JSON | NOT NULL |
| frequency_hours | INTEGER | |
| last_run | TEXT | |
| is_active | INTEGER | DEFAULT 1 |
| created_at | TEXT | DEFAULT datetime('now') |

#### auto_apply_queue
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| profile_id | INTEGER | FK → profiles(id) |
| job_id | INTEGER | FK → jobs(id), NOT NULL |
| resume_id | INTEGER | FK → resumes(id) |
| cover_letter_id | INTEGER | FK → cover_letters(id) |
| apply_method | TEXT | |
| status | TEXT | DEFAULT 'pending' |
| confirmed_at | TEXT | |
| applied_at | TEXT | |
| created_at | TEXT | DEFAULT datetime('now') |

State machine: pending → confirmed → applied.

#### evidence_log
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| entity_type | TEXT | NOT NULL |
| entity_id | INTEGER | NOT NULL |
| source | TEXT | NOT NULL |
| original_text | TEXT | |
| created_at | TEXT | DEFAULT datetime('now') |

Tracks provenance of knowledge bank entries.

#### settings
| Column | Type | Constraints |
|--------|------|-------------|
| key | TEXT | PRIMARY KEY |
| value | JSON | NOT NULL |
| updated_at | TEXT | DEFAULT datetime('now') |

Key-value store. Known keys: `preferences`, `llm`, `token_budget`, `original_resume`, `original_resume_docx`, `original_resume_map`.

#### token_usage
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| feature | TEXT | NOT NULL |
| provider | TEXT | NOT NULL |
| tokens_used | INTEGER | NOT NULL |
| estimated_cost | REAL | |
| created_at | TEXT | DEFAULT datetime('now') |

Time-series log of LLM costs per feature.

#### calibration_judgements
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| job_id | INTEGER | FK → jobs(id) |
| match_score | REAL | NOT NULL |
| match_features | JSON | NOT NULL |
| user_rating | TEXT | NOT NULL ('good'/'partial'/'poor') |
| notes | TEXT | |
| created_at | TEXT | DEFAULT datetime('now') |

User feedback on match scores used to improve algorithm weights.

#### suggestion_feedback (migration v3)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| suggestion_text | TEXT | NOT NULL |
| original_bullet | TEXT | |
| reason | TEXT | |
| created_at | TEXT | DEFAULT datetime('now') |

Stores rejected LLM suggestions — fed back into prompts to avoid repeating bad suggestions.

#### resume_templates (migration v3)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| name | TEXT | NOT NULL |
| filename | TEXT | NOT NULL |
| format | TEXT | NOT NULL |
| raw_text | TEXT | |
| docx_binary | BLOB | |
| paragraph_map | JSON | |
| is_default | INTEGER | DEFAULT 0 |
| created_at | TEXT | DEFAULT datetime('now') |

Max 5 templates. One marked as default. DOCX binary stored for format-preserving generation.

#### users (auth DB only)
| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| email | TEXT | UNIQUE, NOT NULL |
| password_hash | TEXT | NOT NULL |
| name | TEXT | NOT NULL |
| created_at | TEXT | DEFAULT datetime('now') |
| updated_at | TEXT | DEFAULT datetime('now') |

Only exists in `~/.sahaiy/auth.db` when AUTH_MODE=multi.

---

## 6. Table Relationships

### Entity Relationship Diagram

```
                          ┌──────────┐
                          │ profiles │
                          └────┬─────┘
                               │ 1:N on profile_id
          ┌────────────┬───────┼───────┬──────────────┐
          │            │       │       │              │
     ┌────▼───┐  ┌─────▼──┐ ┌─▼──┐ ┌──▼────┐  ┌──────▼──────┐
     │  jobs  │  │ exper. │ │ .. │ │ cover │  │ applications│
     └───┬────┘  └───┬────┘ └────┘ │ ltrs  │  └──────┬──────┘
         │           │             └───┬───┘         │
    ┌────┼────┐  ┌───▼────┐            │        ┌────▼────────────┐
    │    │    │  │achieve.│            │        │ status_history  │
    │    │    │  └────────┘            │        └─────────────────┘
    │    │    │                        │
┌───▼──┐ │   │   ┌───────────────┐    │
│resum.│◄┼───┼───┤auto_apply_que.├────┘
└──┬───┘ │   │   └───────────────┘
   │     │   │
   │  ┌──▼───────────────┐
   │  │calibration_judge.│
   │  └──────────────────┘
   │
   └──→ applications (resume_id FK)
```

### Foreign Key Summary

| From Table | Column | To Table | Column | Nullable |
|------------|--------|----------|--------|----------|
| experiences | profile_id | profiles | id | Yes |
| skills | profile_id | profiles | id | Yes |
| skills | source_experience_id | experiences | id | Yes |
| achievements | experience_id | experiences | id | Yes |
| jobs | profile_id | profiles | id | Yes |
| resumes | profile_id | profiles | id | Yes |
| resumes | job_id | jobs | id | Yes |
| cover_letters | profile_id | profiles | id | Yes |
| cover_letters | job_id | jobs | id | Yes |
| applications | profile_id | profiles | id | Yes |
| applications | job_id | jobs | id | **NOT NULL** |
| applications | resume_id | resumes | id | Yes |
| applications | cover_letter_id | cover_letters | id | Yes |
| application_status_history | application_id | applications | id | **NOT NULL** |
| search_filters | profile_id | profiles | id | Yes |
| auto_apply_queue | profile_id | profiles | id | Yes |
| auto_apply_queue | job_id | jobs | id | **NOT NULL** |
| auto_apply_queue | resume_id | resumes | id | Yes |
| auto_apply_queue | cover_letter_id | cover_letters | id | Yes |
| calibration_judgements | job_id | jobs | id | Yes |

### Delete Cascade Implications

SQLite foreign keys are ON with `PRAGMA foreign_keys=ON`, but **no CASCADE rules are defined**. Deleting a parent row when children exist will fail with a constraint error.

**Dashboard reset** (`backend/agents/job/services/reset.py`) handles this by deleting in correct order:
1. application_status_history
2. applications
3. auto_apply_queue
4. cover_letters
5. calibration_judgements
6. evidence_log
7. ephemeral resumes (is_saved=0)
8. jobs

It preserves: KB (experiences, skills, education, projects), settings, templates, saved resumes, feedback.

---

## 7. What Can Break & How to Fix It

### Critical Failures

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Blank page on load** | ErrorBoundary caught a render error | Check browser console. Common: undefined data passed as props. Fix the component that throws. |
| **"Failed to fetch" on every action** | Backend is down | Start backend: `cd backend && python main.py`. Check port 8040. |
| **Infinite loading on login** | `/api/auth/config` endpoint down or CORS | Check backend logs. In local mode, this should return `{mode: "local"}`. |
| **"_ARRAY_API not found"** | numpy >= 2.0 installed with PyTorch 2.2 | `pip install "numpy<2"` |
| **sentence-transformers import error** | Python 3.14 or wrong PyTorch | Use Python 3.12. `pip install torch==2.2.2` |
| **LLM returns empty/wrong results** | Wrong provider/model config | Check Settings tab. Verify API key. Check `settings` table `llm` key. |
| **Search returns 0 results** | JSearch API key missing or quota exhausted | Add JSEARCH_API_KEY to .env. Free tier: 500 calls/month. |

### Frontend Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| **Stale data after tab switch** | Tab component cached old state | Add `refreshKey` prop or `useEffect` that fetches on tab focus. |
| **Toast shows but nothing happened** | API returned success but data didn't update | Check if component re-fetches after mutation. Look for missing `await` or missing state update. |
| **Modal won't close** | Error thrown during close handler | Check `onClose` callback. Wrap in try/catch. |
| **TypeScript build fails** | Type mismatch between frontend types and API response | Update `types/index.ts` to match backend Pydantic models. |
| **Tests fail after API change** | Mock data doesn't match new types | Update mock data in test files. Check `vi.mocked(api.xxx).mockResolvedValue(...)`. |
| **"Cannot read property of undefined"** | API response changed shape | Add null checks. Check if backend added/removed fields. |

### Backend Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| **DB locked** | Long-running query blocking WAL | Restart backend. Check for hung LLM calls. |
| **Migration fails** | Schema version mismatch | Check `PRAGMA user_version`. Manually run missing ALTER TABLE statements from `db.py`. |
| **LLM provider not updating** | Provider loaded at startup, not per-request | Restart backend after changing provider in Settings. |
| **Export produces empty PDF** | WeasyPrint missing system deps (libpango) | macOS: `brew install pango`. Linux: `apt install libpango-1.0-0`. |
| **DOCX formatting broken** | Template paragraph_map doesn't match content | Re-upload template. Check `docx_surgery.py` paragraph mapping. |

### Recovery Procedures

**Reset everything (keep KB):**
1. Click Dashboard → Reset Dashboard (deletes jobs, apps, ephemeral resumes)
2. Or directly: `DELETE FROM jobs; DELETE FROM applications; ...` in correct FK order

**Reset everything (fresh start):**
1. Delete `~/.sahaiy/sahaiy.db`
2. Restart backend — it recreates with fresh schema

**Fix broken migration:**
1. Check version: `sqlite3 ~/.sahaiy/sahaiy.db "PRAGMA user_version;"`
2. Compare with expected version in `backend/shared/db.py`
3. Run missing ALTER TABLE statements manually
4. Update: `sqlite3 ~/.sahaiy/sahaiy.db "PRAGMA user_version = 4;"`

---

## 8. Test Suite

### Overview

| Suite | Count | Framework | Location |
|-------|-------|-----------|----------|
| Backend | 527+ | pytest | `backend/tests/` |
| Frontend | 90+ | vitest | `frontend/src/test/` |
| **Total** | **617+** | | |

### Frontend Test Structure

```
src/test/
├── setup.ts              # jest-dom matchers
├── components.test.tsx   # Unit: individual components render correctly
├── hooks.test.tsx        # Unit: useAsync, useAuth behavior
├── pages.test.tsx        # Unit: Home, JobDashboard, Login, Signup
├── shared.test.tsx       # Unit: shared components (Modal, StatCard)
└── workflows/            # Integration: full user flows
    ├── scout-jobs.test.tsx           # Search → results → match
    ├── job-search-extra.test.tsx     # AI evaluate, clear, filters
    ├── tailor-resume.test.tsx        # Full resume generation flow
    ├── preview-modal-extra.test.tsx  # Export, save, error paths
    ├── apply-track.test.tsx          # Apply & Track flow
    ├── revision-loop.test.tsx        # Regenerate with revisions
    ├── save-resume.test.tsx          # Save/unsave/max 5
    ├── flag-suggestion.test.tsx      # Flag incorrect suggestions
    ├── import-resume.test.tsx        # Resume file upload
    ├── upload-template.test.tsx      # Template upload
    ├── experience-crud.test.tsx      # Experience CRUD
    ├── education-list.test.tsx       # Education display
    ├── project-list.test.tsx         # Project display
    ├── skills-display.test.tsx       # Skills display
    ├── extract-skills.test.tsx       # Skill extraction
    ├── knowledge-bank-extra.test.tsx # KB edge cases
    ├── application-tracker.test.tsx  # Application tracking
    ├── configure-llm.test.tsx        # LLM config
    ├── view-ai-usage.test.tsx        # Cost tracking
    ├── calibration.test.tsx          # Match calibration
    ├── dashboard-reset.test.tsx      # Reset functionality
    ├── search-defaults.test.tsx      # Search defaults
    ├── resume-flows.test.tsx         # Resume flow states
    ├── resume-selector-and-ai-evaluate.test.tsx  # Resume selection
    ├── saved-resumes-preview.test.tsx  # Saved resume preview
    ├── job-detail.test.tsx           # Job detail dialog
    └── error-boundary.test.tsx       # Error handling
```

### Running Tests

```bash
# Frontend
cd frontend && npx vitest run

# Backend
cd backend && python -m pytest

# Frontend watch mode
cd frontend && npx vitest

# Single test file
cd frontend && npx vitest run src/test/workflows/scout-jobs.test.tsx
```

### Test Patterns

All frontend tests follow:
1. **Mock API**: `vi.mock("@/api/client")` at top of file
2. **Setup mocks**: `vi.mocked(api.xxx).mockResolvedValue(...)` in `beforeEach`
3. **Render**: `render(<Component />)` with necessary wrappers (BrowserRouter, Toaster)
4. **Assert**: `expect(screen.getByText(...)).toBeInTheDocument()`
5. **Interact**: `await userEvent.click(screen.getByRole("button", { name: /.../ }))`
6. **Wait**: `await waitFor(() => expect(...))` for async operations
