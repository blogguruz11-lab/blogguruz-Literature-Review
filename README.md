# Literature review generator: Version 2

Upload research papers, then extract each paper's **research objective, methodology, findings and
limitations**. Every extracted item carries a **page number** and an **exact excerpt**, and the app
checks that the excerpt really appears on that page of the PDF.

Version 1 is a separate project (`litreview_app/`) and is not modified by this one.

## What Version 2 does

- Reads PDFs from memory, page by page, keeping page numbers (the Version 1 parser, copied unchanged).
- Optional research question (500 characters maximum). It only asks the AI to list the most relevant
  findings first. It does not filter anything.
- One Claude API call per paper. The reference list is removed first, so findings of cited works are
  not extracted as the paper's own.
- Each excerpt gets a label: **text verified**, **wrong page**, **not found** or **too short**.
  Items that fail the check are still shown, with a warning, so problems are never hidden.
- Missing information is shown as **"Not stated in the paper"**.
- Consent: nothing is sent until the user ticks the consent box and clicks **Extract evidence**.
- Size limit: at most 150,000 characters per paper. Larger papers are skipped with an explanation.
  The estimated request size is shown before anything is sent.
- Session-only cache keyed by file hash, model, extraction version, research question and size limit.

**Text verified is not proof of correctness.** It means the quoted words appear on that page. It does
not show that the AI's statement is a correct reading of them. A person must read each excerpt.

## Not in Version 2

Custom columns, comparing papers, review drafting, retraction checks, OCR, password-protected PDFs,
claim editing, Word export.

## Project layout

```
litreview_app_v2/
├── app.py                      Streamlit screens
├── requirements.txt            Runtime dependencies
├── requirements-dev.txt        Adds reportlab (tests only)
├── .gitignore                  Keeps secrets out of git
├── .streamlit/
│   ├── config.toml             Upload limit; usage statistics off
│   └── secrets.toml.example    Template for your API key
├── core/
│   ├── pdf_parser.py, models.py, errors.py, text_utils.py   Version 1 files, copied unchanged
│   ├── config.py               Limits and model name
│   ├── inputs.py               Cleaning of the research question; tag-breakout protection
│   ├── preparation.py          Removes the reference list; builds the text that is sent
│   ├── prompts.py              The extraction prompt
│   ├── llm.py                  The only code that calls the Claude API; safe error messages
│   ├── extractor.py            One call per paper; reads and validates the reply
│   ├── verification.py         Excerpt-on-page checks
│   ├── extraction_models.py    Result types
│   └── cache_keys.py           Session cache keys
├── tests/                      64 tests, all using a fake model client
├── README.md
└── LIVE_TEST_CHECKLIST.md      The five-paper test to run before trusting the tool
```

## Setup (Python 3.10 or newer)

```
cd litreview_app_v2
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## API key

Never put the key in source code or commit it.

- **Locally, option 1:** copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and edit it.
- **Locally, option 2:** set an environment variable, for example `export ANTHROPIC_API_KEY="..."`
  (Windows PowerShell: `$env:ANTHROPIC_API_KEY="..."`).
- **Streamlit Community Cloud:** add `ANTHROPIC_API_KEY` in the app's Secrets settings, not in the repo.

## Choosing the model

The default is `claude-sonnet-5-5`. On 28 October 2026 Anthropic's official models overview
(platform.claude.com/docs/en/models/overview) listed these API IDs: `claude-fable-5-1`,
`claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`. Names change, so re-check that page
before deploying. To change the model, set `LITREVIEW_MODEL` as a secret or environment variable.
`claude-haiku-5-5` is cheaper and fast, but do not switch to it until it passes the same five-paper
test as the default.

## Run

```
streamlit run app.py
```

## Run the tests

```
pip install -r requirements-dev.txt
python -m unittest discover -s tests -t . -v
```

## Deployment (Streamlit Community Cloud, summary)

1. Put the **contents** of this folder at the top level of a new GitHub repository, so `app.py` and
   `requirements.txt` sit in the repo root. Check that `.streamlit/secrets.toml` is not committed.
2. In Streamlit Community Cloud, create an app from the repository with `app.py` as the main file.
3. Choose Python 3.10 or newer in the app's advanced settings.
4. Add `ANTHROPIC_API_KEY` under Secrets.
5. Deploy, then run the live test checklist on the deployed app.

Streamlit's menus change, so follow its current documentation for exact clicks. A WordPress site can
link to the deployed app. It cannot run it.

## Cost

The app shows a rough input-size estimate (characters divided by four) before you click Extract.
It is an estimate, not a bill, and it does not include output tokens.

On 28 October 2026 the official models page listed Claude Sonnet 5.5 at $2 per million input tokens
and $10 per million output tokens. By that arithmetic the worst case for one paper is about
37,500 input tokens ($0.075) plus the 16,000-token output cap ($0.16), roughly $0.24. Typical papers
should cost less. Check the pricing page before relying on these figures.

## Privacy

What the code is designed to do:

- Parse PDFs from memory; open and write no files; use no `st.cache_*`.
- Keep results in `st.session_state` only. Results for a removed upload are dropped, and
  **Delete all session data** clears everything, including the consent tick.
- Log only an error type if something unexpected fails, never document text or file names.
- Show text that came from papers or the model with `st.text()`, never as Markdown or HTML.
- Never display the API key.

What the code cannot promise, so verify it:

- How Streamlit and your host handle uploads and logs.
- What Anthropic does with data sent to its API. Read their current terms for your account type
  and describe them accurately in your own privacy notice.

A simple check: upload a PDF containing a unique phrase, extract, press **Delete all session data**,
then search the machine and logs for the phrase.

## Known limits

- Two-column layouts may extract in mixed order. Tables and headings are not extracted.
- An excerpt that spans two pages cannot be verified, so the AI is told to quote from one page.
- The reference list is removed from the first "References", "Bibliography", "Works cited" or
  "Literature cited" heading found after 40% of the document. Appendices after it are dropped too.
  If no heading is found, all text is sent and the app says so.
- The model's replies are never trusted blindly. Malformed, truncated or unreadable replies fail
  visibly and save nothing.
- Scanned PDFs are rejected because there is no OCR.

## Testing status (be honest about it)

Done here:

- 64 automated tests pass using a fake model client. They cover malformed JSON, truncated replies,
  invented excerpts, wrong page numbers, missing fields, over-long papers, prompt injection in
  paper text, reference-list removal, cache keys and error messages.
- The app's logic ran end to end against a stand-in for Streamlit with a fake model.

**Not done, so Version 2 must not be called reliable yet:**

- No call to the real Claude API has been made. The `anthropic` package was not installed in the
  build environment, so `core/llm.py` has never run against the real SDK.
- The app has not been run in real Streamlit or on a host.
- It has not been tried on real research papers.

Two things to watch in the first live runs: (1) this model uses adaptive thinking by default, which
may use part of the 16,000-token output limit. If you see "reply was cut off" messages, raise
`MAX_OUTPUT_TOKENS` in `core/config.py`. (2) No temperature or other sampling setting is passed.

Run `LIVE_TEST_CHECKLIST.md` on five real papers before relying on any output.
