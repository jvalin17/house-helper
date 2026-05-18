"""Built-in service registry — single source of truth for all API sources.

Categories:
  - ai_provider      → AI providers (shown in agent settings for model selection)
  - shared_source    → Data sources used by multiple agents (Google Maps, Walk Score)
  - nestscout_source → NestScout-specific sources (RealtyAPI, RentCast)
  - jobsmith_source  → Jobsmith-specific sources (RapidAPI/JSearch, Adzuna)

To add a new source: add an entry to BUILT_IN_SERVICES below.
sync_built_in_services() runs on every startup, adding missing entries.
"""

BUILT_IN_SERVICES = [
    # AI Providers — no quota tracking (cost-based via token_budget)
    {"service_name": "claude", "category": "ai_provider", "display_name": "Claude (Anthropic)", "signup_url": "https://console.anthropic.com", "description": "Sonnet 4, Opus 4, Haiku — vision + streaming", "free_tier": "$5 free credit", "unlocks": "AI analysis, resume generation, property Q&A", "quota_limit": None, "quota_period": None},
    {"service_name": "openai", "category": "ai_provider", "display_name": "OpenAI", "signup_url": "https://platform.openai.com/api-keys", "description": "GPT-4o, GPT-4.1 — vision + streaming", "free_tier": "Pay-as-you-go", "unlocks": "AI analysis, resume generation, property Q&A", "quota_limit": None, "quota_period": None},
    {"service_name": "deepseek", "category": "ai_provider", "display_name": "DeepSeek", "signup_url": "https://platform.deepseek.com", "description": "V3/R1 — fast + cheap", "free_tier": "$5 free credit", "unlocks": "AI analysis, resume generation (fast + cheap)", "quota_limit": None, "quota_period": None},
    {"service_name": "grok", "category": "ai_provider", "display_name": "Grok (xAI)", "signup_url": "https://console.x.ai", "description": "Grok 2", "free_tier": "$25/mo free credit", "unlocks": "AI analysis, resume generation", "quota_limit": None, "quota_period": None},
    {"service_name": "gemini", "category": "ai_provider", "display_name": "Gemini (Google)", "signup_url": "https://aistudio.google.com/apikey", "description": "Gemini 2.0 Flash/2.5 Pro", "free_tier": "Free tier available", "unlocks": "AI analysis, resume generation", "quota_limit": None, "quota_period": None},
    {"service_name": "openrouter", "category": "ai_provider", "display_name": "OpenRouter", "signup_url": "https://openrouter.ai/keys", "description": "Multi-provider gateway", "free_tier": "$1 free credit", "unlocks": "AI analysis via multiple providers", "quota_limit": None, "quota_period": None},
    {"service_name": "ollama", "category": "ai_provider", "display_name": "Ollama (Local)", "signup_url": None, "description": "Local models — no API key needed", "free_tier": "Free — runs locally", "unlocks": "AI analysis offline, no API costs", "quota_limit": None, "quota_period": None},

    # Shared sources (used by multiple agents)
    {"service_name": "google_maps", "category": "shared_source", "display_name": "Google Maps", "signup_url": "https://console.cloud.google.com/apis", "description": "$200/mo credit — distance, commute, places", "free_tier": "$200/mo free credit", "unlocks": "Commute times, neighborhood places", "quota_limit": None, "quota_period": None},
    {"service_name": "walkscore", "category": "shared_source", "display_name": "Walk Score", "signup_url": "https://www.walkscore.com/professional/api.php", "description": "5K/day — walk/transit/bike scores", "free_tier": "5K requests/day", "unlocks": "Walk, transit, and bike scores", "quota_limit": 5000, "quota_period": "day"},

    # NestScout sources
    {"service_name": "realtyapi", "category": "nestscout_source", "display_name": "RealtyAPI", "signup_url": "https://www.realtyapi.io", "description": "250 req/mo — apartment images + listings", "free_tier": "250 req/mo", "unlocks": "Apartment search with photos (Zillow, Apartments.com)", "quota_limit": 250, "quota_period": "month"},
    {"service_name": "rentcast", "category": "nestscout_source", "display_name": "RentCast", "signup_url": "https://www.rentcast.io/api", "description": "50 req/mo — market data", "free_tier": "50 req/mo", "unlocks": "Market data and rental comparisons", "quota_limit": 50, "quota_period": "month"},

    # Jobsmith sources
    {"service_name": "rapidapi", "category": "jobsmith_source", "display_name": "RapidAPI (JSearch)", "signup_url": "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch", "description": "500 req/mo — LinkedIn, Indeed, Glassdoor", "free_tier": "500 req/mo", "unlocks": "Job search across LinkedIn, Indeed, Glassdoor", "quota_limit": 500, "quota_period": "month"},
    {"service_name": "adzuna_app_id", "category": "jobsmith_source", "display_name": "Adzuna App ID", "signup_url": "https://developer.adzuna.com", "description": "Your Adzuna application ID", "free_tier": "Free with key", "unlocks": "Adzuna job search (paired with app key)", "quota_limit": None, "quota_period": None},
    {"service_name": "adzuna_app_key", "category": "jobsmith_source", "display_name": "Adzuna App Key", "signup_url": "https://developer.adzuna.com", "description": "250 req/day — job search API key", "free_tier": "250 req/day", "unlocks": "Adzuna job search results", "quota_limit": 250, "quota_period": "day"},
]


def sync_built_in_services(connection) -> int:
    """Ensure all built-in services exist in api_credentials table.

    Called on every startup. Creates missing rows, updates categories
    for existing rows. Never overwrites existing keys.
    """
    added_count = 0
    for service in BUILT_IN_SERVICES:
        existing = connection.execute(
            "SELECT id, category FROM api_credentials WHERE service_name = ?",
            (service["service_name"],),
        ).fetchone()
        if not existing:
            connection.execute(
                "INSERT INTO api_credentials (service_name, category, display_name, signup_url, description) "
                "VALUES (?, ?, ?, ?, ?)",
                (service["service_name"], service["category"], service["display_name"],
                 service.get("signup_url"), service.get("description")),
            )
            added_count += 1
        elif existing["category"] != service["category"]:
            # Update category if it changed (e.g., data_source → nestscout_source)
            connection.execute(
                "UPDATE api_credentials SET category = ?, display_name = ?, description = ? WHERE service_name = ?",
                (service["category"], service["display_name"], service.get("description"), service["service_name"]),
            )

    # Clean up obsolete entries
    for obsolete_name in ("adzuna_id", "adzuna_key", "adzuna", "jooble"):
        connection.execute(
            "DELETE FROM api_credentials WHERE service_name = ? AND api_key = ''",
            (obsolete_name,),
        )

    connection.commit()
    return added_count
