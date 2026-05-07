# Nest Lab — Detailed Implementation Plan

Each slab lists: exact files to create/modify, code changes, unit tests, integration tests, and "done" criteria.

**Process per slab:**
```
/implementation → write code with TDD
/precommit → quality gate
git commit + push
verify in browser (if frontend)
→ next slab
```

---

## Slab 1: DB Migration + Feature Preferences Repo

### Code Changes

**New file: `backend/shared/db.py`** (add migration v7)
```sql
-- Migration 7
CREATE TABLE IF NOT EXISTS apartment_feature_preferences (
    id INTEGER PRIMARY KEY,
    feature_name TEXT NOT NULL,
    category TEXT NOT NULL,
    preference TEXT NOT NULL DEFAULT 'neutral',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(feature_name)
);

CREATE TABLE IF NOT EXISTS apartment_lab_analysis (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES apartment_listings(id),
    analysis_type TEXT NOT NULL,
    result JSON NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    estimated_cost REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(listing_id, analysis_type)
);

CREATE TABLE IF NOT EXISTS apartment_qa_history (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES apartment_listings(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

**New file: `backend/agents/apartment/repositories/feature_preferences_repo.py`**
- `get_all_preferences() → list[dict]` — all feature preferences
- `get_preference(feature_name) → dict | None`
- `set_preference(feature_name, category, preference) → None` — upsert
- `get_must_haves() → list[str]` — features where preference='must_have'
- `get_deal_breakers() → list[str]` — features where preference='deal_breaker'
- `reset_preference(feature_name) → None` — delete (back to neutral)

**New file: `backend/agents/apartment/repositories/lab_analysis_repo.py`**
- `get_cached_analysis(listing_id, analysis_type) → dict | None` — returns if < 24h old
- `save_analysis(listing_id, analysis_type, result, tokens, cost) → int`
- `invalidate(listing_id) → None` — delete all cached analyses for a listing

**Modify: `backend/agents/apartment/routes.py`**
- Add `GET /api/apartments/preferences/features` → returns all preferences
- Add `PUT /api/apartments/preferences/features/{feature_name}` → set preference
  Body: `{"category": "unit", "preference": "must_have"}`
- Add `DELETE /api/apartments/preferences/features/{feature_name}` → reset to neutral

### Unit Tests

**New file: `tests/agents/apartment/test_feature_preferences_repo.py`**
```
TestGetPreferences:
  test_get_all_returns_empty_initially
  test_set_and_get_preference
  test_set_preference_upserts_on_duplicate
  test_get_must_haves_returns_only_must_haves
  test_get_deal_breakers_returns_only_deal_breakers
  test_reset_preference_removes_entry
  test_set_preference_validates_value  (rejects "invalid_state")

TestPreferenceValues:
  test_neutral_preference
  test_must_have_preference
  test_deal_breaker_preference
```

**New file: `tests/agents/apartment/test_lab_analysis_repo.py`**
```
TestCachedAnalysis:
  test_save_and_retrieve_analysis
  test_cache_returns_none_when_expired  (mock datetime to 25h ago)
  test_cache_returns_result_when_fresh  (saved just now)
  test_invalidate_deletes_all_for_listing
  test_get_nonexistent_returns_none
  test_save_overwrites_previous  (UNIQUE constraint → replace)
```

### Integration Test

**In `tests/agents/apartment/test_apartment_routes.py`** (add):
```
TestFeaturePreferencesAPI:
  test_set_and_get_feature_preference_via_api
  test_cycle_through_three_states_via_api  (neutral → must_have → deal_breaker → delete)
  test_get_preferences_returns_all_set_features
