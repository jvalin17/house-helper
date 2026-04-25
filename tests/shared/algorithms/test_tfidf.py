"""Tests for tfidf — TF-IDF keyword importance and document similarity."""

from shared.algorithms.tfidf import compute_similarity, extract_keywords


class TestComputeSimilarity:
    """Score similarity between two text documents using TF-IDF + cosine."""

    def test_identical_documents(self):
        score = compute_similarity(
            "Python developer with React experience",
            "Python developer with React experience",
        )
        assert score > 0.99

    def test_similar_documents(self):
        score = compute_similarity(
            "Senior Python developer with FastAPI and React experience",
            "Python engineer experienced in FastAPI and React frontend",
        )
        # TF-IDF with 2-doc corpus yields moderate scores for overlapping terms
        assert score > 0.2

    def test_unrelated_documents(self):
        score = compute_similarity(
            "Python developer with machine learning experience",
            "Professional chef specializing in Italian cuisine",
        )
        assert score < 0.2

    def test_empty_first_document(self):
        score = compute_similarity("", "Python developer")
        assert score == 0.0

    def test_empty_second_document(self):
        score = compute_similarity("Python developer", "")
        assert score == 0.0

    def test_both_empty(self):
        score = compute_similarity("", "")
        assert score == 0.0

    def test_returns_float_between_zero_and_one(self):
        score = compute_similarity("Python React", "Java Spring")
        assert 0.0 <= score <= 1.0


class TestExtractKeywords:
    """Extract the most important keywords from a document using TF-IDF."""

    def test_extracts_relevant_keywords(self):
        text = "Python developer with experience in machine learning and data science"
        keywords = extract_keywords(text, top_n=5)
        assert len(keywords) <= 5
        assert all(isinstance(kw, str) for kw in keywords)
        # With single-doc TF-IDF, all non-stop words are equally important
        # Just verify we get meaningful words back, not stop words
        keywords_lower = [k.lower() for k in keywords]
        assert "python" in keywords_lower or "developer" in keywords_lower

    def test_respects_top_n(self):
        text = "Python Java Go Rust TypeScript React Vue Angular"
        keywords = extract_keywords(text, top_n=3)
        assert len(keywords) == 3

    def test_empty_text_returns_empty(self):
        keywords = extract_keywords("", top_n=5)
        assert keywords == []

    def test_single_word(self):
        keywords = extract_keywords("Python", top_n=5)
        assert len(keywords) == 1
        assert keywords[0].lower() == "python"

    def test_filters_common_words(self):
        text = "the and is a an in on for with to of"
        keywords = extract_keywords(text, top_n=5)
        # Common English stop words should not appear as keywords
        assert len(keywords) == 0
