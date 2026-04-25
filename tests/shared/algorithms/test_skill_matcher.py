"""Tests for skill_matcher — exact + fuzzy skill overlap scoring."""

from shared.algorithms.skill_matcher import compute_skill_overlap, find_best_match


class TestFindBestMatch:
    """Find the closest matching skill from a list of candidates."""

    def test_exact_match_returns_perfect_score(self):
        score, matched = find_best_match("Python", ["Java", "Python", "Go"])
        assert score == 1.0
        assert matched == "Python"

    def test_case_insensitive_match(self):
        score, matched = find_best_match("python", ["Python", "Java"])
        assert score == 1.0
        assert matched == "Python"

    def test_fuzzy_match_reactjs_variants(self):
        score, matched = find_best_match("React.js", ["ReactJS", "Vue.js"])
        assert score > 0.8
        assert matched == "ReactJS"

    def test_fuzzy_match_typescript_variants(self):
        score, matched = find_best_match("TypeScript", ["Typescript", "JavaScript"])
        assert score > 0.9
        assert matched == "Typescript"

    def test_no_match_returns_zero(self):
        score, matched = find_best_match("Python", ["Java", "Go", "Rust"])
        assert score < 0.5
        assert matched is None

    def test_empty_candidates_returns_zero(self):
        score, matched = find_best_match("Python", [])
        assert score == 0.0
        assert matched is None

    def test_abbreviation_match(self):
        score, matched = find_best_match("JS", ["JavaScript", "Python"])
        # JS is short — fuzzy matching may not catch this well, that's OK
        # This documents the limitation
        assert isinstance(score, float)


class TestComputeSkillOverlap:
    """Score how well a set of required skills overlaps with user skills."""

    def test_perfect_overlap(self):
        required = ["Python", "React", "Docker"]
        user_skills = ["Python", "React", "Docker", "AWS"]
        result = compute_skill_overlap(required, user_skills)
        assert result["score"] == 1.0
        assert len(result["matched"]) == 3
        assert len(result["missing"]) == 0

    def test_partial_overlap(self):
        required = ["Python", "React", "Docker", "Kubernetes"]
        user_skills = ["Python", "React"]
        result = compute_skill_overlap(required, user_skills)
        assert 0.4 < result["score"] < 0.6
        assert len(result["matched"]) == 2
        assert set(result["missing"]) == {"Docker", "Kubernetes"}

    def test_no_overlap(self):
        required = ["Java", "Spring", "Oracle"]
        user_skills = ["Python", "React", "PostgreSQL"]
        result = compute_skill_overlap(required, user_skills)
        assert result["score"] < 0.3
        assert len(result["matched"]) == 0
        assert len(result["missing"]) == 3

    def test_fuzzy_overlap(self):
        required = ["React.js", "Node.js", "TypeScript"]
        user_skills = ["ReactJS", "NodeJS", "Typescript"]
        result = compute_skill_overlap(required, user_skills)
        assert result["score"] > 0.8
        assert len(result["matched"]) == 3

    def test_empty_required_returns_perfect(self):
        result = compute_skill_overlap([], ["Python", "React"])
        assert result["score"] == 1.0
        assert len(result["matched"]) == 0
        assert len(result["missing"]) == 0

    def test_empty_user_skills_returns_zero(self):
        result = compute_skill_overlap(["Python", "React"], [])
        assert result["score"] == 0.0
        assert len(result["missing"]) == 2

    def test_result_contains_match_details(self):
        required = ["React.js"]
        user_skills = ["ReactJS"]
        result = compute_skill_overlap(required, user_skills)
        assert len(result["matched"]) == 1
        match = result["matched"][0]
        assert match["required"] == "React.js"
        assert match["matched_with"] == "ReactJS"
        assert match["confidence"] > 0.8
