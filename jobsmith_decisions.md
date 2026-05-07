# Jobsmith — Decisions Log

All design, tech, and architecture decisions for the Jobsmith job search agent.

---

## Design Decisions

| # | Decision | Chosen | Why | Date |
|---|----------|--------|-----|------|
| JD1 | Agent name | Jobsmith | Crafting/forging metaphor for resume building | 2026-04-28 |
| JD2 | Color theme | Blue | Distinct from NestScout purple | 2026-04-28 |
| JD3 | Adzuna credential format | Split into two fields (App ID + App Key) | `app_id\|app_key` pipe format is confusing — users paste wrong key | 2026-05-06 |

## Tech Decisions

| # | Decision | Chosen | Alternatives | Why | Date |
|---|----------|--------|-------------|-----|------|
| JT1 | Job board architecture | Plugin pattern (JSearchPlugin, AdzunaPlugin, RemoteOKPlugin) | Direct API calls | OCP — new boards are just new classes | 2026-04-28 |
| JT2 | Board fallback | When premium boards fail (429), auto-fallback to free boards | Skip free when premium exists | JSearch 429s leave user with nothing | 2026-05-06 |

---

## Known Issues (to fix)

### JI1: Consultancy/Staffing Agency Filtering
**Problem:** Search results include jobs from staffing agencies (Infosys, Wipro, TCS, Cognizant, Accenture, etc.) which are typically contract roles with lower pay, not direct-hire positions.

**Fix:** Add a post-fetch filter like `job_filter.py` that detects staffing companies by name and filters them out. User should be able to toggle this on/off.

**Staffing company keywords:** Infosys, Wipro, TCS, Cognizant, Accenture, HCL, Tech Mahindra, Capgemini, Deloitte (consulting), Randstad, Robert Half, TEKsystems, Insight Global, Dice (staffing), Apex Systems, Kforce, Manpower, Kelly Services, Adecco, CGI, Mindtree, Mphasis, LTIMindtree, UST, Persistent Systems, Hexaware, Cyient, NIIT, Syntel

**Toggle:** `exclude_consultancy` in search preferences.

### JI2: Clearance/Citizenship Filter Not Applied
**Problem:** User sees jobs requiring security clearance or US citizenship even though they can't get those. The filter exists in `job_filter.py` but it's only activated from `resume_preferences` in the profile — which the user hasn't set.

**Fix:**
- Add clearance/citizenship/sponsorship toggles directly to the search UI (not buried in profile)
- Default `exclude_clearance: true` — most users can't get clearance
- Default `exclude_sponsorship: false` — let user opt in to filter these
- Make filters persist per search session

### JI3: Duplicate Results Across Searches
**Problem:** Same job appears multiple times across different searches. Dedup only checks within the current batch, not against DB.

**Fix:**
- Check `source_url` against DB before saving (already done in `save_job` but not in the display)
- Also dedup by `title + company` fuzzy match (same job listed on LinkedIn AND Indeed has different URLs)
- Show "already saved" badge on duplicate results instead of hiding them

### JI4: Natural Language Search
**Problem:** Search is keyword-only. User types "SDET" and gets raw keyword match. No understanding of "software engineer backend python Austin remote" as a structured query.

**Fix:** Parse natural language search input into structured filters:
- Extract title (SDET, backend engineer, ML engineer)
- Extract location (Austin, TX / remote / hybrid)
- Extract skills (Python, Java, React)
- Extract preferences (no clearance, visa sponsor, senior level)
- Use same approach as NestScout search — structured `SearchCriteria` from free text

**Implementation:** `parse_job_search_query(text) -> SearchFilters` — can be algorithmic (regex + NLP) or LLM-powered.

### JI5: Filters Not Respected
**Problem:** Search filters (remote only, salary range, posted within days) are passed to the API but not always enforced:
- JSearch `salary_min/salary_max` params not sent to API
- `posted_within_days` only maps to "week/month/all" — not exact day filtering
- Remote filter on JSearch only applies to `remote_jobs_only` but Adzuna/RemoteOK handle it differently

**Fix:**
- Send salary params to JSearch API
- Post-filter by exact posted date (not just API buckets)
- Normalize remote handling across all boards

### JI6: No Smart Ranking
**Problem:** Results sorted only by match_score (algorithmic skill matching). No consideration of:
- Company reputation / glassdoor rating
- Salary vs market rate
- Commute distance
- Job freshness (newer = better)

**Fix (future):** Composite score: `match_score * 0.4 + freshness * 0.2 + salary_fit * 0.2 + company_quality * 0.2`. But this requires more data — YAGNI for now, algorithmic score is sufficient.

---

## Priority Order

1. **JI2** — Clearance/citizenship filter (quick fix, high impact — stop showing irrelevant jobs)
2. **JI1** — Consultancy filter (medium effort, high impact)
3. **JI3** — Dedup across searches (medium effort, medium impact)
4. **JI4** — Natural language search (high effort, high impact — but needs LLM or good NLP)
5. **JI5** — Filter enforcement (medium effort, medium impact)
6. **JI6** — Smart ranking (future — needs more data sources)
