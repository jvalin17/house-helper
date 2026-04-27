# Design Decisions Log

Decisions that affect behavior, limits, or costs. Check here when something seems wrong.

## Search

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| JSearch pages per search | 3 (= 30 results max) | Each page = 1 API call. Free tier = 500/month. 3 pages per search = ~166 searches/month. | 2026-04-27 |
| JSearch date_posted | "week" (7 days) | Fresh jobs only. API values: today, 3days, week, month, all | 2026-04-27 |
| JSearch country | "us" | Hardcoded US. Should be configurable per profile. | 2026-04-27 |
| RemoteOK max results | 30 | Client-side filtered from full API response | 2026-04-25 |
| Premium source priority | If JSearch/Adzuna available, skip RemoteOK | Avoid diluting quality results with generic ones | 2026-04-27 |

## Auto Apply

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| Max batch size | 5 jobs | Manageable review. User can run multiple batches. | 2026-04-25 |
| Apply method | Open URL in browser (no form fill yet) | Playwright form filling is planned but not built | 2026-04-25 |
| Confirmation | User must click "I've Applied" | Never fake a success message | 2026-04-26 |

## Resume Builder

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| Resume name format | Resume_Role_MM-YY.pdf | No company name in filename (stored in DB only) | 2026-04-26 |
| Template mode | Template assembly from knowledge bank | LLM mode ready but not connected | 2026-04-25 |
| ATS rules | Stored in ats_rules.json (updatable) | Domain knowledge evolves, shouldn't be hardcoded | 2026-04-26 |

## Database

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| Total tables | 17 | Normalized from 22. Settings is key-value. Calibration weights computed on-the-fly. | 2026-04-27 |
| API keys storage | settings table (key='api_keys') | Env vars lost across restarts. DB persists. .env seeded on first run. | 2026-04-27 |
| Profile types | 'focus' (shared knowledge) or 'person' (isolated) | Same DB, profile_id column on 7 tables | 2026-04-27 |

## API & Integration

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| HTTP client | httpx sync (not async) | Async + FastAPI thread pool = silent failures. Sync is simpler and works. | 2026-04-27 |
| Job board plugins | Sync search() method | Was async, caused event loop conflicts in FastAPI workers | 2026-04-27 |
| Legal sources only | JSearch API, Adzuna API, RemoteOK API | LinkedIn/Indeed scrapers removed (violates ToS) | 2026-04-26 |

## Frontend

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| Color palette | Blue/white shades only | User: "green = school project." Blue = professional. | 2026-04-26 |
| Tone | Calming, comforting | Job search is stressful. "One step at a time." | 2026-04-26 |
| No emojis in nav | Text only in tab bar | User: "not super exciting to apply for jobs" | 2026-04-26 |
| Tab order | Search → Superpower Lab → Dashboard → Settings | Matches user journey | 2026-04-25 |

## Token Budget

| Decision | Value | Why | Date |
|----------|-------|-----|------|
| Default | No limit until user configures | User asked: let them set it based on their plan | 2026-04-25 |
| Priority | resume_gen → job_search → cover_letter → extraction | Resume quality is highest value per token | 2026-04-25 |
