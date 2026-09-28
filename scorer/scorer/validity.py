"""Heuristic check of whether a response is a sincere answer (used by the rule coder).

The trained coders (llm, laya) make this call themselves; this is the baseline. It is
deliberately conservative: odd, morbid or misspelled answers are genuine, and only clear
refusals, keyboard mashing and stock trolling phrases are flagged.
"""

from __future__ import annotations

import re

_REFUSAL = re.compile(
    r"^\s*(idk|i ?dunno|dunno|i don'?t know|no idea|nothing|nothin|none|nah|no|pass|skip|n/?a|"
    r"i can'?t (see|tell)( anything)?|i see nothing|can'?t see anything|not sure|no clue|\?+|\.+|-+)\s*[.!?]*\s*$",
    re.I)
_TROLL = re.compile(
    r"\b(lol+|lmao+|rofl|lmfao|ur mom|your mom|yo mama|deez nuts|amogus|rickroll|skibidi|gyatt|rizz|"
    r"poggers|kek|this test is (dumb|stupid|bs)|big chungus|troll(ing)?|jk|just kidding|haha+|hehe+)\b",
    re.I)
_OFF_TASK = re.compile(
    r"^\s*(how (long|many)|when (does|will)|is this|what is this test|why (do|are)|can i|"
    r"what do you want|hello|hi+|hey|ok(ay)?|thanks?|thank you|test+ing?)\b",
    re.I)
_VOWELS = set("aeiouy")


def _gibberish(text: str) -> bool:
    letters = re.sub(r"[^a-z]", "", text.lower())
    if len(letters) < 4:
        return False
    words = re.findall(r"[a-z]+", text.lower())
    vowel_share = sum(ch in _VOWELS for ch in letters) / len(letters)
    long_consonant_run = re.search(r"[^aeiouy\W\d_]{6,}", text.lower()) is not None
    repeated = re.search(r"(.)\1{4,}", letters) is not None or re.search(r"(\w{2,4})\1{3,}", letters) is not None
    keyboard_rows = sum(w in ("asdf", "qwer", "zxcv", "hjkl", "jkl", "qwerty", "asdfgh") or
                        any(row in w for row in ("asdf", "qwert", "zxcv", "hjkl", "sdfg", "fghj"))
                        for w in words)
    return vowel_share < 0.15 or long_consonant_run or repeated or keyboard_rows > 0


def classify(verbatim: str, inquiry: str = "") -> str:
    v = verbatim.strip()
    if not v or _REFUSAL.match(v):
        return "refusal"
    if _gibberish(v):
        return "gibberish"
    if _TROLL.search(v) or _TROLL.search(inquiry or ""):
        return "unserious"
    if _OFF_TASK.match(v):
        return "off_task"
    return "genuine"
