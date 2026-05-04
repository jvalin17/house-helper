# Nest Lab — Deep Property Analysis & Intelligence

## Problem Statement

When apartment hunting, you find a listing that looks promising — but how do you *actually* evaluate it? You'd need to:
- Research rent fairness (is $1,445 good for a 1BR in this area?)
- Analyze the floor plan (will my queen bed fit? is the kitchen usable?)
- Check the neighborhood (walkability, transit, safety, noise)
- Read reviews (what do actual residents say about maintenance response times?)
- Calculate total cost (rent + fees + parking + pet deposit + utilities)
- Compare with alternatives side-by-side

Today this takes hours across 10+ tabs. Nest Lab does it in one immersive view, powered by AI.

## Core Intent

**Nest Lab is an intelligence dashboard for shortlisted apartments.** When a user nests (shortlists) a property or pastes a URL, Nest Lab aggregates data from all available sources, sends it through LLM analysis, and presents an immersive, magazine-style deep dive — price fairness, floor plan analysis, neighborhood intelligence, resident sentiment, and a personalized recommendation score.

The user's feedback (must-have / nice-to-have / deal-breaker tags on features) trains the system to rank future listings better.

---

## Entry Points

| How user enters Lab | What happens |
|---|---|
| Click "Analyze" on a nested listing | Load all data for that listing, run LLM analysis |
| Paste a URL in Lab | Fetch page → extract data → save as listing → run analysis |
| User prompt/question about a listing | LLM answers using all aggregated data as context |

---

## Primary User Flow

```
1. User nests a listing from search (or pastes URL in Lab)
2. Lab opens with hero photo gallery + key facts bar
3. System aggregates: listing data + price comps + neighborhood scores + reviews
4. LLM receives full data package → generates:
   - Property overview (2-3 sentence summary)
   - Price verdict ("Fair / Overpriced / Great deal" with reasoning)
   - Red flags and green lights
   - Questions to ask on tour
5. User scrolls through immersive sections
6. User tags features: must-have / nice-to-have / deal-breaker
7. User asks follow-up questions in a prompt bar
8. User compares 2-3 shortlisted properties side-by-side
```

---

## Sections (scroll order)

### 1. Hero Gallery
- Full-bleed photo carousel (edge-to-edge, no margins)
- Photo count badge, fullscreen lightbox on click
- Virtual tour link if available (from listing data)
- **Priority:** must

### 2. Key Facts Bar (sticky)
- Price, beds, baths, sqft, address — always visible while scrolling
- Nest/unnest button
- "Ask AI" quick prompt button
- **Priority:** must

### 3. AI Overview
- 2-3 sentence LLM-generated summary of the property
- Highlight what makes it unique vs. typical listings in the area
- **Priority:** must

### 4. Price Intelligence
- **Rent verdict**: "Fair" / "Below market" / "Overpriced" with confidence
- **Price comparison chart**: this listing vs. area median (bar chart or position on bell curve)
- **Price trend graph**: area rent over last 12 months (line chart)
- **Total cost breakdown**: rent + parking + pet fee + utilities estimate + renter's insurance = monthly total
- **Move-in cost**: first month + deposit + application fee + admin fee = one-time total
- **Net effective rent**: if concessions (e.g., "2 months free on 14-month lease"), show true monthly cost
- Data sources: RentCast market data, RealtyAPI listing data, user-entered costs
- **Priority:** must (verdict + comparison), should (trend graph, total cost)

### 5. Floor Plan Analysis
- Display floor plan image(s) if available (from listing URL extraction or uploaded)
- **LLM analysis of floor plan** (send image to vision-capable LLM):
  - Livability score (0-100)
  - Room-by-room assessment
  - Red flags: bedroom too small for queen bed, kitchen has no window, bathroom only accessible through bedroom
  - Green lights: good natural light, efficient layout, separate bedroom entrance
  - Furniture fit check: will standard furniture fit?
  - Work-from-home suitability assessment
  - Wasted space percentage
- **"Questions to ask"** generated from floor plan weaknesses
- **Priority:** should (depends on floor plan availability and vision LLM)

