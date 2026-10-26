"""Limits and thresholds. Keep maxUploadSize in .streamlit/config.toml in step with MAX_FILE_MB."""

MAX_FILE_MB = 50
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
MAX_PAGES = 300
MAX_FILES = 10

# A page with fewer characters than this is flagged as "little text".
MIN_CHARS_PER_PAGE = 50
# If the whole document has fewer characters than this, we treat it as having no text layer.
MIN_TOTAL_CHARS = 100

# Metadata strings longer than this are cut, so odd files cannot flood the interface.
MAX_METADATA_CHARS = 300
