from types import SimpleNamespace

from app.scoring import build_protocol, effective_codes, form_quality, has_form
from app.tables import is_popular, z_value, zest


def resp(id=1, card=1, verbatim="a bat", explanation="the wings", regions=None, location=None, codes=None,
         fq_match=None, override=None, followups=None, orientation="^"):
    return SimpleNamespace(
        id=id, card=card, verbatim=verbatim, explanation=explanation, followups=followups or [],
        regions=regions if regions is not None else [[[0, 0], [1, 0], [1, 1]]], orientation=orientation,
        location=location or {"code": "W", "number": None, "space": False, "label": "W", "placeholder": True},
        codes=codes or {"dq": "o", "determinants": ["F"], "pair": False, "contents": ["A"], "special_scores": [],
                        "fq_fallback": "u", "coder": "rule"},
        fq_match=fq_match, override=override,
    )


def test_formless_determinants_have_no_fq():
    assert not has_form(["C"], "v") and not has_form(["C'", "Y"], "v")
    assert not has_form(["mp"], "v") and has_form(["mp"], "o")
    assert form_quality(["C"], "v", {"fq": "o", "location_match": True}, "u", "") == "none"


def test_fq_comes_from_table_only_on_a_location_match():
    assert form_quality(["F"], "o", {"fq": "-", "location_match": True}, "u", "") == "-"
    assert form_quality(["F"], "o", {"fq": "-", "location_match": False}, "u", "") == "u"
    assert form_quality(["F"], "o", None, "-", "") == "-"


def test_well_articulated_ordinary_response_is_plus():
    text = "the head, the wings, the legs and the tail"
    assert form_quality(["F"], "o", {"fq": "o", "location_match": True}, "u", text) == "+"


def test_z_values():
    assert z_value(1, "W", "o", False, 1, True) == 1.0
    assert z_value(1, "W", "v", False, 1, True) is None
    assert z_value(9, "D", "+", False, 1, True) == 2.5   # adjacent
    assert z_value(9, "D", "+", False, 2, True) == 4.5   # distant
    assert z_value(10, "W", "+", True, 1, True) == 6.0   # ZS beats ZW
    assert z_value(3, "D", "o", False, 1, True) is None
    assert z_value(3, "Dd", "o", True, 1, True, space_only=True) is None
    assert z_value(1, "W", "o", False, 1, has_form=False) is None
    assert zest(9) == 27.5 and zest(0) is None and zest(80) == 173.0


def test_populars():
    assert is_popular(1, "W", "a bat")
    assert is_popular(5, "W", "two butterflies")
    assert not is_popular(1, "D1", "a bat")
    assert is_popular(10, "D1", "a blue crab")
    assert is_popular(7, "D1", "a girl's face")
    assert not is_popular(7, "D1", "a face of a rabbit")
    assert is_popular(6, "W", "an animal skin rug")


def test_override_replaces_coder_fields():
    merged = effective_codes({"dq": "o", "determinants": ["F"], "contents": ["A"]},
                             {"determinants": ["FMa"], "note": "x"})
    assert merged["determinants"] == ["FMa"] and merged["contents"] == ["A"]


def test_protocol_rows_numbering_popular_z_and_score_line():
    rows = build_protocol([
        resp(id=2, card=2, verbatim="two bears", location={"code": "D", "number": 1, "space": False,
                                                           "label": "D1", "placeholder": True},
             codes={"dq": "o", "determinants": ["FMa"], "pair": True, "contents": ["A"], "special_scores": []},
             fq_match={"fq": "o", "location_match": True}),
        resp(id=1, card=1, fq_match={"fq": "o", "location_match": True}),
    ])
    assert [r["number"] for r in rows] == [1, 2] and rows[0]["card"] == 1
    assert rows[0]["score_line"] == "Wo F o A P 1.0"
    assert rows[1]["score_line"] == "Do 1 FMa o (2) A P"


def test_perseveration_within_a_card():
    rows = build_protocol([resp(id=1, card=7, verbatim="horns"), resp(id=2, card=7, verbatim="horns again"),
                           resp(id=3, card=8, verbatim="horns")])
    assert "PSV" not in rows[0]["special_scores"]
    assert "PSV" in rows[1]["special_scores"]
    assert "PSV" not in rows[2]["special_scores"]


def test_ghr_phr():
    good = resp(codes={"dq": "o", "determinants": ["Ma"], "pair": False, "contents": ["H"],
                       "special_scores": []}, fq_match={"fq": "o", "location_match": True})
    poor = resp(id=2, card=2, codes={"dq": "o", "determinants": ["F"], "pair": False, "contents": ["Hd"],
                                     "special_scores": []}, fq_match={"fq": "-", "location_match": True})
    animal = resp(id=3, card=3)
    rows = build_protocol([good, poor, animal])
    assert "GHR" in rows[0]["special_scores"]
    assert "PHR" in rows[1]["special_scores"]
    assert not {"GHR", "PHR"} & set(rows[2]["special_scores"])


def test_reviewer_location_and_fq_override():
    r = resp(override={"location": {"code": "D", "number": 4, "space": False, "label": "D4",
                                    "placeholder": False}, "fq": "-"})
    row = build_protocol([r])[0]
    assert row["location"]["label"] == "D4" and row["fq"] == "-" and row["overridden"]