### 6. Feature Tags (User Feedback)
- All extracted features displayed as interactive tags
- User taps a tag → cycles through 3 states:
  - **Neutral** (gray, default)
  - **Must have** (purple, solid)
  - **Deal breaker** (red, with ✗)
- No thumbs, no stars, no sliders — just tap to cycle
- Preferences persist across all listings (if user marks "In-unit W/D" as must-have, it's must-have everywhere)
- Matched features (that align with user's must-haves) highlighted on search cards too
- Categories: Unit features, Building amenities, Neighborhood, Policies, Lease terms
- **Priority:** must

### 7. Neighborhood Intelligence
- **Scores**: Walk Score, Transit Score, Bike Score (Walk Score API or estimated)
- **Commute time**: to user's workplace (user sets in preferences)
- **Nearby amenities**: grocery, restaurants, gyms, parks — with distance
- **Safety grade**: if available from data
- **"What locals say"**: mined from Google Reviews of the property + Reddit mentions
- **Noise assessment**: LLM inference from reviews + location (near highway? airport? bars?)
- **Map**: embedded or linked showing the property + nearby POIs
- **Priority:** should (scores), could (reviews mining, commute)

### 8. Resident Sentiment
- LLM mines Google Reviews, Yelp, Reddit for the property/management company
- Extracts themes: maintenance response, noise, management quality, pest issues, parking
- Shows as sentiment cards: "Maintenance: Generally responsive (7 positive, 2 negative mentions)"
- Highlights direct quotes that are most useful
- **Priority:** could (requires review data access)

### 9. AI Q&A Bar
- Persistent prompt bar at bottom of Lab
- User asks anything: "Is this good for a dog owner?" / "How far is the nearest Indian grocery?"
- LLM answers using all aggregated data as context
- Previous Q&A history shown as conversation
- User's questions also serve as preference hints (if they ask about dog parks, system learns they have a dog)
- **Priority:** must

### 10. Compare View
- Select 2-3 nested listings → side-by-side comparison
- Visual: radar chart showing each property's scores across dimensions
- Table: feature-by-feature comparison with color coding (green = matches must-have, red = deal breaker)
- **Recommendation score**: weighted by user's feature preferences
- "Based on your priorities, Property A scores 87/100 vs. Property B at 72/100"
- **Priority:** should

---

## LLM Data Package

When analyzing a listing, the system sends this context to the LLM:

```
Property Data:
- Title, address, price, beds/baths/sqft
- All extracted features and amenities
- All photos (if vision model) or photo descriptions
- Floor plan images (if available)
- Source URL

Market Context:
- Area median rent for same bed count
- Comparable listings nearby (top 5)
- Price trend direction (up/down/stable)

Neighborhood:
- Walk/Transit/Bike scores
- Nearby amenities (grocery, transit, parks)
- School ratings if applicable

User Context:
- User's feature preferences (must-haves, deal-breakers)
- User's search criteria (location preference, budget)
- Previous questions/prompts (as hints)

Request:
- Generate overview, price verdict, red flags, green lights
- Generate questions to ask on tour
- If floor plan provided: analyze livability
```

---

## User Preference System

### Three-State Tags
```
Tap 1: Neutral (gray)  → Must have (purple, ✓)
Tap 2: Must have        → Deal breaker (red, ✗)
Tap 3: Deal breaker     → Neutral (gray, reset)
```

### Preference Categories
| Category | Example features |
|---|---|
| Unit | In-unit W/D, Dishwasher, Balcony, Walk-in closet, Hardwood floors |
| Building | Pool, Gym, Doorman, Elevator, Rooftop, Package room, EV charging |
| Neighborhood | Walkable, Near transit, Quiet, Safe, Near grocery, Near parks |
| Policies | Pet friendly, Short lease option, Subletting allowed, No breed restrictions |
| Budget | Under $X, Fees included, No application fee, Utilities included |

### How preferences feed back
- Search results: matched must-haves highlighted purple on cards
- Lab analysis: LLM mentions which must-haves are met/missing
- Compare view: scoring weighted by preference importance
- Future auto-search: preferences used as filters

---

## Paste URL Flow

```
1. User pastes URL in Lab prompt bar or dedicated paste area
2. System fetches page (existing url_fetcher.py)
3. Extracts: title, price, beds, baths, sqft, address, amenities, photos, floor plan images
4. Saves as new listing
5. Immediately opens in Lab for full analysis
6. If LLM is connected: runs full AI analysis
7. If no LLM: shows extracted data in immersive view without AI sections
```

---

## Data Sources Per Section

| Section | Data Source | API Cost |
|---|---|---|
| Hero Gallery | listing.images (already in DB from RealtyAPI) | Free (cached) |
| Key Facts | listing table fields | Free (DB) |
| AI Overview | LLM (listing data as context) | LLM tokens |
| Price Intelligence | RentCast market data API, listing data | RentCast API call |
| Floor Plan | listing URL extraction, LLM vision | LLM tokens (vision) |
| Feature Tags | listing.amenities + user preferences table | Free (DB) |
| Neighborhood | Walk Score API (free tier), Google Places API | Walk Score + Google |
| Resident Sentiment | Google Places reviews API, LLM analysis | Google API + LLM |
| AI Q&A | LLM with all data as context | LLM tokens |
| Compare View | All above data, aggregated | Free (computed) |

---

## Non-Functional Requirements

| Requirement | Target |
|---|---|
| Lab load time (cached data) | < 1 second |
| Lab load time (fresh analysis with LLM) | < 10 seconds, with streaming |
| LLM analysis cost per listing | < $0.05 (budget enforcement via existing system) |
| Works without LLM | Yes — shows all data sections except AI Overview, Floor Plan Analysis, Resident Sentiment, AI Q&A |
| Works without external APIs | Yes — shows cached listing data, features, photos. No price comps or neighborhood scores. |
| Photo gallery performance | Lazy loading, max 50 photos displayed |

---

## What Nest Lab Should NOT Do

- Replace visiting the apartment in person
- Provide legal advice about leases
- Auto-apply or contact landlords (that's a separate feature)
- Store user's financial information
- Make the final decision for the user — it provides intelligence, user decides

---

## Database Changes Needed

Existing tables already support most of this:
- `apartment_floor_plans` — floor plan images + AI analysis ✓
- `apartment_neighborhood` — scores, distances, reviews ✓
- `apartment_cost` — cost breakdown ✓
- `apartment_notes` — visit notes, status ✓

New table needed:
```sql
CREATE TABLE apartment_feature_preferences (
    id INTEGER PRIMARY KEY,
    feature_name TEXT NOT NULL,
    category TEXT NOT NULL,
    preference TEXT NOT NULL DEFAULT 'neutral',  -- 'neutral', 'must_have', 'deal_breaker'
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(feature_name)
);
```

---

## Implementation Phases

### Phase 1: Core Lab View (build first)
- Hero gallery + key facts bar
- Feature tags with 3-state preferences
- Paste URL integration
- AI Overview (LLM summary if connected)

### Phase 2: Price Intelligence
- Price verdict (LLM-powered)
- Cost breakdown calculator
- Comparable rents (RentCast data)
- Price trend chart

### Phase 3: Floor Plan Analysis
- Floor plan image display
- LLM vision analysis (livability score, red flags, furniture fit)
- Questions to ask generator

### Phase 4: Neighborhood & Sentiment
- Walk/Transit/Bike scores
- Nearby amenities map
- Review mining (Google Reviews → LLM sentiment extraction)
- Commute calculator

### Phase 5: Compare & Recommend
- Side-by-side comparison view
- Radar charts
- Weighted recommendation score based on preferences

---

## UI/UX Direction

- **Magazine-style single scroll** (not tabs within Lab)
- **Full-bleed photos** — edge-to-edge, no card borders on gallery
- **Purple accent** — consistent with NestScout theme
- **Generous whitespace** — premium feel, not cramped
- **Sticky key facts** — price/address always visible
- **Section anchors** — smooth scroll navigation between sections
- **Skeleton loaders** — show layout while LLM/API data loads
- **Graceful degradation** — every section works with partial data
