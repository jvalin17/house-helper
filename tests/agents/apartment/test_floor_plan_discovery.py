"""Floor plan discovery — tests for finding and saving floor plan images.

Covers: discovery from parsed_data, discovery from image URLs with keywords,
saving to apartment_floor_plans table, URL extraction floor plan saving.
"""

import json
import sqlite3

import pytest

from shared.db import migrate
from shared.pipeline import PipelineContext
from agents.apartment.services.intel_service import IntelService


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def listing_with_floor_plan_in_parsed_data(database_connection):
    """Listing where URL extraction found floor plan images."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, source_url, parsed_data)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "Alexan Braker Pointe",
            "10801 N Mopac Expy, Austin, TX 78759",
            1445.0,
            "https://www.alexanbrakerpointe.com/",
            json.dumps({
                "floor_plan_images": [
                    "https://example.com/floorplan-studio.png",
                    "https://example.com/floorplan-1br.png",
                ],
                "images": [
                    "https://example.com/photo1.jpg",
                    "https://example.com/photo2.jpg",
                ],
            }),
        ),
    )
    database_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def listing_with_floor_plan_in_images(database_connection):
    """Listing where images contain floor-plan-like URLs."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, source_url, parsed_data)
           VALUES (?, ?, ?, ?, ?)""",
        (
            "Camden North End",
            "4730 E Palm Valley Blvd, Round Rock, TX 78665",
            1650.0,
            "https://www.camdenliving.com/",
            json.dumps({
                "images": [
                    "https://cdn.example.com/property-exterior.jpg",
                    "https://cdn.example.com/floor-plan-2br-deluxe.png",
                    "https://cdn.example.com/pool-area.jpg",
                    "https://cdn.example.com/layout-studio-a.png",
                ],
            }),
        ),
    )
    database_connection.commit()
    return cursor.lastrowid


@pytest.fixture
def listing_without_floor_plans(database_connection):
    """Listing with no floor plan data anywhere."""
    cursor = database_connection.execute(
        """INSERT INTO apartment_listings
           (title, address, price, parsed_data)
           VALUES (?, ?, ?, ?)""",
        ("Basic Apt", "123 Oak St", 1200.0, json.dumps({"images": ["photo1.jpg", "photo2.jpg"]})),
    )
    database_connection.commit()
    return cursor.lastrowid


def _count_floor_plans(database_connection, listing_id):
    row = database_connection.execute(
        "SELECT COUNT(*) as count FROM apartment_floor_plans WHERE listing_id = ?",
        (listing_id,),
    ).fetchone()
    return row["count"]


def test_discover_from_parsed_data(database_connection, listing_with_floor_plan_in_parsed_data):
    """Floor plans from parsed_data.floor_plan_images saved to DB."""
    listing_id = listing_with_floor_plan_in_parsed_data
    listing = dict(database_connection.execute(
        "SELECT * FROM apartment_listings WHERE id = ?", (listing_id,)
    ).fetchone())
    listing["parsed_data"] = json.loads(listing["parsed_data"])

    service = IntelService(database_connection)
    context = PipelineContext(source_data={"listing_id": listing_id, "listing": listing})
    service._discover_floor_plans(context)

    assert _count_floor_plans(database_connection, listing_id) == 2

    rows = database_connection.execute(
        "SELECT image_url FROM apartment_floor_plans WHERE listing_id = ?",
        (listing_id,),
    ).fetchall()
    urls = [row["image_url"] for row in rows]
    assert "https://example.com/floorplan-studio.png" in urls
    assert "https://example.com/floorplan-1br.png" in urls


def test_discover_from_image_urls_with_keywords(database_connection, listing_with_floor_plan_in_images):
    """Images with 'floor', 'plan', 'layout' in URL detected as floor plans."""
    listing_id = listing_with_floor_plan_in_images
    listing = dict(database_connection.execute(
        "SELECT * FROM apartment_listings WHERE id = ?", (listing_id,)
    ).fetchone())
    listing["parsed_data"] = json.loads(listing["parsed_data"])

    service = IntelService(database_connection)
    context = PipelineContext(source_data={"listing_id": listing_id, "listing": listing})
    service._discover_floor_plans(context)

    assert _count_floor_plans(database_connection, listing_id) == 2

    rows = database_connection.execute(
        "SELECT image_url FROM apartment_floor_plans WHERE listing_id = ?",
        (listing_id,),
    ).fetchall()
    urls = [row["image_url"] for row in rows]
    assert "https://cdn.example.com/floor-plan-2br-deluxe.png" in urls
    assert "https://cdn.example.com/layout-studio-a.png" in urls
    # Regular photos should NOT be saved as floor plans
    assert "https://cdn.example.com/property-exterior.jpg" not in urls


def test_no_floor_plans_found(database_connection, listing_without_floor_plans):
    """Listing with no floor plan data — nothing saved, no error."""
    listing_id = listing_without_floor_plans
    listing = dict(database_connection.execute(
        "SELECT * FROM apartment_listings WHERE id = ?", (listing_id,)
    ).fetchone())
    listing["parsed_data"] = json.loads(listing["parsed_data"])

    service = IntelService(database_connection)
    context = PipelineContext(source_data={"listing_id": listing_id, "listing": listing})
    service._discover_floor_plans(context)

    assert _count_floor_plans(database_connection, listing_id) == 0


def test_max_5_floor_plans_saved(database_connection):
    """Cap at 5 floor plans even if more are found."""
    cursor = database_connection.execute(
        "INSERT INTO apartment_listings (title, price, parsed_data) VALUES (?, ?, ?)",
        ("Big Complex", 2000.0, json.dumps({
            "floor_plan_images": [f"https://example.com/floor-plan-{index}.png" for index in range(10)],
        })),
    )
    database_connection.commit()
    listing_id = cursor.lastrowid

    listing = dict(database_connection.execute("SELECT * FROM apartment_listings WHERE id = ?", (listing_id,)).fetchone())
    listing["parsed_data"] = json.loads(listing["parsed_data"])

    service = IntelService(database_connection)
    context = PipelineContext(source_data={"listing_id": listing_id, "listing": listing})
    service._discover_floor_plans(context)

    assert _count_floor_plans(database_connection, listing_id) == 5
