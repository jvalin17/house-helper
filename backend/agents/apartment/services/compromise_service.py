"""CompromiseService — calculates preference trade-offs against budget.

Uses learning_machine module functions directly (not a wrapper class).
Real API: get_learned_weights(connection, profile_id, agent) -> dict[str, float]
          _count_meaningful_interactions(connection, profile_id, agent) -> int
"""

import json
import sqlite3

from shared.app_logger import get_logger
from shared.ranking.learning_machine import (
    get_learned_weights,
    _count_meaningful_interactions,
)
from agents.apartment.repositories.listing_repo import ApartmentListingRepository
from agents.apartment.repositories.preferences_repo import ApartmentPreferencesRepository

logger = get_logger("apartment.compromise_service")

MINIMUM_INTERACTIONS_FOR_PROFILE = 10
MAXIMUM_TOP_PREFERENCES = 10
AGENT_NAME = "apartment"


class CompromiseService:
    """Calculates preference trade-offs against budget.

    Uses learning_machine module functions directly (not a wrapper class).
    """

    def __init__(
        self,
        connection: sqlite3.Connection,
        listing_repo: ApartmentListingRepository,
        preferences_repo: ApartmentPreferencesRepository,
    ):
        self._connection = connection
        self._listing_repo = listing_repo
        self._preferences_repo = preferences_repo

    def get_profile(self, profile_id: int | None = None) -> dict:
        """Build search profile from learned weights + budget.

        Steps:
        1. Count interactions — if < 10, return not ready
        2. Read learned term weights
        3. Read max_price from preferences
        4. For each top term: query avg rent of matching listings
        5. Classify each as achievable/stretch
        6. Generate summary via string formatting (no LLM)
        """
        interaction_count = _count_meaningful_interactions(
            self._connection, profile_id, AGENT_NAME
        )

        if interaction_count < MINIMUM_INTERACTIONS_FOR_PROFILE:
            return {"ready": False}

        term_weights = get_learned_weights(
            self._connection, profile_id, AGENT_NAME
        )

        if not term_weights:
            return {"ready": False}

        # Read budget from preferences
        preferences_data = self._preferences_repo.get_preferences()
        maximum_price = preferences_data.get("max_price")

        # Get top positive terms sorted by weight descending
        sorted_terms = sorted(
            [(term, weight) for term, weight in term_weights.items() if weight > 0],
            key=lambda item: item[1],
            reverse=True,
        )[:MAXIMUM_TOP_PREFERENCES]

        # Get all saved listings for matching
        saved_listings = self._listing_repo.list_listings(saved_only=True)

        # For each preference term, compute average rent of matching listings
        preference_entries = []
        total_weighted_rent = 0.0
        total_weighted_count = 0

        for term, weight in sorted_terms:
            matching_listing_prices = self._find_matching_listing_prices(
                saved_listings, term
            )
            average_rent = (
                round(sum(matching_listing_prices) / len(matching_listing_prices))
                if matching_listing_prices
                else 0
            )
            is_achievable = (
                average_rent <= maximum_price
                if maximum_price and average_rent > 0
                else True
            )
            preference_entries.append({
                "term": term,
                "weight": round(weight, 2),
                "achievable": is_achievable,
                "average_rent": average_rent,
            })

            if matching_listing_prices:
                total_weighted_rent += sum(matching_listing_prices)
                total_weighted_count += len(matching_listing_prices)

        # Compute wishlist average
        wishlist_average = (
            round(total_weighted_rent / total_weighted_count)
            if total_weighted_count > 0
            else 0
        )

        # Generate summary string (no LLM)
        if maximum_price and wishlist_average > 0:
            summary = (
                f"Your wishlist averages ${wishlist_average:,}/mo. "
                f"Your budget is ${maximum_price:,}/mo."
            )
        elif maximum_price:
            summary = f"Your budget is ${maximum_price:,}/mo."
        else:
            summary = "Set a budget in preferences to see how your wishlist compares."

        return {
            "ready": True,
            "interaction_count": interaction_count,
            "preferences": preference_entries,
            "budget": maximum_price,
            "wishlist_average": wishlist_average,
            "summary": summary,
        }

    def explore_compromises(
        self,
        enabled: list[str],
        disabled: list[str],
    ) -> dict:
        """Toggle preferences, return matching count + suggestions.

        Steps:
        1. Get all saved listings
        2. Filter by enabled preferences (match ANY enabled term)
        3. Apply budget filter
        4. Count matches, compute avg rent
        5. For each disabled pref: calculate how many MORE listings match
        6. Find best suggestion under budget
        7. Generate positive message (string formatting)
        """
        saved_listings = self._listing_repo.list_listings(saved_only=True)
        preferences_data = self._preferences_repo.get_preferences()
        maximum_price = preferences_data.get("max_price")

        # Filter listings matching ANY enabled preference term
        if enabled:
            matching_listings = [
                listing for listing in saved_listings
                if self._listing_matches_any_term(listing, enabled)
            ]
        else:
            matching_listings = list(saved_listings)

        # Apply budget filter
        budget_filtered_listings = [
            listing for listing in matching_listings
            if self._listing_within_budget(listing, maximum_price)
        ]

        matching_count = len(budget_filtered_listings)
        average_rent = (
            round(
                sum(listing["price"] for listing in budget_filtered_listings if listing.get("price"))
                / max(1, sum(1 for listing in budget_filtered_listings if listing.get("price")))
            )
            if any(listing.get("price") for listing in budget_filtered_listings)
            else 0
        )

        # Calculate per-preference impact for disabled preferences
        per_preference_impact = []
        for disabled_term in disabled:
            # How many MORE listings match if we re-enable this term?
            expanded_terms = enabled + [disabled_term]
            expanded_matches = [
                listing for listing in saved_listings
                if self._listing_matches_any_term(listing, expanded_terms)
                and self._listing_within_budget(listing, maximum_price)
            ]
            listings_added = len(expanded_matches) - matching_count

            # Rent savings: difference in average rent
            expanded_average = (
                round(
                    sum(listing["price"] for listing in expanded_matches if listing.get("price"))
                    / max(1, sum(1 for listing in expanded_matches if listing.get("price")))
                )
                if any(listing.get("price") for listing in expanded_matches)
                else 0
            )
            rent_saved = max(0, average_rent - expanded_average) if average_rent else 0

            per_preference_impact.append({
                "term": disabled_term,
                "enabled": False,
                "listings_added": max(0, listings_added),
                "rent_saved": rent_saved,
            })

        # Find best suggestion: listing under budget with highest match score
        suggestions = self._find_best_suggestions(
            budget_filtered_listings, enabled, disabled, maximum_price
        )

        # Generate positive framing message
        positive_message = self._generate_positive_message(
            matching_count, average_rent, maximum_price, suggestions
        )

        return {
            "matching_count": matching_count,
            "average_rent": average_rent,
            "per_preference_impact": per_preference_impact,
            "suggestions": suggestions,
            "positive_message": positive_message,
        }

    def _find_matching_listing_prices(
        self,
        listings: list[dict],
        term: str,
    ) -> list[float]:
        """Find prices of listings that match a given term in title/address/amenities."""
        matching_prices = []
        normalized_term = term.lower()

        for listing in listings:
            if listing.get("price") is None:
                continue
            if self._listing_contains_term(listing, normalized_term):
                matching_prices.append(listing["price"])

        return matching_prices

    def _listing_contains_term(self, listing: dict, normalized_term: str) -> bool:
        """Check if a listing matches a term in title, address, or amenities."""
        title = (listing.get("title") or "").lower()
        address = (listing.get("address") or "").lower()

        if normalized_term in title or normalized_term in address:
            return True

        amenities = listing.get("amenities") or []
        if isinstance(amenities, str):
            try:
                amenities = json.loads(amenities)
            except (json.JSONDecodeError, TypeError):
                amenities = []

        for amenity in amenities:
            if normalized_term in str(amenity).lower():
                return True

        return False

    def _listing_matches_any_term(self, listing: dict, terms: list[str]) -> bool:
        """Check if a listing matches ANY of the given terms."""
        for term in terms:
            if self._listing_contains_term(listing, term.lower()):
                return True
        return False

    def _listing_within_budget(
        self,
        listing: dict,
        maximum_price: int | float | None,
    ) -> bool:
        """Check if listing price is within budget (or no budget set)."""
        if maximum_price is None:
            return True
        listing_price = listing.get("price")
        if listing_price is None:
            return True  # Include listings with unknown price
        return listing_price <= maximum_price

    def _find_best_suggestions(
        self,
        budget_filtered_listings: list[dict],
        enabled_terms: list[str],
        disabled_terms: list[str],
        maximum_price: int | float | None,
    ) -> list[dict]:
        """Find best matching listings under budget as suggestions."""
        if not budget_filtered_listings:
            return []

        scored_listings = []
        for listing in budget_filtered_listings:
            matching_preferences = [
                term for term in enabled_terms
                if self._listing_contains_term(listing, term.lower())
            ]
            missing_preferences = [
                term for term in disabled_terms
                if not self._listing_contains_term(listing, term.lower())
            ]
            match_count = len(matching_preferences)
            scored_listings.append({
                "listing_id": listing["id"],
                "title": listing.get("title", ""),
                "price": listing.get("price"),
                "match_score": listing.get("match_score"),
                "matching_preferences": matching_preferences,
                "missing_preferences": missing_preferences,
                "preference_match_count": match_count,
            })

        # Sort by preference match count descending, then by price ascending
        scored_listings.sort(
            key=lambda item: (-item["preference_match_count"], item.get("price") or 0)
        )

        # Return top 3 suggestions
        return scored_listings[:3]

    def _generate_positive_message(
        self,
        matching_count: int,
        average_rent: int,
        maximum_price: int | float | None,
        suggestions: list[dict],
    ) -> str:
        """Generate a positive framing message — never negative language."""
        if matching_count == 0:
            return "Adjusting your preferences could open up new options. Try toggling some filters."

        if suggestions and suggestions[0].get("title"):
            best_suggestion_title = suggestions[0]["title"]
            if maximum_price and average_rent <= maximum_price:
                return (
                    f"Great news — {matching_count} listings match your preferences "
                    f"at an average of ${average_rent:,}/mo, within your budget."
                )
            return (
                f"Found {matching_count} listings matching your preferences. "
                f"Check out {best_suggestion_title} as a starting point."
            )

        if maximum_price and average_rent <= maximum_price:
            return (
                f"You have {matching_count} options averaging ${average_rent:,}/mo — "
                f"well within your ${maximum_price:,}/mo budget."
            )

        return (
            f"Found {matching_count} listings matching your current preferences. "
            f"Toggle preferences to discover more options."
        )
