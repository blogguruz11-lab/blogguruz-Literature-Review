
"""Read a PDF from memory, page by page.

Nothing is written to disk and nothing from the document is logged.
All reading goes through parse_pdf(), so the PDF library can be swapped later
without touching the rest of the app.
"""
import hashlib
import io

from pypdf import PasswordType, PdfReader
from pypdf.errors import DependencyError

from . import config
from .errors import (
    EmptyFileError, FileTooLargeError, InvalidPDFError, NoPagesError, NoTextError,
    PasswordProtectedError, TooManyPagesError, UnsupportedPDFError,
)
from .models import PageText, ParsedPDF, PDFMetadata
from .text_utils import clean_page_text, find_doi


def _short(value) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value[: config.MAX_METADATA_CHARS] if value else None


def _read_metadata(reader: PdfReader) -> PDFMetadata:
    try:
        meta = reader.metadata
        if not meta:
            return PDFMetadata()
        try:
            created = meta.creation_date.date().isoformat() if meta.creation_date else None
        except Exception:  # malformed dates are common
            created = None
        return PDFMetadata(
            title=_short(meta.title), author=_short(meta.author),
            subject=_short(meta.subject), created=created,
        )
    except Exception:
        return PDFMetadata()


def _read_labels(reader: PdfReader, count: int) -> list[str | None]:
    """Printed page labels. pypdf returns 1, 2, 3... when a PDF defines none, so a label
    equal to the plain position is treated as 'no label'."""
    try:
        labels = list(reader.page_labels)
    except Exception:
        return [None] * count
    result: list[str | None] = []
    for i in range(count):
        label = labels[i] if i < len(labels) else None
        result.append(None if label in (None, "", str(i + 1)) else str(label))
    return result


def _open_reader(data: bytes) -> PdfReader:
    try:
        reader = PdfReader(io.BytesIO(data))
    except Exception:  # any parser failure means "not a readable PDF"
        raise InvalidPDFError() from None

    if reader.is_encrypted:
        try:
            result = reader.decrypt("")
        except DependencyError:
            raise UnsupportedPDFError(
                "This PDF is encrypted with a method that needs the 'cryptography' package. "
                "Install the requirements and try again."
            ) from None
        except Exception:
            raise PasswordProtectedError() from None
        if result == PasswordType.NOT_DECRYPTED:
            raise PasswordProtectedError()
    return reader


def parse_pdf(
    data: bytes,
    file_name: str = "uploaded.pdf",
    *,
    max_bytes: int = config.MAX_FILE_BYTES,
    max_pages: int = config.MAX_PAGES,
) -> ParsedPDF:
    """Parse PDF bytes into a ParsedPDF, or raise a PDFProcessingError."""
    if not data:
        raise EmptyFileError()
    if len(data) > max_bytes:
        raise FileTooLargeError()
    if b"%PDF-" not in data[:1024]:
        raise InvalidPDFError()

    reader = _open_reader(data)

    try:
        page_count = len(reader.pages)
    except Exception:
        raise InvalidPDFError() from None
    if page_count == 0:
        raise NoPagesError()
    if page_count > max_pages:
        raise TooManyPagesError()

    labels = _read_labels(reader, page_count)
    pages: list[PageText] = []
    unreadable: list[int] = []

    for i in range(page_count):
        try:
            text = clean_page_text(reader.pages[i].extract_text() or "")
        except Exception:
            text = ""
            unreadable.append(i + 1)
        chars = len(text)
        pages.append(PageText(
            index=i + 1, label=labels[i], text=text,
            char_count=chars, low_text=chars < config.MIN_CHARS_PER_PAGE,
        ))

    if sum(p.char_count for p in pages) < config.MIN_TOTAL_CHARS:
        raise NoTextError()

    warnings: list[str] = []
    if unreadable:
        warnings.append(f"Could not read page(s): {', '.join(map(str, unreadable))}.")
    low = [p.index for p in pages if p.low_text and p.index not in unreadable]
    if low:
        shown = ", ".join(map(str, low[:15])) + (" …" if len(low) > 15 else "")
        warnings.append(
            f"Page(s) {shown} have little or no text (blank, scanned or image-only?). "
            "Check these pages in the original PDF."
        )

    first_pages_text = "\n".join(p.text for p in pages[:2])
    return ParsedPDF(
        file_name=file_name,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        page_count=page_count,
        pages=pages,
        metadata=_read_metadata(reader),
        doi_candidate=find_doi(first_pages_text),
        warnings=warnings,
    )
