# Nest Lab — Architecture

## Overview

Nest Lab is a deep analysis view for shortlisted apartments. It aggregates data from multiple sources, runs it through the data processing pipeline and LLM, and presents an immersive magazine-style dashboard.

**Key constraint:** Works without LLM. Works without external APIs. Each section degrades gracefully.

---

## User Journey

```
                    ┌──────────────────┐
                    │  Nest Search Tab  │
                    │   (listing card)  │
                    └────────┬─────────┘
                             │ click "Analyze" or 🔬
                             ▼
                    ┌──────────────────┐
                    │    Nest Lab Tab   │◄──── paste URL
                    │  (listing picker) │
                    └────────┬─────────┘
                             │ select listing
                             ▼
              ┌──────────────────────────────┐
              │     Lab Analysis View         │
              │  ┌────────────────────────┐  │
              │  │ 1. Hero Photo Gallery   │  │ ← cached images (free)
              │  ├────────────────────────┤  │
              │  │ 2. Key Facts (sticky)   │  │ ← DB fields (free)
              │  ├────────────────────────┤  │
              │  │ 3. AI Overview          │  │ ← LLM (streamed)
              │  ├────────────────────────┤  │
              │  │ 4. Price Intelligence   │  │ ← DB + RentCast API
              │  ├────────────────────────┤  │
              │  │ 5. Feature Tags         │  │ ← DB + user clicks
              │  ├────────────────────────┤  │
              │  │ 6. Floor Plan Analysis  │  │ ← LLM vision (streamed)
              │  ├────────────────────────┤  │
              │  │ 7. Neighborhood         │  │ ← Walk Score + Google
              │  ├────────────────────────┤  │
              │  │ 8. AI Q&A Bar           │  │ ← LLM (streamed)
              │  └────────────────────────┘  │
              └──────────────────────────────┘
                             │
                             ▼ select multiple listings
              ┌──────────────────────────────┐
              │     Compare View              │
              │  (side-by-side + radar chart) │
              └──────────────────────────────┘
```

---

## Backend Architecture

### New Services

```
backend/agents/apartment/services/
├── lab_analyzer.py          ← Orchestrates full analysis using pipeline
├── price_analyzer.py        ← Price verdict, comps, cost breakdown
├── floor_plan_analyzer.py   ← LLM vision analysis of floor plans
└── prompts/
    ├── property_overview.py ← System + user prompt for AI overview
    ├── price_verdict.py     ← Prompt for price analysis
    ├── floor_plan.py        ← Prompt for floor plan vision analysis
    └── qa_response.py       ← Prompt for Q&A answers
```

### New Repositories

```
backend/agents/apartment/repositories/
├── feature_preferences_repo.py  ← 3-state feature preferences CRUD
├── lab_analysis_repo.py         ← Cached LLM analysis results
├── cost_repo.py                 ← Cost breakdown CRUD
└── neighborhood_repo.py         ← Neighborhood data CRUD
```

### New API Endpoints

```
# Lab analysis
GET  /api/apartments/lab/{listing_id}           ← Full lab data (cached + fresh)
GET  /api/apartments/lab/{listing_id}/stream     ← SSE stream: progress + LLM analysis
POST /api/apartments/lab/from-url               ← Paste URL → extract → analyze

# Feature preferences (global, not per-listing)
GET  /api/apartments/preferences/features        ← All feature preferences
PUT  /api/apartments/preferences/features/{name}  ← Set feature preference (neutral/must_have/deal_breaker)

# Cost breakdown (per-listing, user-editable)
GET  /api/apartments/cost/{listing_id}           ← Get cost breakdown
PUT  /api/apartments/cost/{listing_id}           ← Save/update cost entries

# Q&A
POST /api/apartments/lab/{listing_id}/ask        ← Ask a question, LLM answers with context
GET  /api/apartments/lab/{listing_id}/qa-history  ← Previous Q&A for this listing

# Compare
POST /api/apartments/compare                     ← Compare 2-3 listings, return scores
```

---

## Data Flow: Lab Analysis

