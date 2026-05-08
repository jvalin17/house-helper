"""Distance calculator — compute distance between coordinates.

Haversine formula for straight-line distance. Good enough for nearby places
(< 10 miles). No API call needed — pure math.

Also provides radius bucketing for organizing places by walkability.
"""

import math

EARTH_RADIUS_MILES = 3959.0

# Radius buckets for organizing nearby places
RADIUS_BUCKETS = [
    {"max_miles": 0.5, "label": "Walking distance", "emoji": "🚶"},
    {"max_miles": 1.0, "label": "Short walk / bike", "emoji": "🚲"},
    {"max_miles": 2.0, "label": "Quick drive", "emoji": "🚗"},
    {"max_miles": 3.0, "label": "Short drive", "emoji": "🚗"},
    {"max_miles": 5.0, "label": "Nearby", "emoji": "📍"},
    {"max_miles": 10.0, "label": "In the area", "emoji": "🗺️"},
]


def haversine_distance_miles(
    latitude_from: float,
    longitude_from: float,
    latitude_to: float,
    longitude_to: float,
) -> float:
    """Calculate distance in miles between two lat/lng points."""
    latitude_from_radians = math.radians(latitude_from)
    latitude_to_radians = math.radians(latitude_to)
    delta_latitude = math.radians(latitude_to - latitude_from)
    delta_longitude = math.radians(longitude_to - longitude_from)

    haversine_a = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(latitude_from_radians) * math.cos(latitude_to_radians)
        * math.sin(delta_longitude / 2) ** 2
    )
    haversine_c = 2 * math.atan2(math.sqrt(haversine_a), math.sqrt(1 - haversine_a))

    return EARTH_RADIUS_MILES * haversine_c


def add_distances_to_places(
    places: list[dict],
    origin_latitude: float,
    origin_longitude: float,
) -> list[dict]:
    """Add distance_miles and radius_bucket to each place."""
    for place in places:
        place_latitude = place.get("latitude")
        place_longitude = place.get("longitude")

        if place_latitude is not None and place_longitude is not None:
            distance = haversine_distance_miles(
                origin_latitude, origin_longitude,
                place_latitude, place_longitude,
            )
            place["distance_miles"] = round(distance, 2)
            place["radius_bucket"] = _get_radius_bucket(distance)
        else:
            place["distance_miles"] = None
            place["radius_bucket"] = None

    return places


def group_places_by_radius(
    places: list[dict],
) -> dict[str, list[dict]]:
    """Group places into radius buckets. Each place goes in the smallest bucket it fits.

    Pre-sorts by distance (O(N log N)), then single pass assigns each place
    to the smallest matching bucket — O(N) after sort.
    """
    valid_places = [
        place for place in places
        if place.get("distance_miles") is not None
    ]
    sorted_places = sorted(valid_places, key=lambda entry: entry["distance_miles"])

    buckets: dict[str, list[dict]] = {}
    for place in sorted_places:
        distance = place["distance_miles"]
        for bucket in RADIUS_BUCKETS:
            if distance <= bucket["max_miles"]:
                bucket_key = f"{bucket['max_miles']}mi"
                buckets.setdefault(bucket_key, []).append(place)
                break

    return buckets


def _get_radius_bucket(distance_miles: float) -> str:
    """Get the human-readable radius bucket for a distance."""
    for bucket in RADIUS_BUCKETS:
        if distance_miles <= bucket["max_miles"]:
            return f"{bucket['emoji']} {bucket['label']} ({bucket['max_miles']}mi)"
    return "🗺️ Far away"
