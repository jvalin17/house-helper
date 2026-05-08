"""Photo analyzer — tests for AI vision analysis of apartment visit photos.

Covers: no-photos error, prompt building, analysis caching, cost estimate,
score clamping, missing files handling, non-vision provider rejection,
and successful analysis flow.
"""

import json
import os
import sqlite3
import tempfile

import pytest

from shared.db import migrate
from shared.llm.base import LLMProviderBase
from agents.apartment.repositories.photo_repo import PhotoRepository
from agents.apartment.repositories.lab_analysis_repo import LabAnalysisRepository
from agents.apartment.services.photo_analyzer import PhotoAnalyzer
from agents.apartment.prompts.photo_analysis import build_photo_analysis_prompt


# ── Fixtures ──────────────────────────────────────────

@pytest.fixture
def database_connection():
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    connection.row_factory = sqlite3.Row
    migrate(connection)
    connection.execute(
        "INSERT INTO apartment_listings (id, title, address, price) "
        "VALUES (1, 'Alexan Braker Pointe', '11011 Domain Dr, Austin, TX 78758', 1445)"
    )
    connection.commit()
    yield connection
    connection.close()


@pytest.fixture
def photo_repo(database_connection):
    return PhotoRepository(database_connection)


@pytest.fixture
def lab_analysis_repo(database_connection):
    return LabAnalysisRepository(database_connection)


@pytest.fixture
def sample_analysis_response():
    """Standard mock analysis JSON returned by the vision LLM."""
    return {
        "rooms": [
            {
                "room_type": "kitchen",
                "observations": "Modern galley-style kitchen with granite counters",
                "condition_score": 8,
                "positives": ["Granite countertops", "Stainless steel appliances"],
                "concerns": ["Limited counter space"],
            },
            {
                "room_type": "bedroom",
                "observations": "Spacious bedroom with large window",
                "condition_score": 7,
                "positives": ["Good natural light", "Walk-in closet"],
                "concerns": ["Carpet shows some wear"],
            },
        ],
        "overall_condition": {
            "score": 7,
            "explanation": "Generally well-maintained with minor cosmetic issues",
        },
        "natural_light": "Good natural light from south-facing windows in bedroom and living area",
        "storage_adequacy": "Adequate — walk-in closet in bedroom, pantry in kitchen",
        "questions_for_landlord": [
            "When was the carpet last replaced?",
            "Are there plans to update the kitchen counters?",
        ],
        "move_in_readiness": "ready",
        "summary": "Well-maintained apartment in good condition. Kitchen is functional but compact. Bedroom has excellent natural light and generous closet space.",
    }


class MockVisionProvider(LLMProviderBase):
    """Mock LLM provider with vision support."""

    def __init__(self, response_json: dict):
        self._response = json.dumps(response_json)
        self._configured = True

    def complete(self, prompt, system=None, feature=None):
        return self._response

    def complete_with_images(self, prompt, images, system=None, feature=None):
        self.last_prompt = prompt
        self.last_images = images
        self.last_system = system
        return self._response

    def provider_name(self):
        return "mock_vision"

    def model_name(self):
        return "mock-vision-4o"

    @property
    def supports_vision(self):
        return True

    def is_configured(self):
        return self._configured


class MockNonVisionProvider(LLMProviderBase):
    """Mock LLM provider WITHOUT vision support."""

    def complete(self, prompt, system=None, feature=None):
        return "{}"

    def provider_name(self):
        return "mock_text"

    def model_name(self):
        return "mock-text-only"

    def is_configured(self):
        return True


# ── Prompt building ──────────────────────────────────

class TestBuildPhotoAnalysisPrompt:
    def test_prompt_includes_property_name(self):
        prompt = build_photo_analysis_prompt(
            listing_title="Alexan Braker Pointe",
            address="11011 Domain Dr, Austin, TX 78758",
        )
        assert "Alexan Braker Pointe" in prompt
        assert "11011 Domain Dr" in prompt

    def test_prompt_includes_room_tags(self):
        prompt = build_photo_analysis_prompt(
            listing_title="Test Property",
            room_tags=["kitchen", "bedroom", "kitchen"],
        )
        assert "bedroom" in prompt
        assert "kitchen" in prompt

    def test_prompt_without_address(self):
        prompt = build_photo_analysis_prompt(listing_title="Test Property")
        assert "Test Property" in prompt
        assert "condition" in prompt.lower()

    def test_prompt_includes_evaluation_criteria(self):
        prompt = build_photo_analysis_prompt(listing_title="Test")
        assert "condition" in prompt.lower()
        assert "natural light" in prompt.lower()
        assert "landlord" in prompt.lower()
        assert "move-in" in prompt.lower() or "move_in" in prompt.lower()


