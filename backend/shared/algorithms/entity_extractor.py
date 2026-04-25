"""Entity extraction from text using spaCy.

Extracts named entities (organizations, dates, locations) and technical skills
from job postings and experience descriptions.

Requires: pip install spacy && python -m spacy download en_core_web_md
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import spacy

DEFAULT_MODEL = "en_core_web_md"

_nlp: spacy.Language | None = None
_is_available: bool | None = None

# Common tech skills that spaCy's NER won't catch (not named entities)
KNOWN_SKILLS_PATTERN = re.compile(
    r"\b("
    r"Python|Java|JavaScript|TypeScript|Go|Rust|Ruby|PHP|Swift|Kotlin|"
    r"C\+\+|C#|SQL|HTML|CSS|Bash|Shell|Scala|Perl|R|Dart|Lua|"
    r"React|Angular|Vue|Svelte|Next\.?js|Nuxt|Django|Flask|FastAPI|"
    r"Spring|Express|Rails|Laravel|ASP\.NET|"
    r"Docker|Kubernetes|AWS|GCP|Azure|Terraform|Ansible|"
    r"PostgreSQL|MySQL|MongoDB|Redis|SQLite|Elasticsearch|"
    r"Git|Linux|Nginx|GraphQL|REST|gRPC|Kafka|RabbitMQ|"
    r"TensorFlow|PyTorch|Pandas|NumPy|Scikit-learn|"
    r"Node\.?js|Webpack|Vite|Jest|Pytest|JUnit"
    r")\b",
    re.IGNORECASE,
)


def is_available() -> bool:
    """Check if spaCy and the required model are installed."""
    global _is_available
    if _is_available is not None:
        return _is_available

    try:
        import spacy
        spacy.load(DEFAULT_MODEL)
        _is_available = True
    except (ImportError, OSError):
        _is_available = False

    return _is_available


def _get_nlp() -> spacy.Language:
    """Lazy-load the spaCy model (singleton)."""
    global _nlp
    if _nlp is not None:
        return _nlp

    if not is_available():
        raise RuntimeError(
            f"spaCy or model '{DEFAULT_MODEL}' is not installed. "
            f"Install with: pip install spacy && python -m spacy download {DEFAULT_MODEL}"
        )

    import spacy

    _nlp = spacy.load(DEFAULT_MODEL)
    return _nlp


def extract_entities(text: str) -> list[dict]:
    """Extract named entities (ORG, DATE, GPE, PERSON, etc.) from text.

    Returns list of {text, label, start, end} dicts.
    """
    if not text.strip():
        return []

    nlp = _get_nlp()
    doc = nlp(text)

    return [
        {
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char,
        }
        for ent in doc.ents
    ]


def extract_skills_from_text(text: str) -> list[str]:
    """Extract technical skills from text using regex pattern matching.

    Uses a curated list of known tech skills. More reliable than NER
    for technical terms since spaCy doesn't classify "Python" as a skill.
    """
    if not text.strip():
        return []

    matches = KNOWN_SKILLS_PATTERN.findall(text)

    # Deduplicate while preserving order, case-insensitive
    seen = set()
    unique_skills = []
    for skill in matches:
        skill_lower = skill.lower()
        if skill_lower not in seen:
            seen.add(skill_lower)
            unique_skills.append(skill)

    return unique_skills
