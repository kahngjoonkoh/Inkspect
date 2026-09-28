"""Structural summary math, checked by hand against the coded protocol in fixtures/example_protocol.txt."""

import pytest

from app.interpretation import interpret
from app.summary import compute, constellations, fmt, split_movement, structural_summary


def row(card, loc, num, dq, dets, fq, contents, pair=False, popular=False, z=None, specials=(), space=False):
    return {"card": card, "location": {"code": loc, "number": num, "space": space,
                                       "label": f"{loc}{'S' if space else ''}{num or ''}"},
            "dq": dq, "determinants": dets, "fq": fq, "contents": contents, "pair": pair, "popular": popular,
            "z": z, "special_scores": list(specials)}


# The 18 responses of the example protocol (the typo "m'p" on card VI read as "mp").
EXAMPLE = [
    row(1, "W", None, "o", ["FMp"], "o", ["A"], popular=True, z=1.0),
    row(1, "W", None, "o", ["F"], "-", ["A"], z=1.0),
    row(1, "W", None, "o", ["F"], "u", ["A"], popular=True, z=1.0),
    row(2, "W", None, "o", ["F"], "-", ["A"], z=4.5),
    row(2, "D", 2, "o", ["F"], "-", ["Ad"]),
    row(2, "D", 3, "o", ["F"], "-", ["Ad"]),
    row(3, "D", 1, "o", ["F"], "-", ["A"], space=True),
    row(3, "Dd", 99, "o", ["F"], "-", ["Ad"]),
    row(4, "D", 3, "o", ["FY"], "o", ["Ad"]),
    row(4, "D", 1, "o", ["Mp", "FV"], "-", ["Ad", "Hx"], specials=["MOR", "INC1"]),
    row(5, "W", None, "o", ["FMa"], "o", ["A"], popular=True, z=1.0),
    row(6, "W", None, "o", ["mp"], "o", ["Ad"], popular=True, z=2.5, specials=["MOR"]),
    row(7, "W", None, "o", ["F"], "-", ["Ad"], z=2.5, specials=["MOR"]),
    row(7, "W", None, "o", ["F"], "-", ["Ad"], z=2.5, specials=["PSV"]),
    row(8, "D", 1, "o", ["F"], "o", ["A"], pair=True, popular=True, specials=["MOR"]),
    row(8, "D", 7, "o", ["F"], "u", ["A"]),
    row(9, "D", 6, "+", ["F"], "-", ["A"], pair=True, z=2.5),
    row(10, "Dd", 99, "o", ["F"], "-", ["A"], space=True, specials=["INC2"]),
]


@pytest.fixture(scope="module")
def v():
    return compute(EXAMPLE)


def test_location_and_organisation(v):
    assert v["R"] == 18 and v["valid"]
    assert (v["W"], v["D"], v["Dd"], v["S"]) == (8, 8, 2, 2)
    assert v["Zf"] == 9 and v["ZSum"] == 18.5 and v["ZEst"] == 27.5 and v["Zd"] == -9.0
    assert v["DQ"] == {"+": 1, "o": 17, "v/+": 0, "v": 0}
    assert v["approach"]["I"] == "W.W.W" and v["approach"]["III"] == "DS.Dd"


def test_determinants_and_core(v):
    assert v["determinants"]["F"] == 13
    assert v["L"] == pytest.approx(13 / 5)
    assert (v["M"], v["FM"], v["m"], v["SumY"], v["SumV"]) == (1, 2, 1, 1, 1)
    assert (v["a"], v["p"], v["Ma"], v["Mp"]) == (1, 3, 0, 1)
    assert v["WSumC"] == 0 and v["EA"] == 1 and v["es"] == 5 and v["AdjEs"] == 5
    assert v["Dscore"] == -1 and v["AdjD"] == -1
    assert v["EBStyle"] == "Avoidant" and v["EBPer"] is None
    assert v["blends"] == ["Mp.FV"] and v["ColShdBlends"] == 0


