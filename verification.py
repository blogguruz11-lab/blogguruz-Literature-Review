"""Check that an excerpt really appears in the text that was sent to the model.

This confirms the words are on the page. It does not confirm that the statement
built on the excerpt is a correct reading of it. A person still has to judge that.
"""
from dataclasses import dataclass

from . import config
from .text_utils import match_key

VERIFIED = "verified"        # excerpt found on the cited page
WRONG_PAGE = "wrong_page"    # found, but not on the cited page
NOT_FOUND = "not_found"      # not found anywhere in the text that was sent
TOO_SHORT = "too_short"      # too short to check reliably


@dataclass(frozen=True)
class Verification:
    status: str
    found_on: tuple[int, ...] = ()


class PageIndex:
    def __init__(self, page_texts: dict[int, str]):
        self._keys = {index: match_key(text) for index, text in page_texts.items()}

    def verify(self, excerpt: str, cited_page: int) -> Verification:
        key = match_key(excerpt)
        if len(key) < config.MIN_EXCERPT_KEY_CHARS:
            return Verification(TOO_SHORT)
        found = tuple(i for i, page_key in self._keys.items() if key in page_key)
        if cited_page in found:
            return Verification(VERIFIED, found)
        if found:
            return Verification(WRONG_PAGE, found)
        return Verification(NOT_FOUND)
