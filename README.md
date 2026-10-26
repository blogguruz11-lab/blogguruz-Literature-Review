# Literature review generator: Version 1

Upload research-paper PDFs, extract the text page by page (keeping page numbers), and review
the result. This is the foundation for later versions: AI extraction, claim IDs, evidence-linked
writing, citation checking, comparison tables and Word export.

## Project layout

```
litreview_app/
├── app.py                  Streamlit interface only (no parsing logic)
├── requirements.txt        What the app needs
├── requirements-dev.txt    Adds reportlab, used only by the tests
├── .streamlit/config.toml  Upload limit; usage statistics off
├── core/
│   ├── config.py           Limits and thresholds
│   ├── errors.py           One error type per failure, with a user-safe message
│   ├── models.py           PageText, PDFMetadata, ParsedPDF
│   ├── text_utils.py       Text cleaning, DOI finder, matching helpers
│   └── pdf_parser.py       parse_pdf(): the only place that touches the PDF library
└── tests/                  Unit tests (standard library unittest)
```

## Setup (Python 3.10 or newer)

macOS / Linux:

```
cd litreview_app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```
cd litreview_app
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

```
streamlit run app.py
```

Streamlit prints a local address (usually http://localhost:8501). Open it, upload PDFs, pick
a page to read its extracted text.

## Run the tests

```
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v
```

## What Version 1 does

- Accepts up to 10 PDFs (50 MB and 300 pages each).
- Extracts text per page and keeps both the PDF page number and the printed page label when
  the PDF defines one.
- Shows pages, words, size, PDF metadata, a DOI found in the first pages, and a file
  fingerprint. It reports exact duplicate uploads.
- Gives a plain-language message for: empty files, non-PDFs, damaged files, password-protected
  PDFs, PDFs with no text layer (scanned or image-only), too many pages, and files that are
  too large. Blank or image-only pages inside an otherwise readable PDF are flagged.

## What Version 1 does not do

No AI calls, no OCR, no password entry, no table or heading extraction, no citation features,
no export. Two-column papers may come out in a mixed reading order, because `pypdf` does not
understand columns. Judge this on your own papers.

## Privacy

What the code is designed to do:

- Read uploads from memory and parse from memory. No file is opened or written by the app.
- Keep results only in `st.session_state`. No `st.cache_*`.
- Drop a paper's data when its upload is removed. "Delete all session data" clears everything.
- Log only an error type if something unexpected fails, never document text or file names.

What the code cannot promise, so verify before relying on it:

- How Streamlit and your hosting provider handle uploads and logs internally.
- Whether anything lands on disk or in logs in your deployment.

A simple check: upload a PDF containing a unique phrase, use the app, press "Delete all session
data", then search the machine for the phrase, for example
`grep -r "your unique phrase" /tmp ~ 2>/dev/null` on macOS or Linux, and check the terminal
output and any log files.

## Where later features plug in

| Feature | Where it goes |
|---|---|
| AI extraction and claim IDs | new `core/extractor.py`, `core/claims.py` using `ParsedPDF.pages` |
| Excerpt and citation checking | `core/checker.py`, using `text_utils.match_key` |
| Writer | `core/writer.py` |
| Comparison table, Word export | `core/export.py` |
| New screens | `app.py`, calling `core` only |
