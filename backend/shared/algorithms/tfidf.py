"""TF-IDF keyword importance and document similarity.

Uses scikit-learn's TfidfVectorizer for lightweight, offline text analysis.
No ML models needed — pure statistics.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def compute_similarity(document_a: str, document_b: str) -> float:
    """Score similarity between two texts using TF-IDF + cosine similarity.

    Returns float 0.0 (unrelated) to 1.0 (identical).
    """
    if not document_a.strip() or not document_b.strip():
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english")
    tfidf_matrix = vectorizer.fit_transform([document_a, document_b])

    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])
    return float(similarity[0][0])


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract the most important keywords from text using TF-IDF scores.

    Returns up to top_n keywords sorted by importance.
    """
    if not text.strip():
        return []

    vectorizer = TfidfVectorizer(stop_words="english")

    try:
        tfidf_matrix = vectorizer.fit_transform([text])
    except ValueError:
        # All words are stop words or text is empty after preprocessing
        return []

    feature_names = vectorizer.get_feature_names_out()
    scores = tfidf_matrix.toarray()[0]

    # Pair keywords with their scores and sort by importance
    keyword_scores = sorted(
        zip(feature_names, scores),
        key=lambda pair: pair[1],
        reverse=True,
    )

    # Filter out zero-score keywords and limit to top_n
    keywords = [
        str(keyword) for keyword, score in keyword_scores
        if score > 0
    ]

    return keywords[:top_n]
