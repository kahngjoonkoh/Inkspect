"""Request/response models shared by every coder (see the build contract)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Orientation = Literal["^", ">", "v", "<"]
DQ = Literal["+", "o", "v/+", "v"]
CoderName = Literal["rule", "llm", "laya"]

MOVEMENT_BASES = ("M", "FM", "m")
MOVEMENT_SUPERSCRIPTS = ("a", "p", "a-p")

DETERMINANTS: tuple[str, ...] = (
    *(f"{b}{s}" for b in MOVEMENT_BASES for s in MOVEMENT_SUPERSCRIPTS),
    "F",
    "FC", "CF", "C", "Cn",
    "FC'", "C'F", "C'",
    "FT", "TF", "T",
    "FV", "VF", "V",
    "FY", "YF", "Y",
    "Fr", "rF",
    "FD",
)

CONTENTS: tuple[str, ...] = (
    "H", "(H)", "Hd", "(Hd)", "Hx",
    "A", "(A)", "Ad", "(Ad)",
    "An", "Art", "Ay", "Bl", "Bt", "Cg", "Cl", "Ex", "Fd", "Fi", "Ge",
    "Hh", "Ls", "Na", "Sc", "Sx", "Xy", "Id",
)

SPECIAL_SCORES: tuple[str, ...] = (
    "DV1", "DV2", "INC1", "INC2", "DR1", "DR2", "FAB1", "FAB2",
    "ALOG", "CONTAM", "AB", "AG", "COP", "MOR", "PER", "CP",
)

CARD_ROMAN = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"}
ORIENTATION_WORDS = {"^": "upright", ">": "rotated right", "v": "upside down", "<": "rotated left"}
ACHROMATIC_CARDS = frozenset({1, 4, 5, 6, 7})


class Location(BaseModel):
    code: Literal["W", "D", "Dd"]
    number: int | None = None
    space: bool = False
    label: str


class FollowupQA(BaseModel):
    prompt: str
    answer: str = ""


class FQHint(BaseModel):
    item: str
    content: str
    fq: str


class CodeRequest(BaseModel):
    card: int = Field(ge=1, le=10)
    orientation: Orientation = "^"
    verbatim: str
    inquiry: str = ""
    followups: list[FollowupQA] = Field(default_factory=list)
    location: Location | None = None
    fq_hint: FQHint | None = None
    coder: CoderName | None = None

    def inquiry_text(self) -> str:
        """Inquiry explanation plus follow-up answers, as one block of text."""
        parts = [self.inquiry, *(f.answer for f in self.followups)]
        return " ".join(p for p in parts if p)


class Codes(BaseModel):
    dq: DQ = "o"
    determinants: list[str] = Field(default_factory=lambda: ["F"])
    pair: bool = False
    contents: list[str] = Field(default_factory=list)
    special_scores: list[str] = Field(default_factory=list)
    fq_fallback: Literal["u", "-"] | None = None
    evidence: dict[str, str] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    coder: CoderName = "rule"

    @field_validator("determinants")
    @classmethod
    def _check_determinants(cls, v: list[str]) -> list[str]:
        bad = [d for d in v if d not in DETERMINANTS]
        if bad:
            raise ValueError(f"unknown determinants: {bad}")
        if not v:
            raise ValueError("at least one determinant is required")
        return list(dict.fromkeys(v))

    @field_validator("contents")
    @classmethod
    def _check_contents(cls, v: list[str]) -> list[str]:
        bad = [c for c in v if c not in CONTENTS]
        if bad:
            raise ValueError(f"unknown contents: {bad}")
        return list(dict.fromkeys(v))

    @field_validator("special_scores")
    @classmethod
    def _check_special(cls, v: list[str]) -> list[str]:
        bad = [s for s in v if s not in SPECIAL_SCORES]
        if bad:
            raise ValueError(f"unknown special scores: {bad}")
        return list(dict.fromkeys(v))

    @field_validator("confidence")
    @classmethod
    def _check_confidence(cls, v: dict[str, float]) -> dict[str, float]:
        return {k: min(1.0, max(0.0, float(x))) for k, x in v.items()}


class FollowupRequest(BaseModel):
    card: int = Field(ge=1, le=10)
    verbatim: str
    inquiry: str = ""
    asked: list[str] = Field(default_factory=list)


class FollowupResponse(BaseModel):
    prompt: str | None = None
    keyword: str | None = None


def state_text(req: CodeRequest) -> str:
    """Plain-text rendering of a response, used as the model 'state' (Laya, training export)."""
    lines = [
        f"Card: {CARD_ROMAN[req.card]} ({'achromatic' if req.card in ACHROMATIC_CARDS else 'chromatic'})",
        f"Orientation: {ORIENTATION_WORDS[req.orientation]}",
        f"Location: {req.location.label if req.location else 'unknown'}",
        f"Response: {req.verbatim.strip()}",
        f"Inquiry: {req.inquiry.strip()}",
    ]
    for f in req.followups:
        lines.append(f"Examiner: {f.prompt.strip()}")
        lines.append(f"Answer: {f.answer.strip()}")
    return "\n".join(lines)
