"""Limits and settings. V1 values are unchanged; the V2 block is new."""
import os

# ---- V1 (unchanged) ----
MAX_FILE_MB = 50
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
MAX_PAGES = 300
MAX_FILES = 10
MIN_CHARS_PER_PAGE = 50
MIN_TOTAL_CHARS = 100
MAX_METADATA_CHARS = 300

# ---- V2 ----
# Confirm the current model name in Anthropic's documentation before deploying.
MODEL_NAME = os.environ.get("LITREVIEW_MODEL", "claude-sonnet-5-5")
EXTRACTION_VERSION = "2.0"          # change when the prompt or schema changes; busts the cache

MAX_CHARS_PER_PAPER = 150_000       # hard limit on text sent per paper (about 37k tokens)
MAX_OUTPUT_TOKENS = 16_000     # adaptive thinking may share this budget; see README
API_TIMEOUT_SECONDS = 120
CHARS_PER_TOKEN_ESTIMATE = 4        # rough English average; used only for estimates

MAX_RESEARCH_QUESTION_CHARS = 500
MAX_FINDINGS = 8
MAX_LIMITATIONS = 6
MAX_ITEM_TEXT_CHARS = 1_000
MAX_EXCERPT_CHARS = 1_000
MIN_EXCERPT_KEY_CHARS = 20          # letters and digits an excerpt needs to be checkable

# The reference list is only searched for after this fraction of the document.
REFERENCES_SEARCH_FROM = 0.4
