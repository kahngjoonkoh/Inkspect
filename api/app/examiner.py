"""Comprehensive System administration rules for the response phase.

Pure functions only: the routers apply the decisions to the database.
"""

import re
from dataclasses import dataclass

MAX_PER_CARD = 5
MIN_R = 14
LAST_CARD = 10

INKBLOT_MESSAGE = (
    "That's right, that's what it is, but I want you to tell me what it might be "
    "— what else does it look like?"
)
CARD_FULL_MESSAGE = "Alright, let's do the next one."
EMPTY_CARD_MESSAGE = "Take your time. Most people find something."
CARD1_SINGLE_MESSAGE = "If you take your time and look some more, I think you'll find something else too."
READMINISTER_MESSAGE = (
    "Now you know how it's done. But there's a problem: you didn't give enough answers "
    "for us to get anything out of the test. We'll go through them again, and this time "
    "give more answers. You can include the same ones you already gave if you like."
)

_BLOT_WORDS = {"ink", "inkblot", "inkblots", "blot", "blots", "splotch", "splatter", "stain", "smudge", "spill"}
_FILLER = {"a", "an", "the", "just", "it", "its", "it's", "is", "some", "of", "looks", "like", "i", "see",
           "only", "this", "that", "thats", "that's", "to", "me", "piece", "bunch", "lot", "lots", "and",
           "black", "coloured", "colored", "big", "spilled", "spilt"}


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def is_inkblot_answer(text: str) -> bool:
    """True when the answer only says it is an inkblot (the CS 'that's what it is' case)."""
    words = re.findall(r"[a-z']+", text.lower())
    content = [w for w in words if w not in _FILLER]
    return bool(content) and all(w in _BLOT_WORDS for w in content)


@dataclass(frozen=True)
class AddDecision:
    accepted: bool
    message: str | None = None
    card_full: bool = False


def decide_add(verbatim: str, existing_on_card: list[str]) -> AddDecision:
    text = normalise(verbatim)
    if not text:
        return AddDecision(False)
    if len(existing_on_card) >= MAX_PER_CARD:
        return AddDecision(False, CARD_FULL_MESSAGE, card_full=True)
    if is_inkblot_answer(text):
        return AddDecision(False, INKBLOT_MESSAGE)
    if text in {normalise(e) for e in existing_on_card}:
        return AddDecision(False)
    full = len(existing_on_card) + 1 >= MAX_PER_CARD
    return AddDecision(True, CARD_FULL_MESSAGE if full else None, card_full=full)


@dataclass(frozen=True)
class NextDecision:
    action: str  # stay | next_card | readminister | inquiry
    message: str | None = None


def decide_next(card: int, count_on_card: int, card1_prompted: bool, empty_prompted: bool,
                total_r: int, administration: int) -> NextDecision:
    """What happens when the test taker presses "Next card".

    - An empty card gets one encouragement; pressing again moves on (a CS rejection).
    - A single response on Card I gets the standard prompt, once.
    - After Card X, a record with R < 14 is re-administered once.
    """
    if count_on_card == 0 and not empty_prompted:
        return NextDecision("stay", EMPTY_CARD_MESSAGE)
    if card == 1 and count_on_card == 1 and not card1_prompted:
        return NextDecision("stay", CARD1_SINGLE_MESSAGE)
    if card < LAST_CARD:
        return NextDecision("next_card")
    if total_r < MIN_R and administration == 1:
        return NextDecision("readminister", READMINISTER_MESSAGE)
    return NextDecision("inquiry")


def normalise_spacing(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())
