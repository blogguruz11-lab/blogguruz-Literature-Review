"""Errors raised while reading a PDF.

Each error carries a plain-language message that is safe to show to the user.
It never contains text from the document itself.
"""


class PDFProcessingError(Exception):
    default_message = "This file could not be processed."

    def __init__(self, message: str | None = None):
        self.user_message = message or self.default_message
        super().__init__(self.user_message)


class EmptyFileError(PDFProcessingError):
    default_message = "The file is empty (0 bytes)."


class FileTooLargeError(PDFProcessingError):
    default_message = "The file is larger than the allowed size."


class InvalidPDFError(PDFProcessingError):
    default_message = (
        "This does not look like a valid PDF. It may be damaged or a different file type "
        "renamed to .pdf."
    )


class PasswordProtectedError(PDFProcessingError):
    default_message = (
        "This PDF is password-protected. Version 1 cannot open it. Remove the password "
        "and upload it again."
    )


class UnsupportedPDFError(PDFProcessingError):
    default_message = "This PDF uses a feature the app cannot read."


class NoPagesError(PDFProcessingError):
    default_message = "The PDF has no pages."


class TooManyPagesError(PDFProcessingError):
    default_message = "The PDF has more pages than the allowed limit."


class NoTextError(PDFProcessingError):
    default_message = (
        "No readable text was found. This PDF is probably scanned or image-only. "
        "Version 1 does not do OCR (text recognition from images)."
    )
