"""Cleaning of text that goes into the prompt."""
import re

from . import config

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_OUR_TAGS = re.compile(r"<(/?\s*(?:paper|research_question)\b)", re.IGNORECASE)
_PAGE_MARKER = re.compile(r"\[\[\s*page", re.IGNORECASE)


def clean_research_question(text: str | None) -> str | None:
    """Trim, remove control characters, collapse spaces, cap the length. None if empty."""
    if not text:
        return None
    text = _CONTROL_CHARS.sub(" ", text)
    text = re.sub(r"\s+", " ", text).strip()[: config.MAX_RESEARCH_QUESTION_CHARS]
    return text or None


def neutralise_markers(text: str) -> str:
    """Stop paper text from closing our data tags or imitating our page markers."""
    text = _OUR_TAGS.sub(r"&lt;\1", text)
    return _PAGE_MARKER.sub("[ [page", text)
