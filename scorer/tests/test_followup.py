"""The inquiry follow-up only ever returns fixed, non-leading CS templates."""

from __future__ import annotations

from scorer.followup import GENERAL_PROMPT, MAX_FOLLOWUPS, keyword_prompt, next_followup
from scorer.lexicon import FOLLOWUP_KEYWORDS
from scorer.schema import FollowupRequest


def ask(verbatim, inquiry="", asked=()):
    return next_followup(FollowupRequest(card=1, verbatim=verbatim, inquiry=inquiry, asked=list(asked)))


def test_keyword_prompt_uses_the_persons_word():
    r = ask("a pretty butterfly", "here are the wings, on the sides")
    assert r.keyword == "pretty"
    assert r.prompt == keyword_prompt("pretty")
    assert "pretty" in r.prompt and r.prompt.endswith("what makes it look pretty?")


def test_keyword_found_in_inquiry():
    r = ask("an animal skin", "the whole thing, it looks soft here")
    assert r.keyword == "soft"


def test_general_prompt_when_explanation_is_vague():
    r = ask("a bat", "it just does")
    assert r.prompt == GENERAL_PROMPT
    assert r.keyword is None


def test_no_prompt_when_explanation_is_clear():
    assert ask("a bat", "here are the wings on the sides and the head at the top").prompt is None


def test_never_repeats_a_prompt():
    first = ask("a pretty flower", "it is")
    second = ask("a pretty flower", "it is", asked=[first.prompt])
    assert second.prompt == GENERAL_PROMPT
    third = ask("a pretty flower", "it is", asked=[first.prompt, second.prompt])
    assert third.prompt is None


def test_stops_after_max_followups():
    asked = ["x"] * MAX_FOLLOWUPS
    assert ask("a pretty flower", "it", asked=asked).prompt is None


def test_prompts_come_only_from_templates():
    allowed = {keyword_prompt(w) for w in FOLLOWUP_KEYWORDS} | {GENERAL_PROMPT, None}
    for text in ["a dark ugly cave", "fluffy clouds", "a monster", "", "blood, bloody and messy"]:
        r = ask(text, text)
        assert r.prompt in allowed
