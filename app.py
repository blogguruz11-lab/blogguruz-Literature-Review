"""Version 1: upload research-paper PDFs, extract text page by page, review the result.

Privacy design (verify it yourself, see README):
- Uploaded files are read from memory and parsed from memory. This app writes no uploaded
  content to disk and logs no document text or file names.
- Results live only in st.session_state. No st.cache_* is used.
- Results for a removed upload are dropped, and the sidebar button clears everything.
"""
import logging

import streamlit as st

from core import config
from core.errors import PDFProcessingError
from core.pdf_parser import parse_pdf

logger = logging.getLogger("litreview")

st.set_page_config(page_title="Literature review generator", layout="wide")


# ---------- state ----------

def init_state() -> None:
    st.session_state.setdefault("results", {})       # upload id -> result dict
    st.session_state.setdefault("uploader_key", 0)   # bumping this empties the uploader


def clear_everything() -> None:
    st.session_state["results"].clear()
    st.session_state["uploader_key"] += 1


# ---------- reading uploads ----------

def upload_id(uploaded) -> str:
    return getattr(uploaded, "file_id", None) or f"{uploaded.name}:{uploaded.size}"


def read_one(uploaded) -> dict:
    """Parse one upload. Never raises; errors become a message for the user."""
    data = uploaded.getvalue()
    try:
        return {"name": uploaded.name, "parsed": parse_pdf(data, uploaded.name), "error": None}
    except PDFProcessingError as exc:
        return {"name": uploaded.name, "parsed": None, "error": exc.user_message}
    except Exception as exc:  # last resort. Log only the error type: details may hold content.
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
    return [(fid, results[fid]) for fid in current]


# ---------- screens ----------

def render_sidebar() -> None:
    with st.sidebar:
        st.header("Your data")
        st.write(
            "Files are read into memory and parsed from memory. This app does not save "
            "uploads to disk or write document text to its logs."
        )
        st.caption(
            "Your hosting setup and Streamlit may still record technical details such as "
            "IP addresses and request times. Closing the tab does not instantly free server "
            "memory, so use the button below when you are done."
        )
        if st.button("Delete all session data", type="primary"):
            clear_everything()
            st.rerun()
        st.divider()
        st.subheader("Limits")
        st.write(f"Up to {config.MAX_FILES} files, {config.MAX_FILE_MB} MB and "
                 f"{config.MAX_PAGES} pages each.")
        st.subheader("Not in Version 1")
        st.write("AI extraction, claim IDs, review writing, citation checking, "
                 "comparison tables, Word export, OCR, password-protected PDFs.")


def render_details(parsed, duplicates: list[str]) -> None:
    meta = parsed.metadata
    st.markdown(
        f"- **Title in PDF metadata:** {meta.title or 'not set'}\n"
        f"- **Author in PDF metadata:** {meta.author or 'not set'}\n"
        f"- **Created:** {meta.created or 'not set'}\n"
        f"- **DOI found in first pages:** {parsed.doi_candidate or 'none found'}\n"
        f"- **File fingerprint (SHA-256, first 12):** `{parsed.sha256[:12]}`"
    )
    st.caption("Metadata and the DOI are hints only. Version 1 does not verify them, so check "
               "them against the paper itself.")
    for other in duplicates:
        st.info(f"This file has exactly the same content as “{other}”.")


def render_pages(fid: str, parsed) -> None:
    def describe(index: int) -> str:
        page = parsed.pages[index - 1]
        parts = [f"PDF page {page.index}"]
        if page.label:
            parts.append(f"printed {page.label}")
        parts.append(f"{page.char_count:,} characters")
        if page.low_text:
            parts.append("little text")
        return " · ".join(parts)

    choice = st.selectbox("Page", [p.index for p in parsed.pages],
                          format_func=describe, key=f"page-{fid}")
    st.text_area("Extracted text", value=parsed.pages[choice - 1].text, height=420,
                 disabled=True, key=f"text-{fid}-{choice}", label_visibility="collapsed")


def render_paper(fid: str, entry: dict, duplicates: list[str]) -> None:
    st.subheader(entry["name"])
    if entry["error"]:
        st.error(entry["error"])
        return
    parsed = entry["parsed"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pages", parsed.page_count)
    col2.metric("Words", f"{parsed.word_count:,}")
    col3.metric("Size", f"{parsed.size_bytes / 1_048_576:.1f} MB")
    col4.metric("Pages with little text", len(parsed.low_text_pages))

    for warning in parsed.warnings:
        st.warning(warning)
    with st.expander("Paper details", expanded=True):
        render_details(parsed, duplicates)
    render_pages(fid, parsed)


def main() -> None:
    init_state()
    render_sidebar()

    st.title("Literature review generator")
    st.write("Version 1: upload papers and check that the text and page numbers were extracted "
             "correctly. Later versions will build on this text.")

    files = st.file_uploader(
        "Upload research papers (PDF)", type=["pdf"], accept_multiple_files=True,
        key=f"uploader-{st.session_state['uploader_key']}",
    )
    if not files:
        st.session_state["results"].clear()
        st.info("Upload one or more PDFs to begin.")
        return
    if len(files) > config.MAX_FILES:
        st.warning(f"Only the first {config.MAX_FILES} files are processed.")

    processed = process_uploads(files)
    by_hash: dict[str, list[str]] = {}
    for _, entry in processed:
        if entry["parsed"]:
            by_hash.setdefault(entry["parsed"].sha256, []).append(entry["name"])

    for fid, entry in processed:
        duplicates = []
        if entry["parsed"]:
            duplicates = [n for n in by_hash[entry["parsed"].sha256] if n != entry["name"]]
        render_paper(fid, entry, duplicates)
        st.divider()


main()
