"""TF-IDF keyword importance and document similarity.

Pure Python implementation — no scipy, numpy, or sklearn needed.
Drops 182MB of dependencies with identical accuracy for our use case.
"""

import math
import re
from collections import Counter

# Common English stop words
STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "had", "has", "have", "he", "her", "his", "how", "i", "if", "in", "into",
    "is", "it", "its", "just", "me", "my", "no", "not", "of", "on", "or",
    "our", "out", "own", "s", "so", "some", "such", "t", "than", "that", "the",
    "their", "them", "then", "there", "these", "they", "this", "those", "through",
    "to", "too", "under", "up", "very", "was", "we", "were", "what", "when",
    "where", "which", "while", "who", "whom", "why", "will", "with", "would",
    "you", "your", "been", "being", "do", "does", "did", "doing", "can", "could",
    "should", "shall", "may", "might", "must", "about", "above", "after", "again",
    "all", "am", "any", "because", "before", "below", "between", "both", "d",
    "each", "few", "further", "here", "itself", "ll", "m", "more", "most", "nor",
    "off", "once", "only", "other", "over", "re", "same", "she", "ve", "during",
})


def _tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words, excluding stop words."""
    words = re.findall(r"[a-zA-Z]{2,}", text.lower())
    return [w for w in words if w not in STOP_WORDS]


def _compute_tf(tokens: list[str]) -> dict[str, float]:
    """Compute term frequency for a list of tokens."""
    counts = Counter(tokens)
    total = len(tokens)
    if total == 0:
        return {}
    return {word: count / total for word, count in counts.items()}


def _compute_idf(documents: list[list[str]]) -> dict[str, float]:
    """Compute inverse document frequency across documents."""
    num_docs = len(documents)
    if num_docs == 0:
        return {}

    doc_freq: dict[str, int] = {}
    for tokens in documents:
        unique = set(tokens)
        for word in unique:
            doc_freq[word] = doc_freq.get(word, 0) + 1

    return {
        word: math.log((num_docs + 1) / (freq + 1)) + 1
        for word, freq in doc_freq.items()
    }


def _cosine_sim(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    common_keys = set(vec_a.keys()) & set(vec_b.keys())
    if not common_keys:
        return 0.0

    dot = sum(vec_a[k] * vec_b[k] for k in common_keys)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def compute_similarity(document_a: str, document_b: str) -> float:
    """Score similarity between two texts using TF-IDF + cosine similarity.

    Returns float 0.0 (unrelated) to 1.0 (identical).
    """
    if not document_a.strip() or not document_b.strip():
        return 0.0

    tokens_a = _tokenize(document_a)
    tokens_b = _tokenize(document_b)

    if not tokens_a or not tokens_b:
        return 0.0

    idf = _compute_idf([tokens_a, tokens_b])
    tf_a = _compute_tf(tokens_a)
    tf_b = _compute_tf(tokens_b)

    tfidf_a = {word: tf * idf.get(word, 0) for word, tf in tf_a.items()}
    tfidf_b = {word: tf * idf.get(word, 0) for word, tf in tf_b.items()}

    return _cosine_sim(tfidf_a, tfidf_b)


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Extract the most important keywords from text using TF-IDF scores.

    Returns up to top_n keywords sorted by importance.
    """
    if not text.strip():
        return []

    tokens = _tokenize(text)
    if not tokens:
        return []

    tf = _compute_tf(tokens)
    # With single document, IDF is uniform — TF alone determines importance
    # Sort by frequency (most frequent non-stop words are most important)
    sorted_words = sorted(tf.items(), key=lambda pair: pair[1], reverse=True)

    return [word for word, _ in sorted_words[:top_n]]
