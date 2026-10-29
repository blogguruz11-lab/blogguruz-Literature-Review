"""Version 2: extract objective, methodology, findings and limitations with page-level evidence.

Privacy and safety design (verify it yourself, see README):
- PDFs are parsed from memory. Nothing is written to disk, cached on disk or logged.
- Text is sent to Anthropic's API only after the user ticks the consent box AND clicks Extract.
- The API key comes from Streamlit secrets or an environment variable. It is never displayed.
- Results live only in st.session_state. No st.cache_* is used.
- Text that came from papers or the model is shown with st.text(), never as Markdown or HTML.
"""
import logging
import os

import streamlit as st

from core import config
from core.cache_keys import extraction_cache_key
from core.errors import PDFProcessingError
from core.extraction_models import FAILED, SKIPPED, EvidenceItem, ExtractionResult
from core.extractor import Extractor, prepare_request, size_limit_result
from core.inputs import clean_research_question
from core.llm import LLMError
from core.gemini_llm import GeminiLLM
from core.pdf_parser import parse_pdf
from core.verification import NOT_FOUND, TOO_SHORT, VERIFIED, WRONG_PAGE

logger = logging.getLogger("litreview")
st.set_page_config(page_title="Literature review generator", layout="wide")

CONSENT_NOTICE = (
    "When you click Extract, the text of the selected papers (without their reference lists) "
    "and your research question, if any, are sent to Google's Gemini API to be analysed. "
    "Do not use confidential or unpublished papers unless Google's current data-handling and "
    "retention terms for your type of API access are acceptable to you and to the paper's owners."
)
CHECK_CAVEAT = (
    "“Text verified” means the quoted words were found on that page of the PDF. It does not show "
    "that the AI's statement is a correct reading of them. Read each excerpt yourself."
)


# ---------- settings and secrets ----------

def get_secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
    except Exception:   # no secrets file is normal on a local machine
        value = None
    return value or os.environ.get(name)


def get_model() -> str:
    return get_secret("LITREVIEW_MODEL") or config.MODEL_NAME


# ---------- state ----------

def init_state() -> None:
    st.session_state.setdefault("results", {})        # upload id -> parse result
    st.session_state.setdefault("extractions", {})    # cache key -> ExtractionResult
    st.session_state.setdefault("uploader_key", 0)    # bumping this resets uploader, question, consent


def clear_everything() -> None:
    st.session_state["results"].clear()
    st.session_state["extractions"].clear()
    st.session_state["uploader_key"] += 1


# ---------- reading uploads (as in Version 1) ----------

def upload_id(uploaded) -> str:
    return getattr(uploaded, "file_id", None) or f"{uploaded.name}:{uploaded.size}"


def read_one(uploaded) -> dict:
    data = uploaded.getvalue()
    try:
        return {"name": uploaded.name, "parsed": parse_pdf(data, uploaded.name), "error": None}
    except PDFProcessingError as exc:
        return {"name": uploaded.name, "parsed": None, "error": exc.user_message}
    except Exception as exc:  # last resort. Log only the type: details may contain content.
        logger.error("Unexpected error while reading a PDF: %s", type(exc).__name__)
        return {"name": uploaded.name, "parsed": None,
                "error": "Something went wrong while reading this file."}
    finally:
        del data


def process_uploads(files) -> list[tuple[str, dict]]:
    results = st.session_state["results"]
    current = []
    for uploaded in list(files)[: config.MAX_FILES]:
        fid = upload_id(uploaded)
        current.append(fid)
        if fid not in results:
            with st.spinner(f"Reading {uploaded.name}…"):
                results[fid] = read_one(uploaded)
    for stale in [fid for fid in results if fid not in current]:
        del results[stale]
    # Drop extraction results whose paper is no longer uploaded.
    live = {r["parsed"].sha256 for r in results.values() if r["parsed"]}
    extractions = st.session_state["extractions"]
    for key in [k for k, v in extractions.items() if v.file_sha256 not in live]:
        del extractions[key]
    return [(fid, results[fid]) for fid in current]


# ---------- sidebar ----------

def render_sidebar() -> None:
    with st.sidebar:
        st.header("Your data")
        st.write("PDFs are read into memory and parsed from memory. This app does not save "
                 "uploads to disk or write document text to its logs.")
        st.write("Paper text is sent to Anthropic's API only after you agree and click Extract.")
        st.caption("Your hosting setup and Streamlit may still record technical details such as "
                   "IP addresses and request times. Closing the tab does not instantly free "
                   "server memory, so use the button below when you are done.")
        if st.button("Delete all session data", type="primary"):
            clear_everything()
            
        st.divider()
        st.subheader("Limits")
        st.write(f"Up to {config.MAX_FILES} files, {config.MAX_FILE_MB} MB and {config.MAX_PAGES} "
                 f"pages each. At most {config.MAX_CHARS_PER_PAPER:,} characters of text are "
                 "sent per paper.")
        st.subheader("Not in Version 2")
        st.write("Custom columns, comparing papers, review drafting, retraction checks, OCR, "
                 "Word export.")


