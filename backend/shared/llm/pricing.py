"""LLM model pricing — used for cost display and budget enforcement.

Update periodically as providers change pricing.
"""

MODELS = {
    "claude": [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "speed": "Fast", "quality": "Great", "input_per_1m": 3.0, "output_per_1m": 15.0, "default": True},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "speed": "Fastest", "quality": "Good", "input_per_1m": 1.0, "output_per_1m": 5.0},
        {"id": "claude-opus-4-20250514", "name": "Claude Opus 4", "speed": "Slower", "quality": "Best", "input_per_1m": 15.0, "output_per_1m": 75.0},
    ],
    "openai": [
        {"id": "gpt-4o", "name": "GPT-4o", "speed": "Fast", "quality": "Great", "input_per_1m": 2.5, "output_per_1m": 10.0, "default": True},
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "speed": "Fastest", "quality": "Good", "input_per_1m": 0.15, "output_per_1m": 0.60},
        {"id": "gpt-4.1", "name": "GPT-4.1", "speed": "Fast", "quality": "Newest", "input_per_1m": 2.0, "output_per_1m": 8.0},
    ],
    "deepseek": [
        {"id": "deepseek-chat", "name": "DeepSeek V3", "speed": "Fast", "quality": "Great", "input_per_1m": 0.27, "output_per_1m": 1.10, "default": True},
        {"id": "deepseek-reasoner", "name": "DeepSeek R1", "speed": "Slower", "quality": "Best", "input_per_1m": 0.55, "output_per_1m": 2.19},
    ],
    "grok": [
        {"id": "grok-2", "name": "Grok 2", "speed": "Fast", "quality": "Great", "input_per_1m": 2.0, "output_per_1m": 10.0, "default": True},
    ],
    "gemini": [
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "speed": "Fastest", "quality": "Good", "input_per_1m": 0.10, "output_per_1m": 0.40, "default": True},
        {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "speed": "Fast", "quality": "Great", "input_per_1m": 1.25, "output_per_1m": 10.0},
    ],
    "openrouter": [
        {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet 4 (via OR)", "speed": "Fast", "quality": "Great", "input_per_1m": 3.0, "output_per_1m": 15.0, "default": True},
        {"id": "openai/gpt-4o", "name": "GPT-4o (via OR)", "speed": "Fast", "quality": "Great", "input_per_1m": 2.5, "output_per_1m": 10.0},
        {"id": "google/gemini-2.0-flash-001", "name": "Gemini Flash (via OR)", "speed": "Fastest", "quality": "Good", "input_per_1m": 0.10, "output_per_1m": 0.40},
        {"id": "deepseek/deepseek-chat-v3-0324", "name": "DeepSeek V3 (via OR)", "speed": "Fast", "quality": "Great", "input_per_1m": 0.27, "output_per_1m": 1.10},
        {"id": "meta-llama/llama-4-maverick", "name": "Llama 4 Maverick (via OR)", "speed": "Fast", "quality": "Great", "input_per_1m": 0.20, "output_per_1m": 0.60},
    ],
    "ollama": [
        {"id": "llama3.1", "name": "Llama 3.1 (local)", "speed": "Varies", "quality": "Good", "input_per_1m": 0, "output_per_1m": 0, "default": True},
        {"id": "mistral", "name": "Mistral (local)", "speed": "Fast", "quality": "Good", "input_per_1m": 0, "output_per_1m": 0},
    ],
    "custom": [
        {"id": "default", "name": "Custom model (set in base URL)", "speed": "Varies", "quality": "Varies", "input_per_1m": 0, "output_per_1m": 0, "default": True},
    ],
}


def get_models_for_provider(provider: str) -> list[dict]:
    return MODELS.get(provider, [])


def get_all_models() -> dict:
    return MODELS


def estimate_cost(provider: str, model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in dollars for a given number of tokens."""
    models = MODELS.get(provider, [])
    for model in models:
        if model["id"] == model_id:
            input_cost = (input_tokens / 1_000_000) * model["input_per_1m"]
            output_cost = (output_tokens / 1_000_000) * model["output_per_1m"]
            return round(input_cost + output_cost, 6)
    return 0.0


def estimate_resume_cost(provider: str, model_id: str) -> float:
    """Rough cost for one resume generation (~1500 input, ~800 output tokens)."""
    return estimate_cost(provider, model_id, 1500, 800)
