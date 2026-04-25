"""Anonymized calibration data export.

Strips all PII (company names, job titles, user notes) before export.
Only match feature vectors and user ratings are included.
"""

import json

# Fields that contain PII and must be stripped before export
PII_FIELDS = {"job_id", "job_title", "job_company", "notes", "company", "title"}

# Fields to keep in the anonymized export
KEEP_FIELDS = {"match_score", "match_features", "user_rating"}


def anonymize_judgements(judgements: list[dict]) -> list[dict]:
    """Strip PII from judgement data, keeping only feature vectors and ratings."""
    return [
        {key: value for key, value in judgement.items() if key in KEEP_FIELDS}
        for judgement in judgements
    ]


def export_calibration(judgements: list[dict], weights: dict) -> str:
    """Export anonymized calibration data as a JSON string.

    Includes anonymized judgements and current weights.
    Safe to share — no PII included.
    """
    anonymized = anonymize_judgements(judgements)

    export_data = {
        "version": 1,
        "judgements": anonymized,
        "weights": weights,
    }

    return json.dumps(export_data, indent=2)
