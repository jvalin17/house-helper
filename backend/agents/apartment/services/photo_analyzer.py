"""Photo analyzer service — AI vision analysis of apartment visit photos.

Sends visit photos to a vision-capable LLM for structured analysis:
room-by-room condition scoring, natural light assessment, questions
for the landlord, and overall move-in readiness.

Requires:
  - Vision-capable LLM provider (supports_vision = True)
  - Photos stored via PhotoRepository
"""

import base64
import os
import sqlite3

from shared.app_logger import get_logger
from shared.pipeline import parse_llm_json_response
from agents.apartment.prompts.photo_analysis import (
    build_photo_analysis_prompt,
    SYSTEM_PROMPT,
)
from agents.apartment.repositories.photo_repo import PhotoRepository

logger = get_logger("apartment.photo_analyzer")

CONDITION_SCORE_MIN = 1
CONDITION_SCORE_MAX = 10

# Estimated cost per photo for vision analysis (rough average across providers)
ESTIMATED_COST_PER_PHOTO = 0.005


class PhotoAnalyzer:
    """Analyzes apartment visit photos using a vision-capable LLM."""

    def __init__(
        self,
        connection: sqlite3.Connection,
        llm_provider,
        photo_repo: PhotoRepository,
    ):
        self._connection = connection
        self._llm_provider = llm_provider
        self._photo_repo = photo_repo

    def analyze(self, listing_id: int) -> dict:
        """Run AI vision analysis on all photos for a listing.

        Steps:
            1. Get photos from photo_repo
            2. Read photo files from disk and base64 encode
            3. Build vision prompt with listing context
            4. Call LLM vision API
            5. Parse and validate JSON response
            6. Cache results via lab_analysis_repo
            7. Return structured result

        Raises:
            ValueError: If listing has no photos or no photos have readable files.
        """
        photos = self._photo_repo.list_photos(listing_id)
        if not photos:
            raise ValueError("No photos found for this listing. Upload photos first.")

        # Read photo files and encode as base64
        image_data_list = self._load_photo_images(photos)
        if not image_data_list:
            raise ValueError(
                "No photo files could be read from disk. "
                "Photos may have been moved or deleted."
            )

        # Verify LLM supports vision
        if not self._llm_provider or not self._llm_provider.is_configured():
            raise ValueError("No AI provider configured. Set one in Settings.")

        if not self._llm_provider.supports_vision:
            raise ValueError(
                f"{self._llm_provider.provider_name()} does not support image analysis. "
                f"Use a vision-capable provider (Claude or GPT-4o)."
            )

        # Get listing context for the prompt
        listing_row = self._connection.execute(
            "SELECT title, address FROM apartment_listings WHERE id = ?",
            (listing_id,),
        ).fetchone()
        listing_title = listing_row["title"] if listing_row else "Unknown Property"
        listing_address = listing_row["address"] if listing_row else None

        # Collect room tags for prompt context
        room_tags = [
            photo["room_tag"]
            for photo in photos
            if photo.get("room_tag")
        ]

        prompt = build_photo_analysis_prompt(
            listing_title=listing_title,
            address=listing_address,
            room_tags=room_tags if room_tags else None,
        )

        # Call vision LLM
        try:
            response = self._llm_provider.complete_with_images(
                prompt=prompt,
                images=image_data_list,
                system=SYSTEM_PROMPT,
                feature="photo_analysis",
            )

            parsed_result = parse_llm_json_response(response)
            if parsed_result:
                parsed_result = self._validate_and_clamp_scores(parsed_result)
                self._cache_analysis(listing_id, parsed_result)
                return parsed_result

            # Non-JSON response — wrap as summary
            logger.warning("Vision LLM returned non-JSON for photo analysis")
            fallback_result = {"summary": response, "parse_error": True}
            self._cache_analysis(listing_id, fallback_result)
            return fallback_result

        except Exception as analysis_error:
            logger.error("Photo analysis failed for listing %d: %s", listing_id, analysis_error)
            raise

    def estimate_cost(self, listing_id: int) -> float:
        """Estimate the cost of analyzing photos for a listing.

        Returns estimated cost in dollars based on photo count.
        """
        photo_count = self._photo_repo.get_photo_count(listing_id)
        return round(photo_count * ESTIMATED_COST_PER_PHOTO, 4)

    def get_cached_analysis(self, listing_id: int) -> dict | None:
        """Get cached photo analysis from lab_analysis_repo if available."""
        from agents.apartment.repositories.lab_analysis_repo import LabAnalysisRepository
        lab_analysis_repo = LabAnalysisRepository(self._connection)
        return lab_analysis_repo.get_cached_analysis(listing_id, "photo_analysis")

    def _load_photo_images(self, photos: list[dict]) -> list[dict]:
        """Load photo files from disk and encode as base64 for vision LLM.

        Returns list of image dicts suitable for complete_with_images().
        Skips files that cannot be read (logs warning, continues).
        """
        app_data_directory = os.environ.get("APP_DATA_DIR", "")
        image_data_list = []

        for photo in photos:
            file_path = photo.get("file_path", "")
            if not file_path:
                continue

            full_path = os.path.join(app_data_directory, file_path) if app_data_directory else file_path

            try:
                with open(full_path, "rb") as image_file:
                    binary_data = image_file.read()

                media_type = self._detect_image_type(binary_data)
                encoded_data = base64.b64encode(binary_data).decode("ascii")
                image_data_list.append({
                    "data": encoded_data,
                    "media_type": media_type,
                })
            except (OSError, IOError) as file_error:
                logger.warning(
                    "Could not read photo file '%s': %s — skipping",
                    file_path,
                    file_error,
                )
                continue

        return image_data_list

    def _detect_image_type(self, binary_data: bytes) -> str:
        """Detect image MIME type from file header bytes."""
        if binary_data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if binary_data[:2] == b"\xff\xd8":
            return "image/jpeg"
        if binary_data[:4] == b"RIFF" and binary_data[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"

    def _validate_and_clamp_scores(self, result: dict) -> dict:
        """Clamp condition scores to valid range (1-10)."""
        # Clamp overall condition score
        overall_condition = result.get("overall_condition")
        if isinstance(overall_condition, dict):
            score = overall_condition.get("score")
            if isinstance(score, (int, float)):
                overall_condition["score"] = max(
                    CONDITION_SCORE_MIN,
                    min(CONDITION_SCORE_MAX, int(score)),
                )

        # Clamp per-room condition scores
        rooms = result.get("rooms")
        if isinstance(rooms, list):
            for room in rooms:
                if isinstance(room, dict):
                    room_score = room.get("condition_score")
                    if isinstance(room_score, (int, float)):
                        room["condition_score"] = max(
                            CONDITION_SCORE_MIN,
                            min(CONDITION_SCORE_MAX, int(room_score)),
                        )

        return result

    def _cache_analysis(self, listing_id: int, result: dict) -> None:
        """Cache analysis result in lab_analysis_repo for future retrieval."""
        from agents.apartment.repositories.lab_analysis_repo import LabAnalysisRepository
        lab_analysis_repo = LabAnalysisRepository(self._connection)
        lab_analysis_repo.save_analysis(
            listing_id=listing_id,
            analysis_type="photo_analysis",
            result=result,
        )