```
GET /api/apartments/lab/{listing_id}

  1. GATHER (parallel where possible)
     ├── listing_repo.get_listing(id)         → listing data, images, amenities
     ├── cost_repo.get_cost(id)               → cost breakdown (if user entered)
     ├── neighborhood_repo.get(id)            → cached neighborhood data
     ├── feature_preferences_repo.get_all()   → user's must-haves/deal-breakers
     └── lab_analysis_repo.get_cached(id)     → previous LLM analysis (if fresh)

  2. CHECK CACHE
     If cached analysis exists and is < 24 hours old → return it
     If no LLM configured → return gathered data without AI sections

  3. PROCESS (pipeline)
     ├── Build context package (token-aware, priority-ordered)
     ├── Send to LLM via complete_stream()
     └── Parse structured JSON response

  4. STORE
     └── lab_analysis_repo.save(listing_id, analysis)

  5. RETURN
     └── Combined: listing + analysis + preferences + cost
```

### Streaming Flow (SSE)

```
GET /api/apartments/lab/{listing_id}/stream

  → data: {"type": "progress", "step": "gathering_data", "status": "running"}
  → data: {"type": "progress", "step": "gathering_data", "status": "complete"}
  → data: {"type": "progress", "step": "analyzing", "status": "running"}
  → data: {"type": "chunk", "text": "## Property Overview\n\n"}
  → data: {"type": "chunk", "text": "Alexan Braker Pointe is a modern..."}
  → data: {"type": "chunk", "text": "...complex in North Austin."}
  → data: {"type": "done", "full_text": "...", "metadata": {"tokens": 1200, "cost": 0.004}}
```

---

## Database Changes

### New table: `apartment_feature_preferences`
```sql
CREATE TABLE IF NOT EXISTS apartment_feature_preferences (
    id INTEGER PRIMARY KEY,
    feature_name TEXT NOT NULL,
    category TEXT NOT NULL,
    preference TEXT NOT NULL DEFAULT 'neutral',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(feature_name)
);
```

### New table: `apartment_lab_analysis`
```sql
CREATE TABLE IF NOT EXISTS apartment_lab_analysis (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES apartment_listings(id),
    analysis_type TEXT NOT NULL,  -- 'overview', 'price_verdict', 'floor_plan', 'qa'
    result JSON NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    estimated_cost REAL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(listing_id, analysis_type)
);
```

### New table: `apartment_qa_history`
```sql
CREATE TABLE IF NOT EXISTS apartment_qa_history (
    id INTEGER PRIMARY KEY,
    listing_id INTEGER NOT NULL REFERENCES apartment_listings(id),
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
```

---

## Frontend Architecture

### Component Structure

```
frontend/src/components/apartment/
├── tabs/
│   └── NestLabTab.tsx              ← Tab container (listing picker + analysis view)
├── lab/
│   ├── LabAnalysisView.tsx         ← Main scrollable analysis page
│   ├── HeroGallery.tsx             ← Full-bleed photo carousel + lightbox
│   ├── KeyFactsBar.tsx             ← Sticky price/beds/baths bar
│   ├── AiOverviewSection.tsx       ← Streamed LLM overview
│   ├── PriceIntelligence.tsx       ← Price verdict + charts + cost breakdown
│   ├── FeatureTagsSection.tsx      ← 3-state interactive tags
│   ├── FloorPlanSection.tsx        ← Floor plan image + LLM analysis
│   ├── NeighborhoodSection.tsx     ← Scores + map + nearby
│   ├── AiQaBar.tsx                 ← Persistent prompt bar + history
│   ├── CompareView.tsx             ← Side-by-side comparison
│   └── SkeletonLoader.tsx          ← Loading states per section
```

### SSE Consumption (Frontend)

```typescript
// Hook for consuming SSE streams
function useLabAnalysisStream(listingId: number) {
  const [progress, setProgress] = useState<string>("")
  const [analysisText, setAnalysisText] = useState<string>("")
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    const eventSource = new EventSource(`/api/apartments/lab/${listingId}/stream`)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "progress") setProgress(data.detail)
      if (data.type === "chunk") setAnalysisText(prev => prev + data.text)
      if (data.type === "done") { setIsComplete(true); eventSource.close() }
      if (data.type === "error") { /* show error */ eventSource.close() }
    }

    return () => eventSource.close()
  }, [listingId])

  return { progress, analysisText, isComplete }
}
```

---

## LLM Prompt Architecture

### Property Overview Prompt

