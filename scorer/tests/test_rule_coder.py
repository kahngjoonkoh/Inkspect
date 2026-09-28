"""Unit tests for each RuleCoder rule family."""

from __future__ import annotations

import pytest

from scorer.coders.rule import RuleCoder
from scorer.schema import DETERMINANTS, CodeRequest, FQHint, Location
from scorer.text import candidates, find, tokens

CODER = RuleCoder()


def code(verbatim: str, inquiry: str = "", card: int = 3, **kw):
    return CODER.code(CodeRequest(card=card, verbatim=verbatim, inquiry=inquiry, **kw))


# --- text helpers -------------------------------------------------------------------

def test_tokens_normalize_spelling_and_quotes():
    assert tokens("The COLOUR, it’s grey X-ray") == ["the", "color", "it's", "gray", "xray"]


@pytest.mark.parametrize(("word", "base"), [
    ("butterflies", "butterfly"), ("wolves", "wolf"), ("dancing", "dance"), ("running", "run"),
    ("people", "person"), ("lying", "lie"), ("mandibles", "mandible"), ("crushed", "crush"),
])
def test_candidates_include_base_form(word, base):
    assert base in candidates(word)


def test_find_matches_phrases_before_words():
    hits = find(tokens("light and dark here"), {"light and dark": "Y", "dark": "C'"})
    assert [(h.value, h.span) for h in hits] == [("Y", "light and dark")]


# --- contents ----------------------------------------------------------------------

@pytest.mark.parametrize(("verbatim", "expected"), [
    ("a bat", "A"), ("two men", "H"), ("a witch", "(H)"), ("a dragon", "(A)"), ("a face", "Hd"),
    ("a mask", "(Hd)"), ("the horns of a deer", "Ad"), ("a bear skin", "Ad"), ("a pelvis", "An"),
    ("an x-ray", "Xy"), ("blood", "Bl"), ("a flower", "Bt"), ("a hat", "Cg"), ("clouds", "Cl"),
    ("an explosion", "Ex"), ("fire", "Fi"), ("an ice cream cone", "Fd"), ("a map", "Ge"),
    ("a lamp", "Hh"), ("a mountain", "Ls"), ("the sun", "Na"), ("an airplane", "Sc"), ("a totem pole", "Ay"),
    ("a painting", "Art"),
])
def test_primary_content(verbatim, expected):
    assert code(verbatim).contents[0] == expected


def test_unknown_content_is_id():
    assert code("a zorblax thing").contents == ["Id"]


def test_detail_of_fictional_human_is_parenthesized():
    assert code("the head of a giant").contents[0] == "(Hd)"


def test_secondary_content_from_inquiry():
    codes = code("two people", "they are holding a pot and wearing hats")
    assert codes.contents[0] == "H"
    assert {"Hh", "Cg"} <= set(codes.contents)


def test_fq_hint_content_leads_and_replaces_same_family():
    codes = code("a raccoon", fq_hint=FQHint(item="Raccoon (head)", content="Ad", fq="o"))
    assert codes.contents[0] == "Ad"
    assert "A" not in codes.contents
    assert codes.fq_fallback is None


def test_verb_fly_is_not_the_insect():
    codes = code("a bird flying", card=5)
    assert codes.contents == ["A"]
    assert codes.determinants == ["FMa"]


# --- movement ---------------------------------------------------------------------

@pytest.mark.parametrize(("verbatim", "expected"), [
    ("two people dancing", "Ma"), ("a man sitting", "Mp"), ("a dog running", "FMa"), ("a bird resting", "FMp"),
    ("an explosion, it is exploding", "ma"), ("water dripping", "mp"), ("a sad face", "Mp"),
])
def test_movement(verbatim, expected):
    assert expected in code(verbatim).determinants


def test_looks_like_is_not_movement():
    assert code("it looks like a bat", "it looks like wings here", card=5).determinants == ["F"]


def test_active_and_passive_on_different_figures_is_a_p():
    codes = code("a man running and a woman sitting")
    assert "Ma-p" in codes.determinants


def test_animals_in_human_activity_get_m_and_fab():
    codes = code("two bears dancing", card=2)
    assert "Ma" in codes.determinants
    assert "FAB1" in codes.special_scores


def test_stative_participle_is_not_movement():
    assert code("tusks of an elephant", "they look a bit burst", card=7).determinants == ["F"]


# --- colour, shading, texture, dimension, reflection -------------------------------------

def test_form_colour():
    assert "FC" in code("a butterfly", "the shape and it is orange", card=8).determinants


def test_colour_dominant_on_formless():
    assert "CF" in code("fire", "the flames, because it is orange and red", card=9).determinants


def test_pure_colour():
    codes = code("blood", "because it's red", card=2)
    assert "C" in codes.determinants
    assert codes.dq == "v"


def test_colour_naming():
    assert code("red and blue", "just the colors", card=10).determinants == ["Cn"]


