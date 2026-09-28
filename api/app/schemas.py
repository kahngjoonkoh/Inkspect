from typing import Literal

from pydantic import BaseModel, Field

Orientation = Literal["^", ">", "v", "<"]
Point = list[float]
Polygon = list[Point]


class CreateSession(BaseModel):
    consent: bool


class AddResponse(BaseModel):
    card: int = Field(ge=1, le=10)
    verbatim: str = Field(max_length=2000)
    orientation: Orientation = "^"
    reaction_ms: int | None = Field(default=None, ge=0)


class InquiryBody(BaseModel):
    regions: list[Polygon] = Field(default_factory=list, max_length=20)
    whole_card: bool = False
    explanation: str = Field(default="", max_length=4000)


class FollowupBody(BaseModel):
    prompt: str = Field(max_length=1000)
    answer: str = Field(max_length=4000)


class CodesOverride(BaseModel):
    location_label: str | None = None
    dq: Literal["+", "o", "v/+", "v"] | None = None
    determinants: list[str] | None = None
    fq: Literal["+", "o", "u", "-", "none"] | None = None
    pair: bool | None = None
    contents: list[str] | None = None
    special_scores: list[str] | None = None
    validity: Literal["genuine", "unserious", "gibberish", "refusal", "off_task"] | None = None
    note: str | None = None


class RegionMapBody(BaseModel):
    card: int = Field(ge=1, le=10)
    placeholder: bool = True
    note: str | None = None
    regions: list[dict]
