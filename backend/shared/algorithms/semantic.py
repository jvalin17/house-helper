"""Sentence-level semantic similarity using Sentence Transformers.

Handles phrases like "distributed systems" ≈ "systems at scale" that
word-level approaches (TF-IDF, spaCy word vectors) miss.

Requires: pip install sentence-transformers (optional dependency).
Falls back gracefully if not installed (e.g., Python 3.14).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None
_is_available: bool | None = None


def is_available() -> bool:
    """Check if sentence-transformers is installed and a model can load."""
    global _is_available
    if _is_available is not None:
        return _is_available

    try:
        import sentence_transformers  # noqa: F401
        _is_available = True
    except ImportError:
        _is_available = False

    return _is_available


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (singleton)."""
    global _model
    if _model is not None:
        return _model

    if not is_available():
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Install with: pip install sentence-transformers"
        )

    from sentence_transformers import SentenceTransformer

    _model = SentenceTransformer(DEFAULT_MODEL_NAME)
    return _model


def compute_semantic_similarity(text_a: str, text_b: str) -> float:
    """Score semantic similarity between two texts.

    Returns float 0.0 (unrelated) to 1.0 (identical meaning).
    """
    if not text_a.strip() or not text_b.strip():
        return 0.0

    model = _get_model()
    embeddings = model.encode([text_a, text_b], normalize_embeddings=True)

    # Cosine similarity of normalized vectors = dot product
    similarity = float(embeddings[0] @ embeddings[1])
    return similarity


def compute_batch_similarity(
    query: str, candidates: list[str]
) -> list[dict]:
    """Score one query against multiple candidates efficiently.

    Returns list of {text, score} dicts sorted by score descending.
    """
    if not candidates:
        return []

    if not query.strip():
        return [{"text": c, "score": 0.0} for c in candidates]

    model = _get_model()
    query_embedding = model.encode([query], normalize_embeddings=True)[0]
    candidate_embeddings = model.encode(candidates, normalize_embeddings=True)

    results = []
    for candidate_text, candidate_embedding in zip(candidates, candidate_embeddings):
        score = float(query_embedding @ candidate_embedding)
        results.append({"text": candidate_text, "score": score})

    results.sort(key=lambda r: r["score"], reverse=True)
    return results
