"""Shared address utilities — extract city, normalize addresses."""


def extract_city_from_address(address: str) -> str:
    """Extract city from a comma-separated address string.

    '10801 N Mopac Expy, Austin, TX, 78759' → 'Austin'
    """
    if not address:
        return ""
    parts = [part.strip() for part in address.split(",")]
    return parts[1] if len(parts) >= 2 else ""