```

### Done Criteria
- `curl PUT /api/apartments/preferences/features/in-unit-wd` → saves must_have
- `curl GET /api/apartments/preferences/features` → returns list with in-unit-wd
- 16+ tests passing

---

## Slab 2: Lab Analysis Pipeline + LLM Overview

### Code Changes

**New directory: `backend/agents/apartment/prompts/`**
- `__init__.py`

**New file: `backend/agents/apartment/prompts/property_overview.py`**
- `SYSTEM_PROMPT` — constant string
- `build_overview_prompt(listing, preferences, comparable_listings) → str`
- Returns prompt that asks for: overview, price_verdict, neighborhood_intel, red_flags, green_lights, questions_to_ask, match_score
- Includes neighborhood questions (Layer 1 — LLM knowledge)

**New file: `backend/agents/apartment/services/lab_analyzer.py`**
- `class LabAnalyzerService`
- `__init__(listing_repo, feature_prefs_repo, lab_analysis_repo, llm_provider)`
- `analyze(listing_id) → dict` — runs full pipeline:
  1. gather_listing_data (from listing_repo)
  2. gather_preferences (from feature_prefs_repo)
  3. gather_comparables (from listing_repo — same city, similar beds)
  4. check_cache (from lab_analysis_repo — skip LLM if fresh)
  5. build_context (using build_context_package from shared/pipeline.py)
  6. run_llm (using provider_manager.complete)
  7. parse_result (using parse_llm_json_response from shared/pipeline.py)
  8. store_cache (save to lab_analysis_repo)
- `analyze_stream(listing_id) → Iterator[str]` — same but uses complete_stream
- `get_lab_data(listing_id) → dict` — returns all gathered data WITHOUT LLM (for no-LLM mode)

**Modify: `backend/agents/apartment/routes.py`**
- Add `GET /api/apartments/lab/{listing_id}` → calls lab_analyzer.analyze()
- Returns: `{listing, analysis, preferences, cost}`
- If no LLM: returns listing + preferences + cost without analysis

### Unit Tests

**New file: `tests/agents/apartment/test_lab_analyzer.py`**
```
TestLabAnalyzer:
  test_analyze_returns_structured_result_with_mock_llm
  test_analyze_returns_data_without_llm  (no analysis, but listing+prefs)
  test_analyze_uses_cache_when_fresh  (no LLM call when cached)
  test_analyze_calls_llm_when_cache_expired
  test_analyze_includes_comparable_listings_in_context
  test_analyze_includes_user_preferences_in_context
  test_analyze_handles_llm_error_gracefully  (returns partial data)
  test_analyze_stream_yields_chunks
```

**New file: `tests/agents/apartment/test_property_overview_prompt.py`**
```
TestBuildOverviewPrompt:
  test_prompt_includes_listing_title_and_address
  test_prompt_includes_price_and_beds_baths
  test_prompt_includes_user_must_haves
  test_prompt_includes_comparable_prices
  test_prompt_includes_neighborhood_questions
  test_prompt_fits_within_token_budget  (using fits_in_context)
```

### Integration Test

**In `tests/agents/apartment/test_apartment_routes.py`** (add):
```
TestLabAnalysisAPI:
  test_lab_endpoint_returns_listing_data
  test_lab_endpoint_returns_404_for_nonexistent_listing
  test_lab_endpoint_returns_cached_analysis_when_available
```

### Done Criteria
- `curl GET /api/apartments/lab/258` → returns listing data + analysis (if LLM connected)
- Without LLM: returns listing + preferences + features (no analysis section)
- Pipeline steps logged in console
- 14+ tests passing

---

## Slab 3: SSE Streaming Endpoint

### Code Changes

**Modify: `backend/agents/apartment/routes.py`**
- Add `GET /api/apartments/lab/{listing_id}/stream` (async def)
- Returns `StreamingResponse(generate(), media_type="text/event-stream")`
- Generator yields: progress events → LLM chunks → done event
- Uses `format_sse_stream()`, `format_sse_progress()` from shared/llm/streaming.py

### Unit Tests

**New file: `tests/agents/apartment/test_lab_streaming.py`**
```
TestLabStreamingEndpoint:
  test_stream_returns_event_stream_content_type
  test_stream_yields_progress_events
  test_stream_yields_done_event_with_full_text  (mock LLM)
  test_stream_handles_no_llm_gracefully
  test_stream_returns_404_for_nonexistent_listing
