
"""One AI call per paper, then check every excerpt against the text that was sent."""
import json
import math
import re
from dataclasses import dataclass

from . import config
from .extraction_models import EXTRACTED, FAILED, SKIPPED, EvidenceItem, ExtractionResult
from .inputs import clean_research_question
from .llm import LLMClient, LLMError
from .models import ParsedPDF
from .preparation import PreparedPaper, prepare_paper
from .prompts import SYSTEM_PROMPT, build_user_message
from .verification import PageIndex


@dataclass(frozen=True)
class ExtractionRequest:
    system: str
    user: str
    prepared: PreparedPaper
    research_question: str | None
    estimated_input_tokens: int  # A rough estimate, not a bill


def prepare_request(
    parsed: ParsedPDF,
    research_question: str | None,
) -> ExtractionRequest:
    rq = clean_research_question(research_question)
    prepared = prepare_paper(parsed)
    user = build_user_message(prepared.as_prompt_text(), rq)
    tokens = math.ceil(
        (len(SYSTEM_PROMPT) + len(user))
        / config.CHARS_PER_TOKEN_ESTIMATE
    )
    return ExtractionRequest(
        SYSTEM_PROMPT, user, prepared, rq, tokens
    )


def size_limit_result(
    request: ExtractionRequest,
    parsed: ParsedPDF,
    model: str,
    max_chars: int = config.MAX_CHARS_PER_PAPER,
) -> ExtractionResult | None:
    """Return a skipped result when the paper exceeds the limit."""
    chars = request.prepared.char_count

    if chars <= max_chars:
        return None

    return ExtractionResult(
        status=SKIPPED,
        file_sha256=parsed.sha256,
        model=model,
        research_question=request.research_question,
        estimated_input_tokens=request.estimated_input_tokens,
        reference_note=request.prepared.reference_note,
        message=(
            f"Not sent to the AI: this paper has about {chars:,} "
            f"characters of text, above the limit of {max_chars:,}."
        ),
    )


def parse_reply_json(text: str) -> dict | None:
    text = text.strip()
    candidates = [
        text,
        re.sub(r"^```(?:json)?\s*|\s*```$", "", text),
    ]

    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict):
            return value

    return None


def _read_item(raw, name: str, issues: list[str]) -> dict | None:
    if raw is None:
        return None

    if isinstance(raw, dict):
        text = raw.get("text")
        page = raw.get("page")
        excerpt = raw.get("excerpt")

        ok = (
            isinstance(text, str)
            and bool(text.strip())
            and len(text) <= getattr(
                config, "MAX_ITEM_TEXT_CHARS", 10000
            )
            and isinstance(excerpt, str)
            and bool(excerpt.strip())
            and len(excerpt) <= getattr(
                config, "MAX_EXCERPT_CHARS", 5000
            )
            and isinstance(page, int)
            and not isinstance(page, bool)
        )

        if ok:
            relevant = raw.get("relevant")
            return {
                "text": text.strip(),
                "page": page,
                "excerpt": excerpt.strip(),
                "relevant": (
                    relevant if isinstance(relevant, bool) else None
                ),
            }

    issues.append(
        f"{name}: the model returned an item in the wrong format, "
        "so it was left out."
    )
    return None


def _read_list(
    raw,
    name: str,
    cap: int,
    issues: list[str],
) -> list[dict]:
    if raw is None:
        return []

    if not isinstance(raw, list):
        issues.append(
            f"{name}: the model returned the wrong format, "
            "so it was left out."
        )
        return []

    items = [
        item
        for n, entry in enumerate(raw, 1)
        if (
            item := _read_item(entry, f"{name} #{n}", issues)
        )
    ]

    if len(items) > cap:
        issues.append(
            f"{name}: the model returned {len(items)} items; "
            f"only the first {cap} are shown."
        )
        items = items[:cap]

    return items


class Extractor:
    def __init__(
        self,
        llm: LLMClient,
        *,
        max_chars: int = config.MAX_CHARS_PER_PAPER,
        max_output_tokens: int = config.MAX_OUTPUT_TOKENS,
    ):
        self.llm = llm
        self.max_chars = max_chars
        self.max_output_tokens = max_output_tokens

    def extract(
        self,
        parsed: ParsedPDF,
        research_question: str | None = None,
    ) -> ExtractionResult:
        request = prepare_request(parsed, research_question)
        model = getattr(self.llm, "model", "unknown")

        skipped = size_limit_result(
            request, parsed, model, self.max_chars
        )
        if skipped:
            return skipped

        def result(status: str, **extra) -> ExtractionResult:
            return ExtractionResult(
                status=status,
                file_sha256=parsed.sha256,
                model=model,
                research_question=request.research_question,
                estimated_input_tokens=request.estimated_input_tokens,
                reference_note=request.prepared.reference_note,
                **extra,
            )

        try:
            reply = self.llm.complete(
                request.system,
                request.user,
                self.max_output_tokens,
            )
        except LLMError as exc:
            return result(FAILED, message=exc.user_message)

        if reply.truncated:
            return result(
                FAILED,
                message=(
                    "The AI's reply was cut off before it finished, "
                    "so nothing was saved. Try again."
                ),
            )

        raw = parse_reply_json(reply.text)
        if raw is None:
            return result(
                FAILED,
                message=(
                    "The AI's reply could not be read in the expected "
                    "format, so nothing was saved. Try again."
                ),
            )

        issues: list[str] = []

        objective = _read_item(
            raw.get("objective"), "objective", issues
        )
        methodology = _read_item(
            raw.get("methodology"), "methodology", issues
        )
        findings = _read_list(
            raw.get("findings"), "findings",
            config.MAX_FINDINGS, issues
        )
        limitations = _read_list(
            raw.get("limitations"), "limitations",
            config.MAX_LIMITATIONS, issues
        )

        index = PageIndex(request.prepared.page_texts())

        def checked(item: dict | None) -> EvidenceItem | None:
            if item is None:
                return None

            verdict = index.verify(
                item["excerpt"], item["page"]
            )

            return EvidenceItem(
                item["text"],
                item["page"],
                item["excerpt"],
                verdict.status,
                verdict.found_on,
                item["relevant"],
            )

        return result(
            EXTRACTED,
            objective=checked(objective),
            methodology=checked(methodology),
            findings=[checked(item) for item in findings],
            limitations=[checked(item) for item in limitations],
            issues=issues,
        )
