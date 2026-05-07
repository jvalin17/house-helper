"""Cost repository — tests for apartment cost breakdowns."""

import sqlite3
import pytest
from shared.db import migrate
from agents.apartment.repositories.cost_repo import CostRepository


@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    connection.execute(
        "INSERT INTO apartment_listings (id, title, price) VALUES (1, 'Alexan Braker Pointe', 1445)"
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def cost_repo(database_connection):
    return CostRepository(database_connection)


class TestCostRepo:
    def test_save_and_retrieve_cost(self, cost_repo):
        cost_repo.save_cost(1, base_rent=1445, parking_fee=150, pet_fee=50, utilities_estimate=120)
        cost = cost_repo.get_cost(1)
        assert cost is not None
        assert cost["base_rent"] == 1445
        assert cost["parking_fee"] == 150
        assert cost["pet_fee"] == 50
        assert cost["utilities_estimate"] == 120
        assert cost["total_monthly"] == 1445 + 150 + 50 + 120  # 1765

    def test_calculates_effective_monthly_with_concession(self, cost_repo):
        """2 months free on 14-month lease: (1445*14 - 2890) / 14 = $1,238.57"""
        cost_repo.save_cost(
            1, base_rent=1445, lease_months=14,
            special_discount=2890, special_description="2 months free",
        )
        cost = cost_repo.get_cost(1)
        assert cost["effective_monthly"] == round((1445 * 14 - 2890) / 14, 2)
        assert cost["effective_monthly"] < cost["base_rent"]

    def test_update_existing_cost(self, cost_repo):
        cost_repo.save_cost(1, base_rent=1445, parking_fee=100)
        cost_repo.save_cost(1, base_rent=1445, parking_fee=200)
        cost = cost_repo.get_cost(1)
        assert cost["parking_fee"] == 200

    def test_get_nonexistent_returns_none(self, cost_repo):
        assert cost_repo.get_cost(999) is None

    def test_total_monthly_includes_all_fees(self, cost_repo):
        cost_repo.save_cost(
            1, base_rent=1500, parking_fee=150,
            pet_fee=75, utilities_estimate=130,
        )
        cost = cost_repo.get_cost(1)
        assert cost["total_monthly"] == 1500 + 150 + 75 + 130  # 1855

    def test_zero_fees_default(self, cost_repo):
        cost_repo.save_cost(1, base_rent=1200)
        cost = cost_repo.get_cost(1)
        assert cost["parking_fee"] == 0
        assert cost["pet_fee"] == 0
        assert cost["utilities_estimate"] == 0
        assert cost["total_monthly"] == 1200
