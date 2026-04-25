"""Tests for calibration/exporter — anonymized calibration data export."""

import json

from shared.calibration.exporter import anonymize_judgements, export_calibration


SAMPLE_JUDGEMENTS = [
    {
        "job_id": 1,
        "match_score": 0.75,
        "match_features": {"skills_overlap": 0.9, "semantic_sim": 0.6},
        "user_rating": "good",
        "notes": "Great match for my Python skills",
        "job_title": "Senior Engineer at Google",
        "job_company": "Google",
    },
    {
        "job_id": 2,
        "match_score": 0.3,
        "match_features": {"skills_overlap": 0.2, "semantic_sim": 0.4},
        "user_rating": "poor",
        "notes": "Not relevant to my background",
        "job_title": "Chef at Restaurant",
        "job_company": "FancyFood",
    },
]


class TestAnonymizeJudgements:
    """Strip PII from calibration data before export."""

    def test_removes_job_title(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "job_title" not in entry

    def test_removes_company(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "job_company" not in entry

    def test_removes_notes(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "notes" not in entry

    def test_removes_job_id(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "job_id" not in entry

    def test_keeps_features(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "match_features" in entry

    def test_keeps_rating(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "user_rating" in entry

    def test_keeps_score(self):
        anonymized = anonymize_judgements(SAMPLE_JUDGEMENTS)
        for entry in anonymized:
            assert "match_score" in entry

    def test_empty_input(self):
        assert anonymize_judgements([]) == []


class TestExportCalibration:
    """Export calibration data as JSON string."""

    def test_returns_valid_json(self):
        result = export_calibration(SAMPLE_JUDGEMENTS, {"skills_overlap": 0.5, "semantic_sim": 0.5})
        parsed = json.loads(result)
        assert "judgements" in parsed
        assert "weights" in parsed

    def test_judgements_are_anonymized(self):
        result = export_calibration(SAMPLE_JUDGEMENTS, {})
        parsed = json.loads(result)
        for entry in parsed["judgements"]:
            assert "job_id" not in entry
            assert "notes" not in entry

    def test_includes_weights(self):
        weights = {"skills_overlap": 0.6, "semantic_sim": 0.4}
        result = export_calibration([], weights)
        parsed = json.loads(result)
        assert parsed["weights"] == weights