# ---------- showing a paper ----------

def page_label(parsed, page: int) -> str:
    match = next((p for p in parsed.pages if p.index == page), None)
    if match and match.label:
        return f"PDF page {page} (printed {match.label})"
    return f"PDF page {page}"


def render_pdf_text(fid: str, parsed) -> None:
    def describe(index: int) -> str:
        page = parsed.pages[index - 1]
        parts = [f"PDF page {page.index}"]
        if page.label:
            parts.append(f"printed {page.label}")
        parts.append(f"{page.char_count:,} characters")
        if page.low_text:
            parts.append("little text")
        return " · ".join(parts)

    choice = st.selectbox("Page", [p.index for p in parsed.pages], format_func=describe,
                          key=f"page-{fid}")
    st.text_area("Extracted text", value=parsed.pages[choice - 1].text, height=300,
                 disabled=True, key=f"text-{fid}-{choice}", label_visibility="collapsed")


def render_item(parsed, item: EvidenceItem) -> None:
    st.text(item.text)
    st.caption(f"Cited: {page_label(parsed, item.page)}")
    st.text(f"Excerpt: “{item.excerpt}”")
    if item.status == VERIFIED:
        st.caption("Text verified: these exact words appear on the cited page.")
    elif item.status == WRONG_PAGE:
        pages = ", ".join(page_label(parsed, p) for p in item.found_on)
        st.warning(f"Wrong page: these words appear on {pages}, not on the cited page.")
    elif item.status == NOT_FOUND:
        st.warning("Not found: these words do not appear in the text sent to the AI. "
                   "Treat this statement as unverified.")
    elif item.status == TOO_SHORT:
        st.warning("Too short: the excerpt is too short to check reliably.")


def render_section(parsed, title: str, items: list[EvidenceItem], missing_text: str) -> None:
    st.markdown(f"**{title}**")
    if not items:
        st.text(missing_text)
    for item in items:
        render_item(parsed, item)
    st.write("")



def render_extraction(parsed, result: ExtractionResult) -> None:
    if result.status == FAILED:
        st.error(result.message)
        return

    if result.status == SKIPPED:
        st.warning(result.message)
        return

    st.caption(f"Model: {result.model}. {result.reference_note}")
    if result.research_question:
        st.caption(
            "Research question used: "
            + result.research_question[:80]
            + ("…" if len(result.research_question) > 80 else "")
        )

    st.info(CHECK_CAVEAT)
    for issue in result.issues:
        st.warning(issue)
    absent = "Not stated in the paper"
    render_section(parsed, "Research objective", [result.objective] if result.objective else [], absent)
    render_section(parsed, "Methodology", [result.methodology] if result.methodology else [], absent)
    render_section(parsed, "Findings", result.findings, absent)
    render_section(parsed, "Limitations", result.limitations, absent)


