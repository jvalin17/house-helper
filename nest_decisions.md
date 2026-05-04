# NestScout — Decisions Log

All design, tech, and architecture decisions for the NestScout apartment finder agent.

---

## Design Decisions

| # | Decision | Chosen | Why | Date |
|---|----------|--------|-----|------|
| D1 | Agent name | NestScout | Bird/nest theme, distinct from Jobsmith | 2026-04-30 |
| D2 | Tab structure | 4 tabs: Nest Search, Nest Lab, Dashboard, Settings | Mirrors Jobsmith for consistency | 2026-04-30 |
| D3 | Save/unsave icon | 🪹/🪺 (empty nest / full nest) | Hearts are generic, nest theme is unique | 2026-05-01 |
| D4 | Color theme | Purple + golden/orange | Distinct from Jobsmith's blue theme | 2026-05-01 |
| D5 | Search results layout | Continuous feed (Apple-style), not grid | Better for comparing listings vertically | 2026-05-01 |
| D6 | Flip card back | Only non-repetitive info: photos, features, extra details | User complained about repeated title/price/stats | 2026-05-02 |
| D7 | Filter out 55+ communities | Auto-filter by title keywords | Not relevant to user's search | 2026-05-02 |
| D8 | Empty state text | "Ready to find your next nest" | On-brand with NestScout theme | 2026-05-02 |

## Tech Decisions

