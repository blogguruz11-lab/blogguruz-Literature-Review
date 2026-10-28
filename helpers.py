"""Test helpers: papers built in memory and a fake model client. No API is ever called."""
import hashlib
import json

from core.llm import LLMError, LLMReply
from core.models import PageText, ParsedPDF, PDFMetadata

P1 = ("Sleep and exam performance. Abstract. We examine whether sleep duration affects exam "
      "performance among university students in a large sample.")
P2 = ("Methods. We surveyed 400 students at one university over twelve weeks using a validated "
      "questionnaire and recorded their exam scores.")
P3 = ("Results. Students sleeping under six hours scored lower on average than those sleeping "
      "eight hours or more across all courses studied. Limitations. The sample came from a single "
      "campus so the results may not generalise to other settings.")
P4 = ("References\n[1] Smith A. Another study of sleep. Journal of Sleep 2010. Participants "
      "slept for nine hours in the trial and improved on every measure tested.")


def make_parsed(pages=(P1, P2, P3, P4), name="paper.pdf") -> ParsedPDF:
    page_objs = [PageText(i, None, t, len(t), len(t) < 50) for i, t in enumerate(pages, 1)]
    sha = hashlib.sha256("".join(pages).encode()).hexdigest()
    return ParsedPDF(name, 1000, sha, len(pages), page_objs, PDFMetadata())


def item(text, page, excerpt, **extra):
    return {"text": text, "page": page, "excerpt": excerpt, **extra}


GOOD_REPLY = {
    "objective": item("Tests whether sleep duration affects exam results.", 1,
                      "whether sleep duration affects exam performance among university students"),
    "methodology": item("Survey of 400 students over twelve weeks.", 2,
                        "We surveyed 400 students at one university over twelve weeks"),
    "findings": [item("Short sleepers scored lower.", 3,
                      "Students sleeping under six hours scored lower on average", relevant=True)],
    "limitations": [item("Single campus sample.", 3,
                         "The sample came from a single campus so the results may not generalise")],
}


class FakeLLM:
    """Returns a prepared reply (a dict, a raw string, or an LLMReply) or raises an LLMError."""
    model = "fake-model"

    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []

    def complete(self, system, user, max_tokens):
        self.calls.append({"system": system, "user": user, "max_tokens": max_tokens})
        if self.error:
            raise self.error
        if isinstance(self.reply, LLMReply):
            return self.reply
        return LLMReply(self.reply if isinstance(self.reply, str) else json.dumps(self.reply))


__all__ = ["make_parsed", "item", "GOOD_REPLY", "FakeLLM", "LLMError", "LLMReply",
           "P1", "P2", "P3", "P4"]