def render_paper(fid: str, entry: dict, result: ExtractionResult | None) -> None:
    st.subheader(entry["name"])
    if entry["error"]:
        st.error(entry["error"])
        return
    parsed = entry["parsed"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Pages", parsed.page_count)
    c2.metric("Words", f"{parsed.word_count:,}")
    c3.metric("Pages with little text", len(parsed.low_text_pages))
    for warning in parsed.warnings:
        st.warning(warning)
    if result is None:
        st.info("Not extracted yet.")
    else:
        render_extraction(parsed, result)
    with st.expander("Check the text extracted from the PDF"):
        meta = parsed.metadata
        st.text(f"Title in PDF metadata: {meta.title or 'not set'}\n"
                f"Author in PDF metadata: {meta.author or 'not set'}\n"
                f"DOI found in first pages: {parsed.doi_candidate or 'none found'}\n"
                f"File fingerprint (first 12): {parsed.sha256[:12]}")
        st.caption("Metadata and the DOI are hints only and are not verified.")
        render_pdf_text(fid, parsed)


# ---------- extraction panel ----------

def render_extraction_panel(readable: list[tuple[str, dict]], rq: str | None) -> None:
    st.subheader("Extract evidence")
    model = get_model()
    api_key = get_secret("GEMINI_API_KEY")
    extractions = st.session_state["extractions"]
    pending, seen = [], set()
    for fid, entry in readable:
        parsed = entry["parsed"]
        request = prepare_request(parsed, rq)
        key = extraction_cache_key(parsed.sha256, model, config.EXTRACTION_VERSION,
                                   request.research_question, config.MAX_CHARS_PER_PAPER)
        too_long = size_limit_result(request, parsed, model)
        if too_long:
            extractions[key] = too_long       # no API call, no cost
            continue
        existing = extractions.get(key)
        if (existing is None or existing.status == FAILED) and key not in seen:
            seen.add(key)
            pending.append((key, entry, request))

    st.info(CONSENT_NOTICE)
    if not api_key:
        st.error(
    "No API key found. Add GEMINI_API_KEY to Streamlit secrets "
    "or set it as an environment variable. The key is never shown here."
)
    if pending:
        total = sum(r.estimated_input_tokens for _, _, r in pending)
        st.write(f"{len(pending)} paper(s) will be sent. Rough size estimate: about {total:,} "
                 "input tokens in total (an estimate, not a bill; the model also produces output "
                 "tokens). Check Anthropic's pricing page for current prices.")
        for _, entry, request in pending:
            st.text(f"{entry['name']}: about {request.estimated_input_tokens:,} input tokens")
    else:
        st.write("Nothing waiting to be extracted for the current papers and research question.")

    consent = st.checkbox(
        "I understand that this text will be sent to Google's Gemini API, and I agree.",
        key=f"consent-{st.session_state['uploader_key']}")
    if st.button("Extract evidence", type="primary",
                 disabled=not (consent and api_key and pending)):
      
        try:
            extractor = Extractor(
                GeminiLLM(
                    api_key,
                    model,
                    config.API_TIMEOUT_SECONDS
                )
            )
        except Exception as exc:
            st.error(f"Could not start Gemini: {type(exc).__name__}: {exc}")
            with st.expander("Technical details"):
                st.code(logging.exception if False else str(exc))
            return

        progress = st.progress(0.0)

        for n, (key, entry, _) in enumerate(pending, 1):
            try:
                with st.spinner(
                    f"Extracting {entry['name']} ({n} of {len(pending)})…"
                ):
                    result = extractor.extract(entry["parsed"], rq)
                    extractions[key] = result

                    if result.status == FAILED:
                        st.error(
                            f"Extraction failed for {entry['name']}: "
                            f"{result.message}"
                        )
                    elif result.status == SKIPPED:
                        st.warning(
                            f"Extraction skipped for {entry['name']}: "
                            f"{result.message}"
                        )

            except Exception as exc:
                st.error(
                    f"Extraction crashed for {entry['name']}: "
                    f"{type(exc).__name__}: {exc}"
                )
                with st.expander(
                    f"Technical details — {entry['name']}"
                ):
                    st.code(str(exc))

            progress.progress(n / len(pending))

        st.rerun()



# ---------- page ----------

def main() -> None:
    init_state()
    render_sidebar()
    st.title("Literature review generator")
    st.write("Version 2: extract each paper's objective, methodology, findings and limitations, "
             "each with a page number and an exact excerpt that is checked against the PDF.")

    uploader_key = st.session_state["uploader_key"]
    files = st.file_uploader("Upload research papers (PDF)", type=["pdf"],
                             accept_multiple_files=True, key=f"uploader-{uploader_key}")
    if not files:
        st.session_state["results"].clear()
        st.session_state["extractions"].clear()
        st.info("Upload one or more PDFs to begin.")
        return
    if len(files) > config.MAX_FILES:
        st.warning(f"Only the first {config.MAX_FILES} files are processed.")

    rq = clean_research_question(st.text_area(
        "Research question (optional)", max_chars=config.MAX_RESEARCH_QUESTION_CHARS, height=80,
        key=f"rq-{uploader_key}",
        help="Helps the AI list the most relevant findings first. It does not filter anything."))

    processed = process_uploads(files)
    readable = [(fid, e) for fid, e in processed if e["parsed"]]
    if readable:
        render_extraction_panel(readable, rq)
        st.divider()

   model = get_model()
    for fid, entry in processed:
        result = None
        if entry["parsed"]:
            parsed = entry["parsed"]
            request = prepare_request(parsed, rq)
            key = extraction_cache_key(parsed.sha256, model, config.EXTRACTION_VERSION,
                                       request.research_question, config.MAX_CHARS_PER_PAPER)
            result = st.session_state["extractions"].get(key)
        render_paper(fid, entry, result)
        st.divider()


main()
