"""Text helpers. normalize() and match_key() are not used by Version 1's screens yet;
they are here for the later excerpt-verification step."""
import re
import unicodedata

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_DOI = re.compile(r"\b(10\.\d{4,9}/[^\s\"'<>]+)", re.IGNORECASE)
_DOI_TRAILING = ".,;:)]}"


def clean_page_text(text: str) -> str:
    """Tidy extracted text for display: unify newlines, drop control characters,
    trim trailing spaces and collapse long runs of blank lines. Words are not changed."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_CHARS.sub("", text)
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize(text: str) -> str:
    """Readable normalised text: ligatures, curly quotes, dashes and line-break hyphens."""
    text = unicodedata.normalize("NFKC", text).replace("\u00ad", "")
    text = text.translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2013": "-", "\u2014": "-",
    }))
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def match_key(text: str) -> str:
    """Loose comparison key: lower-case letters and digits only."""
    text = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in text if ch.isalnum())


def find_doi(text: str) -> str | None:
    """Return the first DOI-looking string in the text, or None. Not verified."""
    for match in _DOI.finditer(text):
        doi = match.group(1).rstrip(_DOI_TRAILING)
        if "/" in doi and len(doi) > 7:
            return doi
    return None
