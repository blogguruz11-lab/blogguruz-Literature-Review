"""Decide exactly which text is sent to the model, and keep a record of it.

The same text is used later to check excerpts, so a verified excerpt is always
something the model was actually given.
"""
import re
from dataclasses import dataclass

from . import config
from .inputs import neutralise_markers
from .models import ParsedPDF

_REFERENCES_HEADING = re.compile(
    r"(?im)^[ \t]*(?:\d+\.?[ \t]*)?(references|bibliography|works cited|literature cited)[ \t]*$"
)


@dataclass(frozen=True)
class PreparedPaper:
    pages: tuple[tuple[int, str], ...]       # (PDF page number, text that is sent)
    references_start_page: int | None        # None when no reference heading was found

    @property
    def char_count(self) -> int:
        return sum(len(text) for _, text in self.pages)

    def page_texts(self) -> dict[int, str]:
        return dict(self.pages)

    def as_prompt_text(self) -> str:
        return "\n\n".join(f"[[page {i}]]\n{t}" for i, t in self.pages if t.strip())

    @property
    def reference_note(self) -> str:
        if self.references_start_page is None:
            return "No reference-list heading was found, so all of the text was used."
        return (f"The reference list was removed from PDF page {self.references_start_page} "
                "onward, so findings of cited works are not extracted.")


def prepare_paper(parsed: ParsedPDF) -> PreparedPaper:
    total = parsed.page_count
    ref_page = ref_pos = None
    for page in parsed.pages:
        if (page.index - 1) / total < config.REFERENCES_SEARCH_FROM:
            continue
        match = _REFERENCES_HEADING.search(page.text)
        if match:
            ref_page, ref_pos = page.index, match.start()
            break

    pages = []
    for page in parsed.pages:
        if ref_page is not None and page.index > ref_page:
            break
        text = page.text[:ref_pos] if page.index == ref_page else page.text
        pages.append((page.index, neutralise_markers(text).strip()))
    return PreparedPaper(pages=tuple(pages), references_start_page=ref_page)