| # | Decision | Chosen | Alternatives Considered | Why | Date |
|---|----------|--------|------------------------|-----|------|
| T1 | Multi-agent architecture | Shared services (shared/) + agent-specific code (agents/apartment/) | Monolith, microservices | Reuses LLM, budget, auth without coupling agents | 2026-04-30 |
| T2 | Frontend routing | Separate pages per agent (ApartmentDashboard.tsx, JobDashboard.tsx) | Single page with agent switcher | Cleaner separation, independent tab state | 2026-04-30 |
| T3 | Database | Same SQLite file, prefixed tables (apartment_*) | Separate DB per agent | Simpler, shares settings/LLM config | 2026-04-30 |
| T4 | Primary listing API | RealtyAPI.io (Zillow data) | RentCast, Zillow direct, Apartments.com | Only API that returns photos. 250 free req/mo | 2026-05-02 |
| T5 | Secondary listing API | RentCast | Realtor.com, SimplyRETS | Good structured data (price history, market data). No images. 50 free req/mo | 2026-05-01 |
| T6 | Search architecture | Strategy pattern — ABC base class, provider adapters, orchestrator | Direct function calls per API | OCP-compliant, easy to add providers, per-provider failover | 2026-05-02 |
| T7 | API failover | Per-provider try/except in orchestrator, merge partial results | Fail-all on any error | One broken source should never kill the search | 2026-05-02 |
| T8 | List endpoint optimization | Strip parsed_data from list response, keep only images | Return full parsed_data | 420 listings × raw API response = 5.4 MB → 1.2 MB after stripping | 2026-05-02 |
| T9 | ProviderCard theming | `themeColor` prop ("blue" / "purple") on shared component | Separate components per agent | DRY — same component, different accent colors | 2026-05-01 |
| T10 | Multi-source via parameterized provider | Single `RealtyApiProvider` class with `source_key` param for Zillow/Apartments.com/Redfin/Realtor | Separate class per source | Same API key, same response format — only base URL differs | 2026-05-02 |
| T11 | Dedup matching strategy | zpid → address normalization → lat/lng proximity + price range | Address-only, manual matching | Three-tier fallback catches same property across sources even with different formatting | 2026-05-02 |
| T12 | API quota conservation | Cache search results in DB, reuse existing data instead of re-calling APIs | Always fetch live | Free tiers are limited (250+50 req/mo). Search once, browse from DB | 2026-05-02 |
| T13 | RealtyAPI response schema | Verified live: `{searchResults: [{property: {...}}]}`, NOT flat list | Guessed schema from docs | Docs were wrong/incomplete. Live test call revealed nested `property` wrapper, `media.allPropertyPhotos`, `minPrice` instead of `price`, `price` can be dict `{value, changedDate}` | 2026-05-02 |
| T14 | Unified LLM base class | Single `LLMProviderBase` ABC with `supports_vision`/`supports_streaming` properties | 3 separate Protocols (LLMProvider, VisionCapable, StreamCapable) | Eliminates `hasattr()` checks, every provider gets streaming via fallback, capabilities discoverable via properties | 2026-05-03 |
| T15 | Token counting | Pythonic UTF-8 bytes/4 heuristic + PNG/JPEG header parsing for images | `anthropic.count_tokens()`, `tiktoken` | Zero API dependency, works across all providers, ±15% accurate for English | 2026-05-03 |
| T16 | SSE streaming | `format_sse_stream()` + `format_sse_progress()` helpers, `StreamingResponse` | WebSocket, polling | SSE is simpler, one-directional (server→client), native browser EventSource support | 2026-05-03 |
| T17 | Data processing pipeline | `PipelineContext` + `run_pipeline()` with per-step error handling | Ad-hoc function chains | Reusable across agents (apartment analysis, resume generation), fault-tolerant, composable | 2026-05-03 |
| T18 | Provider manager rename | `LazyLLMProvider` → `LLMProviderManager` | Keep old name | Name should describe what it does: manages lifecycle, config, budget, logging | 2026-05-03 |
| T19 | All providers stream | Streaming on Claude, OpenAI, Ollama, HuggingFace + base class fallback | Only Claude + OpenAI | Building for multi-agent future (travel agent, etc.) — every provider must support every capability | 2026-05-03 |
| T20 | TokenRepository to shared/ | Moved from `agents/job/` to `shared/repositories/` | Keep in job agent | Budget enforcement is cross-agent (NestScout, Jobsmith, future agents share one budget) | 2026-05-03 |
| T21 | Neighborhood data (default) | LLM generates from training data in analysis prompt | Google Places API, Yelp, bulk download | Zero extra cost — LLM already knows restaurants/grocery/parks near any US address. Not real-time but good enough for 90% of users | 2026-05-03 |
| T22 | Walk/Transit/Bike scores | Walk Score API (5K/day free) | LLM estimation, Google, calculate from OSM | Industry-standard scores, free tier, simple REST call | 2026-05-03 |
| T23 | Airport + commute distance | Google Distance Matrix API ($0.005/call) | Manual Google Maps lookup | Accurate drive/transit time, user saves Google API key in Settings | 2026-05-03 |
| T24 | Live enrichment (on demand) | Overture Maps bulk download into SQLite | Google Places per-call, Yelp ($229/mo) | Zero API cost, 30K+ POIs per metro, user triggers download for their area. Future enhancement, not Phase 1 | 2026-05-03 |
| T25 | Yelp API | Rejected | $229/mo after 30-day trial | Prohibitive cost for a free-tier app. Google Places is cheaper, Overture is free | 2026-05-03 |
| T26 | Apple Maps API | Deferred | Generous free tier (25K/day) but no ratings, no reviews, no photos | Same data quality as Overture but requires API calls. May use for map tiles in future | 2026-05-03 |
| T27 | Neighborhood data layers | 4-layer strategy: LLM (default) → Walk Score (free) → Google Distance (cheap) → Overture bulk (on demand) | Single API approach | Each layer adds value independently. User pays only for what they enable. Works fully with just LLM. | 2026-05-03 |
| T28 | Three-tier info architecture | Search Cards (free) → Nest Lab (LLM only) → Nest Intel (premium, up to $5/listing) | Single view with everything | No repetition across tiers. Each tier adds depth. 90% of users stop at Lab. Intel is explicit opt-in. | 2026-05-03 |
| T29 | Premium tier name | "Nest Intel" | "Deep Dive", "Full Intel", "Premium Insights" | On-brand with NestScout, spy/intelligence theme, sounds cool | 2026-05-03 |
| T30 | Nest Intel scope | Individual unit listings, floor plan + unit context (floor/facing), Walk Score real data, Google Distance exact, detailed rent comps, all APIs maxed out | Partial enrichment | User explicitly opts in with spending cap ($5). Gets everything the APIs can provide. | 2026-05-03 |
| T31 | Floor plan analysis requires unit | Deferred to Nest Intel tier — need unit number/floor to analyze sunlight, road noise, wind, facing | Analyze without unit context | Generic floor plan analysis without unit context gives incomplete insights | 2026-05-03 |
| T32 | Open source API strategy | LLM as primary data source (user's own key), free APIs (Overpass/Nominatim) no key needed, external APIs only for Nest Intel | Bundle API keys | Can't redistribute third-party keys. Setup is one Settings page. | 2026-05-03 |
| T33 | Text summarization service | `shared/text_summarizer.py` — truncate, extract key points, condense paragraphs to bullets | Inline truncation | Universal utility: compare cards, Q&A previews, notifications, any agent that needs concise text. Comparison service (agent-specific) uses this. | 2026-05-04 |

## Architecture — Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Strategy** | `services/base_provider.py`, `realtyapi_search.py`, `rentcast_search.py` | Each API source is a pluggable provider with a common interface |
| **Registry** | `services/provider_registry.py` | Central list of all providers, ordered by priority |
| **Orchestrator** | `services/search_orchestrator.py` | Runs providers, handles failures, merges results |
| **Repository** | `repositories/listing_repo.py`, `preferences_repo.py` | DB access isolated from business logic |
| **Factory** | `routes.py` → `create_router()` | Agent router creation with dependency injection |
| **Coordinator** | `coordinator.py` | Multi-agent registration and lifecycle |
| **Template Method** | `LLMProviderBase` | `complete_stream()` default calls `complete()` — subclasses override for native streaming |
| **Pipeline** | `shared/pipeline.py` | gather → process → build context → LLM → restructure → present |
| **Manager** | `shared/llm/provider_manager.py` | Wraps any provider with budget, logging, config hot-swap |

## Requirement Decisions

| # | Requirement | Status | Notes |
|---|------------|--------|-------|
| R1 | Structured search filters (city, zip, beds, amenities, max rent) | Done | Airbnb-style pills and multi-select |
| R2 | Natural language search | Partial | Input field exists, backend doesn't use it yet (needs LLM) |
| R3 | Image display on listing cards | Done | RealtyAPI provides 15-47 photos per listing |
| R4 | Amenities/features on cards | Partial | RealtyAPI search doesn't return amenities — needs `/apartment_details` endpoint |
| R5 | Distance to nearest airport | Pending | Needs Google Maps API integration |
| R6 | Auto-search (daily top 5 notifications) | Pending | Phase 6 |
| R7 | Paste URL extraction | Done | Backend extracts title, price, beds, baths, amenities from HTML |
| R8 | Deduplication across sources | Done | Data processor merges by zpid/address/proximity. Enriches: most images, most amenities, longest title |
| R9 | Cost calculator | Pending | Phase 3 |
| R10 | Neighborhood intelligence | Pending | Phase 4 — Google Places integration |

## Backend Tech

| Component | Technology | Notes |
|-----------|-----------|-------|
| Framework | FastAPI | Sync routes (not async) |
| Database | SQLite + WAL mode | `~/.panini/panini.db`, PRAGMA user_version migrations |
| HTTP client | httpx | For external API calls (RealtyAPI, RentCast) |
| Logging | `shared/app_logger.py` | Structured logging per module |
| URL fetching | `shared/url_fetcher.py` | SSRF protection, timeout handling |
| HTML extraction | `agents/apartment/services/url_extractor.py` | BeautifulSoup-based |
| LLM | `shared/llm/` LazyLLMProvider | 9 providers, budget enforcement |

## Frontend Tech

| Component | Technology | Notes |
|-----------|-----------|-------|
| Framework | React 19 + TypeScript | Vite bundler |
| Styling | Tailwind 4 + shadcn/ui | Purple theme for NestScout |
| API client | `src/api/client.ts` | Zero raw fetch() in components |
| Notifications | Sonner toasts | Success/error/info |
| State | useState (local) | No global state manager needed yet |
| Tabs | CSS hidden pattern | All tabs stay mounted, switch via display |

## API Response Schemas (Verified from Live Calls)

### RealtyAPI `/search/byaddress` (2026-05-02)
```
Response: {searchResults: [{property: {...}, resultType: "propertyGroup"}], resultsCount: {...}, pagesInfo: {...}}
Property: {zpid, title, address: {streetAddress, city, state, zipcode}, location: {lat, lng},
           media: {allPropertyPhotos: {medium: [urls], highResolution: [urls]}},
           minPrice, maxPrice, unitsGroup: [{bedrooms, minPrice}]}
Notes: price can be dict {value, changedDate} on some listings. No amenities in search — need /apartment_details.
```

### RentCast `/v1/listings/rental/long-term` (2026-05-01)
```
Response: [{formattedAddress, price, bedrooms, bathrooms, squareFootage, propertyType,
            latitude, longitude, daysOnMarket, listedDate, status, ...}]
Notes: NO images. NO amenities (features only on separate /v1/properties endpoint).
```

## Key Prompts / User Feedback

| Feedback | Action Taken |
|----------|-------------|
| "That looks like a school project" | Redesigned to Apple-style continuous feed with modern aesthetics |
| "Heart is very generic" | Changed to 🪹/🪺 nest emoji |
| "Not red.. purple and golden" | Changed theme from rose to purple + orange accent |
| "Search should be after refine" | Moved ⚡Search button below refine section |
| "I still don't see images" | Discovered RentCast has no images, integrated RealtyAPI |
| "If one API fails, we should have other API" | Built Strategy pattern with per-provider failover |
| "Why is search only for RealtyAPI?" | Refactored to common search interface with provider adapters |
| "Filter out 55+ community" | Added age-restricted keyword filter |
| "Distance to airport for every property" | Saved as pending requirement (R5) |
| "We should have common search class and strategy pattern" | Refactored to ABC + provider adapters + orchestrator + registry |
| "Put tech decisions somewhere" | Created `nest_decisions.md` — this file |
| "Button stays grayed out" | Root cause: 5.4 MB JSON response froze browser. Fixed by stripping `parsed_data` from list endpoint |
| "We should have data process engine" | Built `data_processor.py` — dedup by zpid/address/proximity, merge images+amenities |
| "Limited API usage, store and reuse data" | Decision T12: cache results in DB, browse from existing data instead of re-calling APIs |
| "What data do we get from RealtyAPI? Only Zillow?" | Documented multi-source support (Zillow, Apartments.com, Redfin, Realtor.com) — all same key |

## File Structure

```
backend/agents/apartment/
├── routes.py                          # API endpoints
├── models.py                          # Pydantic models
├── repositories/
│   ├── listing_repo.py                # Listing CRUD
│   └── preferences_repo.py           # Preferences + custom sources
└── services/
    ├── base_provider.py               # ABC for search providers
    ├── search_orchestrator.py         # Runs providers, merges results
    ├── provider_registry.py           # Lists all registered providers
    ├── realtyapi_search.py            # RealtyAPI adapter + RealtyApiProvider
    ├── rentcast_search.py             # RentCast adapter + RentCastProvider
    └── url_extractor.py               # HTML → listing data
```