```
System: You are a real estate analyst. Analyze this apartment listing
and provide a concise, honest assessment.

Context:
{listing_data_json}
{user_preferences_json}
{market_data_json}

Return JSON:
{
  "overview": "2-3 sentence summary",
  "price_verdict": "fair|below_market|overpriced",
  "price_reasoning": "Why this verdict",
  "red_flags": ["flag1", "flag2"],
  "green_lights": ["strength1", "strength2"],
  "questions_to_ask": ["question1", "question2"],
  "match_score": 85,
  "match_reasoning": "Why this score based on user preferences"
}
```

### Q&A Prompt

```
System: You are a helpful apartment hunting assistant. Answer the user's
question using ONLY the data provided. If you don't have the data, say so.

Context:
{listing_data_json}
{previous_qa_json}

User question: {question}
```

---

## Neighborhood Data — 4-Layer Strategy

```
Layer 1 (default, $0):    LLM generates neighborhood intel from training data
                          Included in the analysis prompt — no extra API call
                          Knows: restaurants, grocery, parks, schools, vibe, safety feel

Layer 2 (free API):       Walk Score API → walk/transit/bike scores
                          5,000 calls/day free tier
                          User saves Walk Score API key in Settings

Layer 3 (cheap API):      Google Distance Matrix → airport distance, commute time
                          $0.005/call, user saves Google API key in Settings
                          Triggered by: "Get more info" button

Layer 4 (on demand):      Overture Maps bulk download → live POI enrichment
                          30K+ POIs per metro area, stored in local SQLite
                          User triggers: "Download area data" in Settings
                          Monthly refresh recommended
                          Future enhancement — not in Phase 1
```

### API Key Management (Settings tab)

Add to built-in sources alongside RealtyAPI/RentCast:

| Source | Key | Used for |
|--------|-----|----------|
| RealtyAPI | `realtyapi` | Listing search (Zillow, Apartments.com) |
| RentCast | `rentcast` | Listing search (market data) |
| Walk Score | `walkscore` | Walk/transit/bike scores |
| Google Maps | `google_maps` | Distance Matrix (commute, airport) |

All stored in `settings` table under `apartment_api_keys` JSON (existing pattern).

### Neighborhood Prompt (Layer 1)

Bundled into the property overview prompt — no separate call:

```
Given the property at {address} ({latitude}, {longitude}):

1. What are the nearest grocery stores? (name, approximate distance)
2. Top-rated restaurants within walking distance?
3. Parks, playgrounds, or family-friendly places nearby?
4. Notable attractions or points of interest?
5. How walkable is this area? Transit access?
6. Any noise concerns? (highway, airport, nightlife)
7. General neighborhood character and safety feel?
8. Distance to nearest airport?

Be specific — use real place names from your knowledge.
If you're not confident about a place, say so.
```

### Walk Score Integration (Layer 2)

```python
# Simple REST call — no SDK needed
GET https://api.walkscore.com/score
  ?lat=30.4186&lon=-97.7404
  &address=10801+N+Mopac+Expy+Austin+TX
  &transit=1&bike=1
  &wsapikey={key}
  &format=json

Response: {walkscore: 72, description: "Very Walkable",
           transit: {score: 45}, bike: {score: 61}}
```

### Google Distance Matrix (Layer 3)

```python
# Airport distance
GET https://maps.googleapis.com/maps/api/distancematrix/json
  ?origins=30.4186,-97.7404
  &destinations=airport:Austin-Bergstrom+International+Airport
  &mode=driving
  &key={key}

# Commute to workplace (user sets workplace address in preferences)
GET ...&destinations={user_workplace_address}&mode=transit
```

---

## Implementation Slabs (build order)

### Slab 1: DB migration + feature preferences repo + API
- Migration v7: `apartment_feature_preferences`, `apartment_lab_analysis`, `apartment_qa_history`
- `feature_preferences_repo.py` — CRUD for 3-state preferences
- Routes: GET/PUT feature preferences
- TDD: 8-10 tests

### Slab 2: Lab analysis pipeline + overview prompt (with neighborhood in prompt)
- `lab_analyzer.py` — uses pipeline to gather data, build context, call LLM
- `prompts/property_overview.py` — includes neighborhood questions in prompt
- `lab_analysis_repo.py` — cache LLM results
- Route: GET `/lab/{listing_id}` (non-streaming first)
- LLM response includes: overview, price verdict, neighborhood intel, red flags, questions
- TDD: 6-8 tests