# ── No photos error ──────────────────────────────────

class TestNoPhotosError:
    def test_analyze_raises_when_no_photos(self, database_connection, photo_repo, sample_analysis_response):
        provider = MockVisionProvider(sample_analysis_response)
        analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)

        with pytest.raises(ValueError, match="No photos found"):
            analyzer.analyze(1)

    def test_analyze_raises_when_files_unreadable(self, database_connection, photo_repo, sample_analysis_response):
        """Photos exist in DB but files can't be read from disk."""
        photo_repo.save_photos(1, [
            {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg", "room_tag": "kitchen"},
        ])
        provider = MockVisionProvider(sample_analysis_response)
        analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)

        with pytest.raises(ValueError, match="No photo files could be read"):
            analyzer.analyze(1)


# ── Provider validation ──────────────────────────────

class TestProviderValidation:
    def test_analyze_raises_without_configured_provider(self, database_connection, photo_repo):
        with tempfile.TemporaryDirectory() as temp_directory:
            photo_directory = os.path.join(temp_directory, "photos", "1")
            os.makedirs(photo_directory)
            photo_file_path = os.path.join(photo_directory, "abc12345-6789-0abc-def0-123456789abc.jpg")
            with open(photo_file_path, "wb") as temp_file:
                temp_file.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
            ])

            os.environ["APP_DATA_DIR"] = temp_directory
            try:
                analyzer = PhotoAnalyzer(database_connection, None, photo_repo)
                with pytest.raises(ValueError, match="No AI provider configured"):
                    analyzer.analyze(1)
            finally:
                os.environ.pop("APP_DATA_DIR", None)

    def test_analyze_raises_for_non_vision_provider(self, database_connection, photo_repo):
        # Create a real file so we get past the file-reading step
        with tempfile.TemporaryDirectory() as temp_directory:
            photo_directory = os.path.join(temp_directory, "photos", "1")
            os.makedirs(photo_directory)
            photo_file_path = os.path.join(photo_directory, "abc12345-6789-0abc-def0-123456789abc.jpg")
            with open(photo_file_path, "wb") as temp_file:
                temp_file.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
            ])

            os.environ["APP_DATA_DIR"] = temp_directory
            try:
                provider = MockNonVisionProvider()
                analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
                with pytest.raises(ValueError, match="does not support image analysis"):
                    analyzer.analyze(1)
            finally:
                os.environ.pop("APP_DATA_DIR", None)


# ── Cost estimation ──────────────────────────────────

class TestCostEstimation:
    def test_estimate_cost_with_photos(self, database_connection, photo_repo):
        photo_repo.save_photos(1, [
            {"file_path": "photos/1/aaaa1111-2222-3333-4444-555566667777.jpg"},
            {"file_path": "photos/1/bbbb1111-2222-3333-4444-555566667777.jpg"},
            {"file_path": "photos/1/cccc1111-2222-3333-4444-555566667777.jpg"},
        ])
        provider = MockVisionProvider({})
        analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
        estimated_cost = analyzer.estimate_cost(1)
        assert estimated_cost == 0.015

    def test_estimate_cost_no_photos(self, database_connection, photo_repo):
        provider = MockVisionProvider({})
        analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
        assert analyzer.estimate_cost(1) == 0.0


# ── Score clamping ───────────────────────────────────

class TestScoreClamping:
    def test_overall_score_clamped_to_max(self, database_connection, photo_repo):
        with tempfile.TemporaryDirectory() as temp_directory:
            photo_directory = os.path.join(temp_directory, "photos", "1")
            os.makedirs(photo_directory)
            photo_file_path = os.path.join(photo_directory, "abc12345-6789-0abc-def0-123456789abc.jpg")
            with open(photo_file_path, "wb") as temp_file:
                temp_file.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
            ])

            os.environ["APP_DATA_DIR"] = temp_directory
            try:
                response = {
                    "overall_condition": {"score": 15, "explanation": "Over the top"},
                    "rooms": [
                        {"room_type": "kitchen", "observations": "Good", "condition_score": 12, "positives": [], "concerns": []},
                    ],
                    "summary": "Great place",
                }
                provider = MockVisionProvider(response)
                analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
                result = analyzer.analyze(1)
                assert result["overall_condition"]["score"] == 10
                assert result["rooms"][0]["condition_score"] == 10
            finally:
                os.environ.pop("APP_DATA_DIR", None)

    def test_overall_score_clamped_to_min(self, database_connection, photo_repo):
        with tempfile.TemporaryDirectory() as temp_directory:
            photo_directory = os.path.join(temp_directory, "photos", "1")
            os.makedirs(photo_directory)
            photo_file_path = os.path.join(photo_directory, "abc12345-6789-0abc-def0-123456789abc.jpg")
            with open(photo_file_path, "wb") as temp_file:
                temp_file.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
            ])

            os.environ["APP_DATA_DIR"] = temp_directory
            try:
                response = {
                    "overall_condition": {"score": -5, "explanation": "Terrible"},
                    "rooms": [],
                    "summary": "Awful place",
                }
                provider = MockVisionProvider(response)
                analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
                result = analyzer.analyze(1)
                assert result["overall_condition"]["score"] == 1
            finally:
                os.environ.pop("APP_DATA_DIR", None)


