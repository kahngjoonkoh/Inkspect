"""CS-legal inquiry follow-ups.

The examiner may only ask non-leading questions. Prompts therefore come from
a fixed template list and are never generated: either a key-word query about
a word the person used ("You said pretty...") or the general
"help me see it" prompt. At most two follow-ups per response.
"""

from __future__ import annotations

from .lexicon import FOLLOWUP_KEYWORDS, LOCATION_WORDS
from .schema import FollowupRequest, FollowupResponse
from .text import tokens

MAX_FOLLOWUPS = 2

KEYWORD_TEMPLATE = "You said “{word}”. I'm not sure I see it the way you do — what makes it look {word}?"
GENERAL_PROMPT = ("I'm not sure I see it the way you do. Help me see it — "
                  "where is it and what makes it look like that?")


def keyword_prompt(word: str) -> str:
    return KEYWORD_TEMPLATE.format(word=word)


def next_followup(req: FollowupRequest) -> FollowupResponse:
    asked = set(req.asked)
    if len(req.asked) >= MAX_FOLLOWUPS:
        return FollowupResponse()

    said = tokens(f"{req.verbatim} {req.inquiry}")
    for word in FOLLOWUP_KEYWORDS:
        if word in said:
            prompt = keyword_prompt(word)
            if prompt not in asked:
                return FollowupResponse(prompt=prompt, keyword=word)

    explanation = tokens(req.inquiry)
    vague = len(explanation) < 4 or not any(t in LOCATION_WORDS for t in explanation)
    if vague and GENERAL_PROMPT not in asked:
        return FollowupResponse(prompt=GENERAL_PROMPT, keyword=None)
    return FollowupResponse()
