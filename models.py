"""Plain data containers shared by the parser and the interface."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PageText:
    index: int            # 1-based position of the page in the PDF file
    label: str | None     # printed page number, only when the PDF defines page labels
    text: str
    char_count: int
    low_text: bool        # True when the page has very little extractable text


@dataclass(frozen=True)
class PDFMetadata:
    """Taken from the PDF file's own metadata. Often empty or wrong, so treat as a hint."""
    title: str | None = None
    author: str | None = None
    subject: str | None = None
    created: str | None = None


@dataclass
class ParsedPDF:
    file_name: str
    size_bytes: int
    sha256: str
    page_count: int
    pages: list[PageText]
    metadata: PDFMetadata
    doi_candidate: str | None = None   # found in the first pages; not verified
    warnings: list[str] = field(default_factory=list)

    @property
    def word_count(self) -> int:
        return sum(len(p.text.split()) for p in self.pages)

    @property
    def low_text_pages(self) -> list[int]:
        return [p.index for p in self.pages if p.low_text]