### Slab 3: SSE streaming endpoint
- Route: GET `/lab/{listing_id}/stream`
- Uses `format_sse_stream()` + `format_sse_progress()`
- TDD: 4-6 tests

### Slab 4: Walk Score + Google Distance Matrix integration
- `neighborhood_service.py` — Walk Score + Distance Matrix calls
- Add `walkscore` and `google_maps` to built-in sources in Settings
- Cache results in `apartment_neighborhood` table
- Route: GET `/lab/{listing_id}/neighborhood`
- Triggered by "Get more info" in frontend
- TDD: 6-8 tests

### Slab 5: Frontend — NestLabTab + listing picker
- `NestLabTab.tsx` — replaces placeholder
- Listing picker from nested listings
- Paste URL integration (reuse existing endpoint)
- Loading states

### Slab 6: Frontend — LabAnalysisView (hero gallery + key facts + AI overview)
- `LabAnalysisView.tsx` — main scrollable page
- `HeroGallery.tsx` — full-bleed carousel
- `KeyFactsBar.tsx` — sticky bar
- `AiOverviewSection.tsx` — streamed LLM text with neighborhood section

### Slab 7: Frontend — Feature tags (3-state)
- `FeatureTagsSection.tsx` — interactive tags
- Connects to feature preferences API
- Persists across listings

### Slab 8: Frontend — Neighborhood section + "Get more info"
- `NeighborhoodSection.tsx` — shows LLM intel (default)
- "Get more info" button → fetches Walk Score + Distance Matrix
- Displays: scores, airport distance, commute time

### Slab 9: Price intelligence + cost calculator
- `price_analyzer.py` — cost breakdown, verdict
- `PriceIntelligence.tsx` — charts, cost table
- Route: GET/PUT cost breakdown

### Slab 10: AI Q&A bar
- `AiQaBar.tsx` — prompt input + history
- Route: POST ask, GET history
- `prompts/qa_response.py`

### Slab 11: Floor plan analysis (if vision LLM available)
- `floor_plan_analyzer.py` — LLM vision call
- `FloorPlanSection.tsx` — display + analysis
- `prompts/floor_plan.py`

### Slab 12: Compare view
- `CompareView.tsx` — side-by-side
- Route: POST compare
- Radar chart (CSS/SVG, no heavy library)

### Slab 13 (future): Overture Maps bulk download
- Settings: "Download area data" button
- Downloads Overture GeoParquet for user's area → loads into SQLite
- `overture_provider.py` — local query for nearby POIs
- Enriches neighborhood section with live POI data

---

## Decisions

| # | Decision | Chosen | Why |
|---|----------|--------|-----|
| A1 | Analysis caching | Cache in `apartment_lab_analysis`, 24h TTL | Don't re-call LLM for same listing |
| A2 | Streaming | SSE via `EventSource` | Simpler than WebSocket, browser-native |
| A3 | Q&A storage | Separate `apartment_qa_history` table | Questions are user-generated, not analysis |
| A4 | Feature preferences | Global (not per-listing) | "I need in-unit W/D" applies everywhere |
| A5 | Compare max | 3 listings | UI constraint — more gets unusable |
| A6 | Chart library | None — CSS-only for bar charts, SVG for radar | Avoid heavy deps (recharts=500KB) |
| A7 | Section loading | Independent — each section loads separately | Fast perceived load, no blocking |
| A8 | No-LLM mode | Show all data sections, hide AI-only sections | Must work without LLM connected |
| A9 | Neighborhood default | LLM generates from training data (free) | Knows real places, zero cost, bundled in analysis |
| A10 | Neighborhood enrichment | Walk Score (free) + Google Distance (cheap), user-triggered | Only pay when user explicitly wants live data |
| A11 | Bulk POI data | Deferred to Slab 13 (Overture Maps) | Valuable but complex; LLM + Walk Score covers 90% of use cases first |
| A12 | Yelp | Rejected ($229/mo) | Cost prohibitive for free-tier app |
| A13 | API keys in Settings | Same pattern as RealtyAPI/RentCast | User self-serve, stored in `apartment_api_keys` JSON |

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM returns malformed JSON | Analysis fails | `parse_llm_json_response()` with fallback + retry once |
| LLM neighborhood data outdated | Wrong restaurant listed | Disclaimer: "Based on AI knowledge, may not reflect recent changes" |
| Floor plan not available | Section empty | Show "No floor plan available — paste URL with floor plan" |
| RentCast quota exhausted | No price comps | Show listing price only, explain "Connect API for comparisons" |
| Large gallery (50+ photos) | Slow load | Lazy loading, show first 5, "load more" |
| Budget exceeded mid-analysis | Partial results | Stream what we have, show error for remaining sections |
| Walk Score API key not set | No scores | Hide scores section, show "Connect Walk Score in Settings" |
| Google API key not set | No commute/airport | Hide distance section, show "Connect Google Maps in Settings" |

