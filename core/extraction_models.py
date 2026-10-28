"""Result types for AI extraction."""
from dataclasses import dataclass, field

EXTRACTED = "extracted"
FAILED = "failed"
SKIPPED = "skipped"


@dataclass(frozen=True)
class EvidenceItem:
    text: str                        # the model's statement
    page: int                        # PDF page number the model cited
    excerpt: str                     # exact words the model says support it
    status: str                      # a verification status
    found_on: tuple[int, ...] = ()   # pages where the excerpt text was actually found
    relevant: bool | None = None     # relevance to the research question, when one was given


@dataclass
class ExtractionResult:
    status: str                      # EXTRACTED, FAILED or SKIPPED
    file_sha256: str
    model: str
    research_question: str | None
    estimated_input_tokens: int
    reference_note: str = ""
    message: str | None = None       # shown to the user when failed or skipped
    objective: EvidenceItem | None = None
    methodology: EvidenceItem | None = None
    findings: list[EvidenceItem] = field(default_factory=list)
    limitations: list[EvidenceItem] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)   # problems found while reading the reply

    @property
    def items(self) -> list[EvidenceItem]:
        singles = [i for i in (self.objective, self.methodology) if i]
        return singles + self.findings + self.limitations

    @property
    def verified_count(self) -> int:
        return sum(1 for i in self.items if i.status == "verified")

    @property
    def unverified_count(self) -> int:
        return len(self.items) - self.verified_count
