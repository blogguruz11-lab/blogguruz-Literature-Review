"""Session-cache keys. Every setting that changes the result is part of the key."""
import hashlib
import re


def extraction_cache_key(file_sha256: str, model: str, version: str,
                         research_question: str | None, max_chars: int) -> str:
    question = re.sub(r"\s+", " ", research_question or "").strip().casefold()
    raw = "\x1f".join([file_sha256, model, version, question, str(max_chars)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
