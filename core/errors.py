
"""Errors raised while reading a PDF."""


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
    default_message = "This does not look like a valid PDF."


class PasswordProtectedError(PDFProcessingError):
    default_message = "This PDF is password-protected."


class UnsupportedPDFError(PDFProcessingError):
    default_message = "This PDF uses a feature the app cannot read."


class NoPagesError(PDFProcessingError):
    default_message = "The PDF has no pages."


class TooManyPagesError(PDFProcessingError):
    default_message = "The PDF has more pages than the allowed limit."


class NoTextError(PDFProcessingError):
    default_message = "No readable text was found in this PDF."

