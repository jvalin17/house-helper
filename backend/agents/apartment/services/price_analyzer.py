"""Price analysis — comparable rent context and statistics.

Provides area median, percentile ranking, and comparable listings
for a given listing. Uses data already in the DB (no API calls).
"""

from shared.app_logger import get_logger

logger = get_logger("apartment.price_analyzer")


def get_price_context(listing_id: int, listing_repo) -> dict:
    """Compute price context for a listing vs comparables in the area.

    Returns: listing price, area median, percentile, comparable count.
    """
    listing = listing_repo.get_listing(listing_id)
    if not listing or listing.get("price") is None:
        return {"error": "Listing not found or has no price"}

    listing_price = listing["price"]

    from shared.address_utils import extract_city_from_address
    city = extract_city_from_address(listing.get("address") or "")

    if not city:
        return {
            "listing_price": listing_price,
            "area_median": None,
            "percentile": None,
            "comparable_count": 0,
            "comparables": [],
        }

    # Find comparables at SQL level
    comparables = listing_repo.find_comparables(city=city, exclude_listing_id=listing_id, limit=20)
    comparable_prices = [comparable["price"] for comparable in comparables]

    if not comparable_prices:
        return {
            "listing_price": listing_price,
            "area_median": None,
            "percentile": None,
            "comparable_count": 0,
            "comparables": [],
        }

    # Calculate median
    sorted_prices = sorted(comparable_prices)
    median_index = len(sorted_prices) // 2
    if len(sorted_prices) % 2 == 0:
        area_median = (sorted_prices[median_index - 1] + sorted_prices[median_index]) / 2
    else:
        area_median = sorted_prices[median_index]

    # Calculate percentile (what % of listings cost less than this one)
    cheaper_count = sum(1 for price in comparable_prices if price < listing_price)
    percentile = round((cheaper_count / len(comparable_prices)) * 100)

    # Sort comparables by price proximity
    comparables.sort(key=lambda comparable: abs(comparable["price"] - listing_price))

    return {
        "listing_price": listing_price,
        "area_median": round(area_median, 0),
        "percentile": percentile,
        "comparable_count": len(comparables),
        "price_vs_median": round(listing_price - area_median, 0),
        "comparables": comparables[:10],
    }