---

## Follow-ups & Future Enhancements

### Nest Intel (Premium Tier — up to $5/listing)

Cool, sophisticated UI. User explicitly opts in. Goes full-blown on all APIs.

| Feature | How | Source |
|---------|-----|--------|
| **Individual unit listings** | RealtyAPI `/apartment_details` endpoint | Shows exact prices, sqft, availability per unit (not just summary) |
| **Floor plan + unit context** | User selects specific unit → floor, facing, unit number | Enables sunlight/noise/wind analysis (meaningless without unit) |
| **Concession auto-extract** | Scrape listing URL → send to LLM: "Extract move-in specials" → auto-fill cost calculator | Saves user from manually finding "2 months free on 14-month lease" |
| **Real Walk/Transit/Bike scores** | Walk Score API (free) | Verified scores, not LLM estimates |
| **Exact airport + commute time** | Google Distance Matrix with traffic | Real driving time, not LLM approximation |
| **Detailed rent comparables** | RentCast market data API | Historical rent trends, price per sqft vs area |
| **Review mining** | Google Places reviews → LLM sentiment extraction | Themes: maintenance, noise, pests, management quality with direct quotes |
| **Floor plan vision analysis** | LLM vision on floor plan image WITH unit context | Livability score, furniture fit, WFH suitability, red flags |

### Scraping Enhancements

| Feature | How |
|---------|-----|
| **Concession scraping** | Fetch listing URL → LLM extracts: `{concession, lease_length, discount_amount}` → auto-fill cost calculator |
| **Fee scraping** | Fetch listing URL → LLM extracts: application fee, admin fee, pet deposit, parking cost → pre-fill cost fields |
| **Policy scraping** | Fetch listing URL → LLM extracts: pet policy (breeds, weight limits), subletting rules, guest policy, lease break penalty |
| **Availability scraping** | Fetch listing URL → LLM extracts: available units, move-in dates, waitlist status |
| **Photo enrichment** | Fetch listing URL → extract additional photos not in API response (interior shots, amenity photos) |

### Data Processing Enhancements

| Feature | How |
|---------|-----|
| **Unit-level comparison** | Compare specific units across properties (3A at Alexan vs 2B at Camden) |
| **Price history tracking** | Store price snapshots over time, show if rent increased/decreased |
| **Preference learning** | Track which listings user spends time on, which features they click → improve match scores |
| **Auto-suggest must-haves** | After user sets 3+ preferences, LLM suggests: "You might also want to mark X as must-have based on your pattern" |
| **Neighborhood comparison** | Compare neighborhoods side-by-side, not just listings |

### UI Enhancements

| Feature | How |
|---------|-----|
| **Nest Intel interface** | Dark/premium theme, full-screen immersive layout, animated score gauges |
| **Interactive map** | Show listing on map with POIs, Walk Score heatmap, commute radius |
| **Radar chart comparison** | SVG radar showing scores across 6 dimensions for 2-3 listings |
| **Photo lightbox** | Fullscreen gallery with swipe, zoom, photo categories (bedroom, kitchen, amenity) |
| **PDF export** | Export Lab analysis as shareable PDF for co-decision makers |

### Open Source Considerations

| Challenge | Solution |
|-----------|----------|
| Users need API keys | One Settings page, paste key, done. Clear signup links per source. |
| Free APIs (no key needed) | Overpass (POIs), Nominatim (geocoding) — use as Layer 0 for zero-friction features |
| LLM as primary data source | Layer 1 — user's own LLM key covers 90% of value (neighborhood, analysis, scraping) |
| Expensive features gated | Nest Intel tier — user opts in with spending cap, explicit cost shown before each action |
