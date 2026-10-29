"""Central configuration: limits, thresholds, and model settings."""

# ---------------------------------------------------------------------------
# Upload limits
# ---------------------------------------------------------------------------
MAX_FILE_MB = 50
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024
MAX_PAGES = 300
MAX_FILES = 10

# ---------------------------------------------------------------------------
# PDF text quality thresholds
# ---------------------------------------------------------------------------
MIN_CHARS_PER_PAGE = 50
MIN_TOTAL_CHARS = 100
MAX_METADATA_CHARS = 300

# ---------------------------------------------------------------------------
# Paper preparation
# ---------------------------------------------------------------------------
# Fraction of the document after which to start looking for the references
# section. 0.5 means only pages in the second half are searched.
REFERENCES_SEARCH_FROM = 0.5

# Rough heuristic used to estimate token counts from character counts.
CHARS_PER_TOKEN_ESTIMATE = 4

# Maximum characters of a single paper sent to the model.
MAX_CHARS_PER_PAPER = 100_000

# ---------------------------------------------------------------------------
# Model and extraction
# ---------------------------------------------------------------------------
MODEL_NAME = "claude-sonnet-4-5"
MAX_OUTPUT_TOKENS = 4000

MAX_FINDINGS = 8
MAX_LIMITATIONS = 5

MAX_RESEARCH_QUESTION_CHARS = 2000
API_TIMEOUT_SECONDS = 120

# Bump whenever the extraction prompt or output schema changes, so cached
# results from older versions are not reused.
EXTRACTION_VERSION = "1"
MIN_EXCERPT_KEY_CHARS = 20