def test_form_quality_and_mediation(v):
    assert v["FQx"] == {"+": 0, "o": 5, "u": 2, "-": 11, "none": 0}
    assert v["MQual"]["-"] == 1 and v["M-"] == 1
    assert v["XA%"] == pytest.approx(7 / 18)
    assert v["WDA%"] == pytest.approx(7 / 16)
    assert v["X-%"] == pytest.approx(11 / 18)
    assert v["X+%"] == pytest.approx(5 / 18)
    assert v["Xu%"] == pytest.approx(2 / 18)
    assert v["S-"] == 2 and v["P"] == 5


def test_affect_interpersonal_self(v):
    assert v["Afr"] == pytest.approx(4 / 14)
    assert v["contents"]["A"] == 10 and v["contents"]["Ad"] == 8 and v["contents"]["Hx"] == 1
    assert v["HumanCont"] == 0 and v["PureH"] == 0 and v["Isolation"] == 0
    assert v["Egocentricity"] == pytest.approx(2 / 18)
    assert v["MOR"] == 4 and v["PSV"] == 1


def test_special_score_sums(v):
    assert v["Sum6"] == 2 and v["Lvl2"] == 1 and v["WSum6"] == 2 + 4


def test_constellations(v):
    c = {item["name"]: item for item in constellations(v)}
    assert c["PTI"]["value"] == 3 and not c["PTI"]["positive"]
    assert c["DEPI"]["value"] == 5 and c["DEPI"]["positive"]
    assert c["CDI"]["value"] == 4 and c["CDI"]["positive"]
    assert c["S-CON"]["value"] == 6 and not c["S-CON"]["positive"]
    assert c["HVI"]["value"] == 2 and not c["HVI"]["positive"]
    assert not c["OBS"]["positive"]
    assert [x["met"] for x in c["DEPI"]["conditions"]] == [True, False, True, True, False, True, True]


def test_interpretation_picks_first_positive_key_variable(v):
    result = interpret(v, constellations(v), placeholder_regions=True)
    assert result["key_variable"] == "CDI > 3"
    assert result["strategy"].startswith("Controls → Interpersonal")
    assert any("placeholder" in c for c in result["caveats"])
    controls = next(cl for cl in result["clusters"] if cl["name"] == "Controls")
    assert any("Adj D is below zero" in f for f in controls["findings"])


def test_d_score_scale():
    base = [row(1, "W", None, "o", ["Ma"], "o", ["H"], z=1.0)] * 6
    v = compute(base + [row(2, "W", None, "o", ["F"], "o", ["A"])] * 4)
    assert v["EA"] == 6 and v["es"] == 0 and v["Dscore"] == 2  # +5.5..+7.5 -> +2
    assert v["EBStyle"] == "Introversive"


def test_extratensive_and_ebper():
    rows = ([row(8, "D", 1, "o", ["CF"], "o", ["Bt"])] * 4 + [row(9, "D", 1, "o", ["Ma"], "o", ["H"])]
            + [row(1, "W", None, "o", ["F"], "o", ["A"])] * 2 + [row(2, "W", None, "o", ["FMa"], "o", ["A"])] * 8)
    v = compute(rows)
    assert v["WSumC"] == 4.0 and v["M"] == 1 and v["EBStyle"] == "Extratensive" and v["EBPer"] == 4.0


def test_short_record_is_flagged_invalid():
    v = compute(EXAMPLE[:10])
    assert not v["valid"]
    assert "not interpretively valid" in interpret(v, constellations(v), False)["caveats"][0]


def test_display_format():
    assert fmt(0.4375) == ".44" and fmt(2.6) == "2.60" and fmt(None) == "—" and fmt(4.0) == "4.0" and fmt(0.0) == "0.0"
    _, summary = structural_summary(EXAMPLE)
    titles = [s["title"] for s in summary["sections"]]
    assert "Core" in titles and "Mediation" in titles
    core = {i["label"]: i["value"] for s in summary["sections"] if s["title"] == "Core" for i in s["items"]}
    assert core["R"] == "18" and core["EB"] == "1 : 0.0" and core["L"] == "2.60"


def test_split_movement():
    assert split_movement("FMa") == ("FM", "a")
    assert split_movement("Ma-p") == ("M", "a-p")
    assert split_movement("mp") == ("m", "p")
    assert split_movement("FC'") == ("FC'", None)