```

### Integration Test

```
TestLabStreamingIntegration:
  test_full_stream_with_mock_provider  (progress → chunks → done)
```

### Done Criteria
- `curl -N GET /api/apartments/lab/258/stream` → receives SSE events
- Each event is valid `data: {...}\n\n` format
- 6+ tests passing

---

## Slab 4: Walk Score + Google Distance Matrix

### Code Changes

**New file: `backend/agents/apartment/services/neighborhood_service.py`**
- `get_walk_scores(latitude, longitude, address, connection) → dict | None`
  - Reads `walkscore` key from `apartment_api_keys` in settings
  - Calls Walk Score API
  - Returns `{walk_score, walk_description, transit_score, bike_score}`
- `get_distance_to_airport(latitude, longitude, connection) → dict | None`
  - Reads `google_maps` key from settings
  - Calls Distance Matrix with destination=nearest airport
  - Returns `{distance_km, drive_minutes}`
- `get_commute_time(origin_lat, origin_lng, destination_address, connection) → dict | None`
  - Calls Distance Matrix with user's workplace
  - Returns `{distance_km, duration_minutes, mode}`
- `fetch_and_cache_neighborhood(listing_id, connection) → dict`
  - Orchestrates: walk scores + airport distance + commute
  - Saves to `apartment_neighborhood` table
  - Returns combined result

**Modify: `backend/agents/apartment/routes.py`**
- Add `GET /api/apartments/lab/{listing_id}/neighborhood` → fetch_and_cache_neighborhood
- Add `walkscore` and `google_maps` to built-in sources list

**Modify: `frontend/src/api/client.ts`**
- Add `getLabNeighborhood(listingId)` method

### Unit Tests

**New file: `tests/agents/apartment/test_neighborhood_service.py`**
```
TestWalkScore:
  test_returns_scores_with_mocked_api_response
  test_returns_none_when_no_api_key
  test_handles_api_error_gracefully

TestDistanceMatrix:
  test_returns_airport_distance_with_mocked_response
  test_returns_commute_time_with_mocked_response
  test_returns_none_when_no_google_key

TestFetchAndCache:
  test_caches_results_in_neighborhood_table
  test_returns_cached_results_on_second_call
```

### Integration Test

```
TestNeighborhoodAPI:
  test_neighborhood_endpoint_returns_404_for_nonexistent
  test_sources_endpoint_includes_walkscore_and_google