# ── Analysis caching ────────────────────────────────

class TestAnalysisCaching:
    def test_analysis_cached_in_lab_analysis(self, database_connection, photo_repo, lab_analysis_repo, sample_analysis_response):
        with tempfile.TemporaryDirectory() as temp_directory:
            photo_directory = os.path.join(temp_directory, "photos", "1")
            os.makedirs(photo_directory)
            photo_file_path = os.path.join(photo_directory, "abc12345-6789-0abc-def0-123456789abc.jpg")
            with open(photo_file_path, "wb") as temp_file:
                temp_file.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            photo_repo.save_photos(1, [
                {"file_path": "photos/1/abc12345-6789-0abc-def0-123456789abc.jpg"},
            ])

            os.environ["APP_DATA_DIR"] = temp_directory
            try:
                provider = MockVisionProvider(sample_analysis_response)
                analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
                result = analyzer.analyze(1)

                # Verify it was cached
                cached = lab_analysis_repo.get_cached_analysis(1, "photo_analysis")
                assert cached is not None
                assert cached["overall_condition"]["score"] == 7
                assert cached["move_in_readiness"] == "ready"
            finally:
                os.environ.pop("APP_DATA_DIR", None)

    def test_get_cached_analysis(self, database_connection, photo_repo, lab_analysis_repo, sample_analysis_response):
        # Manually cache some analysis
        lab_analysis_repo.save_analysis(1, "photo_analysis", sample_analysis_response)

        provider = MockVisionProvider({})
        analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
        cached = analyzer.get_cached_analysis(1)
        assert cached is not None
        assert cached["overall_condition"]["score"] == 7

    def test_get_cached_analysis_returns_none_when_empty(self, database_connection, photo_repo):
        provider = MockVisionProvider({})
        analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
        assert analyzer.get_cached_analysis(1) is None


# ── Full analysis flow ───────────────────────────────

class TestFullAnalysisFlow:
    def test_successful_analysis_returns_structured_result(self, database_connection, photo_repo, sample_analysis_response):
        with tempfile.TemporaryDirectory() as temp_directory:
            photo_directory = os.path.join(temp_directory, "photos", "1")
            os.makedirs(photo_directory)

            # Create two photo files
            for file_name in ["aaaa1111-2222-3333-4444-555566667777.jpg", "bbbb1111-2222-3333-4444-555566667777.png"]:
                file_path = os.path.join(photo_directory, file_name)
                with open(file_path, "wb") as temp_file:
                    temp_file.write(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            photo_repo.save_photos(1, [
                {"file_path": "photos/1/aaaa1111-2222-3333-4444-555566667777.jpg", "room_tag": "kitchen"},
                {"file_path": "photos/1/bbbb1111-2222-3333-4444-555566667777.png", "room_tag": "bedroom"},
            ])

            os.environ["APP_DATA_DIR"] = temp_directory
            try:
                provider = MockVisionProvider(sample_analysis_response)
                analyzer = PhotoAnalyzer(database_connection, provider, photo_repo)
                result = analyzer.analyze(1)

                assert result["overall_condition"]["score"] == 7
                assert result["move_in_readiness"] == "ready"
                assert len(result["rooms"]) == 2
                assert result["rooms"][0]["room_type"] == "kitchen"
                assert result["rooms"][0]["condition_score"] == 8
                assert "Granite countertops" in result["rooms"][0]["positives"]
                assert result["natural_light"] is not None
                assert len(result["questions_for_landlord"]) == 2

                # Verify images were sent to the provider
                assert len(provider.last_images) == 2
                assert "data" in provider.last_images[0]
                assert provider.last_images[0]["media_type"] == "image/jpeg"
            finally:
                os.environ.pop("APP_DATA_DIR", None)
