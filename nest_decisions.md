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

## Architecture — Design Patterns

| Pattern | Where | Purpose |
|---------|-------|---------|
| **Strategy** | `services/base_provider.py`, `realtyapi_search.py`, `rentcast_search.py` | Each API source is a pluggable provider with a common interface |
| **Registry** | `services/provider_registry.py` | Central list of all providers, ordered by priority |
| **Orchestrator** | `services/search_orchestrator.py` | Runs providers, handles failures, merges results |
| **Repository** | `repositories/listing_repo.py`, `preferences_repo.py` | DB access isolated from business logic |
| **Factory** | `routes.py` → `create_router()` | Agent router creation with dependency injection |
| **Coordinator** | `coordinator.py` | Multi-agent registration and lifecycle |

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