```

### Done Criteria
- `curl GET /api/apartments/sources` → shows Walk Score + Google Maps
- With keys configured: returns real scores
- Without keys: returns null gracefully
- 8+ tests passing

---

## Slab 5: Frontend — NestLabTab + Listing Picker

### Code Changes

**New file: `frontend/src/components/apartment/tabs/NestLabTab.tsx`**
- Shows nested (saved) listings as selectable cards
- Paste URL bar at top
- When listing selected → shows LabAnalysisView
- Back button to return to picker

**Modify: `frontend/src/pages/ApartmentDashboard.tsx`**
- Replace Lab placeholder with `<NestLabTab />`

**Modify: `frontend/src/api/client.ts`**
- Add `getLabAnalysis(listingId)` method
- Add `getLabAnalysisStream(listingId)` — returns EventSource URL
- Add `setFeaturePreference(name, category, preference)` method
- Add `getFeaturePreferences()` method

### Tests
- Frontend: manual verification (pick listing, paste URL)
- No automated frontend tests yet (deferred to hardening pass)

### Done Criteria
- Open NestScout → Nest Lab tab → see nested listings
- Click a listing → transitions to analysis view
- Paste URL → creates listing → opens in Lab
- Back button returns to picker

---

## Slab 6: Frontend — Hero Gallery + Key Facts + AI Overview

### Code Changes

**New file: `frontend/src/components/apartment/lab/LabAnalysisView.tsx`**
- Main scrollable page with section anchors
- Fetches lab data from `/api/apartments/lab/{id}`
- Connects to SSE stream for AI sections

**New file: `frontend/src/components/apartment/lab/HeroGallery.tsx`**
- Full-bleed photo carousel
- Click to open lightbox (fullscreen)
- Photo count badge
- Lazy loading (first 5 visible, rest load on scroll)

**New file: `frontend/src/components/apartment/lab/KeyFactsBar.tsx`**
- Sticky bar: price, beds, baths, sqft, address
- Nest/unnest button
- "Ask AI" button (scrolls to Q&A bar)

**New file: `frontend/src/components/apartment/lab/AiOverviewSection.tsx`**
- Connects to SSE stream via `useLabAnalysisStream` hook
- Shows skeleton while streaming
- Renders: overview text, price verdict badge, red flags, green lights
- Neighborhood intel section (from LLM)
- "Questions to ask on tour" list

**New file: `frontend/src/hooks/useLabAnalysisStream.ts`**
- Custom hook: manages EventSource connection
- Returns: `{progress, analysisText, structuredResult, isComplete, error}`

### Tests
- Manual verification (gallery, sticky bar, streaming text)

### Done Criteria
- Open listing in Lab → see full-bleed photo gallery
- Scroll → key facts bar sticks to top
- AI overview streams in (if LLM connected)
- Without LLM → overview section hidden, everything else visible

---

## Slab 7: Frontend — Feature Tags (3-State)

### Code Changes

**New file: `frontend/src/components/apartment/lab/FeatureTagsSection.tsx`**
- Displays all listing amenities as interactive tags
- Tap cycles: gray (neutral) → purple (must have) → red (deal breaker) → gray
- Grouped by category: Unit, Building, Neighborhood
- Persists via `PUT /api/apartments/preferences/features/{name}`
- On mount: loads user's existing preferences → pre-colors tags

### Tests
- Manual: tap tag cycles through 3 states, persists on refresh

### Done Criteria
- Tags display from listing amenities
- Tap cycles through 3 visual states
- Refresh page → preferences preserved
- Open different listing → same preferences applied

---

## Slab 8: Frontend — Neighborhood Section + "Get More Info"

### Code Changes

**New file: `frontend/src/components/apartment/lab/NeighborhoodSection.tsx`**
- Default: shows LLM-generated neighborhood intel (from AI overview response)
- "Get more info" button → calls `GET /lab/{id}/neighborhood`
- After fetch: shows Walk Score / Transit Score / Bike Score as visual gauges
- Shows airport distance + drive time
- Shows commute time (if user has workplace set in preferences)
- Cached: second open shows data instantly

### Tests
- Manual: "Get more info" fetches scores, displays gauges

### Done Criteria
- LLM neighborhood text shows by default
- Click "Get more info" → scores appear (if API keys set)
- Without API keys → shows helpful "Connect in Settings" message

---

## Slab 9: Price Intelligence + Cost Calculator

### Code Changes

**New file: `backend/agents/apartment/repositories/cost_repo.py`**
- `get_cost(listing_id) → dict | None`
- `save_cost(listing_id, **fields) → int`

**New file: `backend/agents/apartment/services/price_analyzer.py`**
- `get_price_context(listing_id, connection) → dict`
  - Listing price, comparable listings (same city+beds), area median
  - Returns: `{listing_price, area_median, percentile, comparable_count}`

**Modify: `backend/agents/apartment/routes.py`**
- Add `GET /api/apartments/cost/{listing_id}` → get_cost
- Add `PUT /api/apartments/cost/{listing_id}` → save_cost (user-editable)

**New file: `frontend/src/components/apartment/lab/PriceIntelligence.tsx`**
- Price verdict badge (from AI overview)
- Cost breakdown: editable fields (parking, pet fee, utilities, deposit)
- Monthly total + move-in total (auto-calculated)
- Bar showing this listing vs area median
- Save cost → `PUT /api/apartments/cost/{id}`

### Unit Tests

**New file: `tests/agents/apartment/test_cost_repo.py`**
```
TestCostRepo:
  test_save_and_retrieve_cost
  test_update_existing_cost
  test_get_nonexistent_returns_none
  test_calculates_total_monthly