def test_colour_used_only_to_locate_is_ignored():
    assert code("a crab", "the blue part", card=10).determinants == ["F"]


def test_chromatic_on_achromatic_card_is_cp():
    codes = code("a pink butterfly", card=5)
    assert "CP" in codes.special_scores
    assert not {"FC", "CF", "C", "Cn"} & set(codes.determinants)


def test_achromatic_colour():
    assert "FC'" in code("a bat", "because it's black", card=5).determinants


def test_texture():
    assert "FT" in code("an animal skin", "it looks furry", card=6).determinants


def test_diffuse_shading():
    assert "FY" in code("an x-ray of a pelvis", "the light and dark shading", card=6).determinants


def test_vista_needs_shading_and_depth():
    codes = code("a canyon", "the darker shading makes it look deep, far away", card=4)
    assert any(d in ("FV", "VF", "V") for d in codes.determinants)


def test_form_dimension_without_shading():
    assert "FD" in code("a giant", "seen from below, his feet are big", card=4).determinants


def test_reflection_blocks_pair():
    codes = code("a bear and its reflection in the water", card=8)
    assert "Fr" in codes.determinants
    assert not codes.pair


def test_all_determinants_are_contract_codes():
    samples = ["two people dancing", "blood", "red and blue", "a furry rug", "a reflection", "a bat"]
    for s in samples:
        for d in code(s, card=10).determinants:
            assert d in DETERMINANTS


# --- developmental quality and pair ---------------------------------------------------

@pytest.mark.parametrize(("verbatim", "dq"), [
    ("a bat", "o"), ("a man holding a flag", "+"), ("a cloud", "v"), ("clouds over the water", "v/+"),
    ("a group of rhinos", "+"), ("two women talking to each other", "+"),
])
def test_dq(verbatim, dq):
    assert code(verbatim, card=9).dq == dq


@pytest.mark.parametrize(("verbatim", "inquiry", "pair"), [
    ("two dogs", "", True), ("lions", "", True), ("a pair of boots", "", True),
    ("a butterfly", "one wing on each side", False), ("a crab", "", False),
    ("a beaver", "the two blue spots are his fists", False),
])
def test_pair(verbatim, inquiry, pair):
    assert code(verbatim, inquiry, card=10).pair is pair


# --- special scores -------------------------------------------------------------------

@pytest.mark.parametrize(("verbatim", "inquiry", "score"), [
    ("a dead bird", "", "MOR"), ("a torn butterfly", "", "MOR"),
    ("two men fighting", "", "AG"),
    ("two women dancing together", "", "COP"),
    ("a bat", "I've seen one like this at my uncle's house", "PER"),
    ("a symbol of peace", "", "AB"),
    ("a pair of two birds", "", "DV1"),
    ("a bat with hands", "", "INC1"), ("a green dog", "", "INC1"), ("a butterfly with a face", "", "INC1"),
])
def test_special_scores(verbatim, inquiry, score):
    assert score in code(verbatim, inquiry, card=8).special_scores


def test_cop_not_scored_with_ag():
    assert "COP" not in code("two people fighting together").special_scores


# --- fq fallback, evidence, confidence --------------------------------------------------

def test_fq_fallback_default_and_dd99():
    assert code("a bat").fq_fallback == "u"
    dd99 = code("a bat", location=Location(code="Dd", number=99, label="Dd99"))
    assert dd99.fq_fallback == "-"


def test_every_code_has_evidence_and_confidence():
    codes = code("two people dancing", "the red is blood", card=3)
    for key in ("H", "Ma", "(2)", "COP"):
        assert codes.evidence[key]
        assert 0 < codes.confidence[key] <= 1
    assert codes.coder == "rule"


def test_deterministic():
    a = code("a bat flying", "the wings are black")
    b = code("a bat flying", "the wings are black")
    assert a == b


def test_naturally_colored_animals_are_not_incom():
    assert "INC1" not in code("blue crabs", card=10).special_scores
    assert "INC1" in code("a blue dog", card=10).special_scores


def test_detail_named_in_response_beats_whole_object_hint():
    codes = code("rabbit ears", card=5, fq_hint=FQHint(item="Rabbit", content="A", fq="u"))
    assert codes.contents == ["Ad"]


@pytest.mark.parametrize("verbatim,expected", [
    ("a bat", "genuine"), ("a buterfly wiht big wigns", "genuine"), ("a dead crushed animal", "genuine"),
    ("a map of ohio", "genuine"), ("idk", "refusal"), ("nothing", "refusal"), ("asdfghjkl", "gibberish"),
    ("jjjjjjjjj", "gibberish"), ("ur mom lol", "unserious"), ("deez nuts", "unserious"),
    ("how long is this test", "off_task"),
])
def test_validity_heuristic(verbatim, expected):
    assert code(verbatim).validity == expected
