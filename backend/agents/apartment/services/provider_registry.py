"""Registry of all apartment search providers.

To add a new provider:
  1. Create a class that extends ApartmentSearchProvider (see base_provider.py)
  2. Add it to the list in get_all_providers() below

All RealtyAPI sources share one API key. Each counts against the same
250 free requests/month quota, so we only enable Zillow + Apartments.com
by default to avoid burning through the quota.
"""

import sqlite3

from agents.apartment.services.realtyapi_search import RealtyApiProvider
from agents.apartment.services.rentcast_search import RentCastProvider


def get_all_providers(connection: sqlite3.Connection) -> list:
    """Return all registered search providers, ordered by priority.

    RealtyAPI (Zillow) first — best image coverage.
    RealtyAPI (Apartments.com) second — rental-focused, different inventory.
    RentCast third — structured market data, no images.
    Redfin/Realtor disabled by default — enable if user wants broader search.
    """
    return [
        RealtyApiProvider(connection, source_key="zillow"),
        RealtyApiProvider(connection, source_key="apartments"),
        RentCastProvider(connection),
        # Disabled by default to conserve API quota:
        # RealtyApiProvider(connection, source_key="redfin"),
        # RealtyApiProvider(connection, source_key="realtor"),
    ]