```

**New file: `tests/agents/apartment/test_price_analyzer.py`**
```
TestPriceAnalyzer:
  test_returns_area_median_from_comparables
  test_returns_percentile_position
  test_handles_no_comparables
```

### Integration Test

```
TestCostAPI:
  test_save_and_get_cost_via_api
  test_cost_includes_calculated_totals
```

### Done Criteria
- Cost section shows editable fields
- Save cost → persists
- Price verdict badge visible
- This listing vs median bar renders
- 6+ tests

---

## Slab 10: AI Q&A Bar

### Code Changes

**New file: `backend/agents/apartment/prompts/qa_response.py`**
- `SYSTEM_PROMPT` — "answer using only the data provided"
- `build_qa_prompt(listing, question, previous_qa, preferences) → str`

**New file: `backend/agents/apartment/repositories/qa_history_repo.py`**
- `get_history(listing_id) → list[dict]`
- `save_qa(listing_id, question, answer) → int`

**Modify: `backend/agents/apartment/routes.py`**
- Add `POST /api/apartments/lab/{listing_id}/ask` → LLM answers with context
- Add `GET /api/apartments/lab/{listing_id}/qa-history` → previous Q&A

**New file: `frontend/src/components/apartment/lab/AiQaBar.tsx`**
- Persistent bar at bottom of Lab
- Text input + send button
- Shows conversation history (user questions + AI answers)
- Streams answer via SSE
- Disabled with message when no LLM configured

### Unit Tests

**New file: `tests/agents/apartment/test_qa_history_repo.py`**
```
TestQaHistory:
  test_save_and_retrieve_qa
  test_history_returns_chronological_order
  test_history_empty_initially
```

**New file: `tests/agents/apartment/test_qa_prompt.py`**
```
TestQaPrompt:
  test_prompt_includes_listing_context
  test_prompt_includes_previous_qa
  test_prompt_includes_user_question
```

### Integration Test

```
TestQaAPI:
  test_ask_returns_answer_with_mock_llm
  test_ask_returns_error_without_llm
  test_history_returns_previous_qa
```

### Done Criteria
- Type question → AI streams answer
- History shows on reload
- Without LLM → "Connect an AI provider in Settings"
- 6+ tests

---

## Slab 11: Floor Plan Analysis

### Code Changes

**New file: `backend/agents/apartment/prompts/floor_plan.py`**
- `SYSTEM_PROMPT` — "analyze this floor plan image"
- `build_floor_plan_prompt(listing, preferences) → str`
- Asks for: livability score, room assessment, red flags, furniture fit, WFH suitability

**New file: `backend/agents/apartment/services/floor_plan_analyzer.py`**
- `analyze_floor_plan(listing_id, connection, provider_manager) → dict`
  - Gets floor plan images from `apartment_floor_plans` table
  - Calls `provider_manager.complete_with_images()`
  - Parses JSON result → saves to `apartment_floor_plans.ai_analysis`

**Modify: `backend/agents/apartment/routes.py`**
- Add `POST /api/apartments/lab/{listing_id}/analyze-floor-plan`

**New file: `frontend/src/components/apartment/lab/FloorPlanSection.tsx`**
- Shows floor plan image(s)
- "Analyze" button → triggers vision LLM
- Shows: livability score gauge, red flags, green lights, furniture fit
- Disabled if no vision-capable LLM

### Unit Tests

**New file: `tests/agents/apartment/test_floor_plan_analyzer.py`**
```
TestFloorPlanAnalyzer:
  test_analyze_returns_structured_result_with_mock_vision_llm
  test_returns_error_when_no_vision_support
  test_returns_error_when_no_floor_plan_images
  test_caches_result_in_floor_plans_table
