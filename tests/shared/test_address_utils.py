"""Shared address utilities — tests."""

from shared.address_utils import extract_city_from_address


class TestExtractCityFromAddress:
    def test_extracts_city_from_standard_address(self):
        assert extract_city_from_address("10801 N Mopac Expy, Austin, TX, 78759") == "Austin"

    def test_extracts_city_from_two_part_address(self):
        assert extract_city_from_address("500 Elm St, Dallas") == "Dallas"

    def test_returns_empty_for_single_part(self):
        assert extract_city_from_address("Just a street name") == ""

    def test_returns_empty_for_empty_string(self):
        assert extract_city_from_address("") == ""

    def test_handles_extra_whitespace(self):
        assert extract_city_from_address("123 Main St ,  Houston , TX") == "Houston"

    def test_handles_none_gracefully(self):
        assert extract_city_from_address("") == ""