```

### Done Criteria
- Floor plan image displays
- "Analyze" → livability score + flags stream in
- Without vision LLM → "Requires Claude or GPT-4o"
- 4+ tests

---

## Slab 12: Compare View

### Code Changes

**Modify: `backend/agents/apartment/routes.py`**
- Add `POST /api/apartments/compare` → body: `{listing_ids: [1, 2, 3]}`
  - Returns: listings with analyses + preference match scores
  - Calculates weighted score based on user's must-haves/deal-breakers

**New file: `frontend/src/components/apartment/lab/CompareView.tsx`**
- Listing picker (checkboxes, max 3)
- Side-by-side cards
- Feature comparison table (green = must-have matched, red = deal-breaker)
- Radar chart (SVG) showing scores across dimensions
- Recommendation: "Based on your priorities, A scores 87 vs B at 72"

### Unit Tests

```
TestCompareEndpoint:
  test_compare_two_listings_returns_scores
  test_compare_highlights_must_have_matches
  test_compare_flags_deal_breakers
  test_compare_rejects_more_than_three
  test_compare_handles_nonexistent_listing
```

### Done Criteria
- Select 2-3 listings → see side-by-side
- Must-haves highlighted green, deal-breakers red
- Recommendation score visible
- 5+ tests

---

## Slab 13 (Future): Overture Maps Bulk Download

### Code Changes

**New file: `backend/agents/apartment/services/overture_provider.py`**
- `download_area_data(latitude, longitude, radius_miles) → int` (POI count)
  - Downloads Overture GeoParquet for bounding box
  - Filters POIs by category
  - Loads into `apartment_local_pois` SQLite table
- `query_nearby(latitude, longitude, category, radius_km) → list[dict]`
  - Queries local POI data
  - Returns: name, category, distance, coordinates

**New table: `apartment_local_pois`**
```sql
CREATE TABLE apartment_local_pois (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    address TEXT,
    source TEXT DEFAULT 'overture',
    raw_data JSON,
    downloaded_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_pois_location ON apartment_local_pois(latitude, longitude);
CREATE INDEX idx_pois_category ON apartment_local_pois(category);
```

**Modify: Settings UI**
- "Download area data" button with location + radius input
- Shows: "30,247 places downloaded for Austin, TX (50mi)"

### Done Criteria
- Download button works
- Local queries return POIs
- Neighborhood section uses local data when available
- Deferred — build after slabs 1-12 are stable

---

## Test Summary

| Slab | Unit Tests | Integration Tests | Total |
|------|-----------|-------------------|-------|
| 1 | 13 (prefs repo + analysis repo) | 3 (routes) | 16 |
| 2 | 14 (analyzer + prompt) | 3 (routes) | 17 |
| 3 | 5 (streaming) | 1 (full stream) | 6 |
| 4 | 6 (neighborhood svc) | 2 (routes) | 8 |
| 5 | — (manual) | — | 0 |
| 6 | — (manual) | — | 0 |
| 7 | — (manual) | — | 0 |
| 8 | — (manual) | — | 0 |
| 9 | 4 (cost repo) + 3 (price) | 2 (routes) | 9 |
| 10 | 3 (qa repo) + 2 (prompt) | 3 (routes) | 8 |
| 11 | 4 (floor plan) | — | 4 |
| 12 | 5 (compare) | — | 5 |
| **Total** | **59** | **14** | **73** |

Combined with existing 767 tests → **~840 total** after all slabs.
